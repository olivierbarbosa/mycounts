"""Matérialisation des échéances récurrentes, contre PostgreSQL.

L'idempotence n'est pas testée « en principe » : le job est réellement rejoué trois fois
et l'on vérifie que rien ne bouge. C'est la seule façon de savoir si la clé d'unicité
fait son travail.
"""

from __future__ import annotations

import datetime as dt

import pytest
from mycounts.domain.agregats import Agregat, EtatOperation, calculer
from mycounts.domain.montants import Cents
from mycounts.domain.recurrence import UniteRecurrence
from mycounts.jobs.materialisation import materialiser
from mycounts.repository import budget as depot
from mycounts.repository import recurrences as depot_rec
from mycounts.repository.base import Principal
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.integration.test_api_auth import creer_compte as creer_utilisateur

J = dt.date


def foyer_avec_recurrence(
    session: Session, *, ancre: dt.date, montant: int = -1099, fin: dt.date | None = None
) -> tuple[Principal, object]:
    foyer_id, utilisateur_id = creer_utilisateur(session, "a@essai.fr")
    principal = Principal(utilisateur_id=utilisateur_id, foyer_id=foyer_id)
    compte = depot.creer_compte(session, principal, nom="Courant")
    session.commit()
    recurrence = depot_rec.creer_recurrence(
        session,
        principal,
        compte_id=compte.id,
        libelle="Abonnement musique",
        montant_centimes=Cents(montant),
        ancre=ancre,
        unite=UniteRecurrence.MOIS,
        fin=fin,
    )
    session.commit()
    return principal, recurrence


def test_les_echeances_echues_deviennent_des_operations_a_confirmer(
    session_bd: Session,
) -> None:
    principal, _ = foyer_avec_recurrence(session_bd, ancre=J(2026, 6, 5))

    bilan = materialiser(session_bd, a_la_date=J(2026, 8, 19), foyer_id=principal.foyer_id)

    assert bilan.creees == 3  # 5 juin, 5 juillet, 5 août
    operations = depot.operations_visibles(session_bd, principal)
    assert [o.date_operation for o in operations] == [J(2026, 8, 5), J(2026, 7, 5), J(2026, 6, 5)]
    assert all(o.etat == EtatOperation.A_CONFIRMER for o in operations)


def test_le_job_est_idempotent(session_bd: Session) -> None:
    """Rejoué trois fois, il ne crée aucun doublon.

    Les deux compteurs varient en sens opposés d'une exécution à l'autre : la première
    crée et n'ignore rien, les suivantes n'ignorent que ce qui existe déjà. Si les deux
    montaient ensemble, la clé d'unicité ne servirait à rien.
    """
    principal, _ = foyer_avec_recurrence(session_bd, ancre=J(2026, 6, 5))

    premier = materialiser(session_bd, a_la_date=J(2026, 8, 19), foyer_id=principal.foyer_id)
    second = materialiser(session_bd, a_la_date=J(2026, 8, 19), foyer_id=principal.foyer_id)
    troisieme = materialiser(session_bd, a_la_date=J(2026, 8, 19), foyer_id=principal.foyer_id)

    assert (premier.creees, premier.deja_presentes) == (3, 0)
    assert (second.creees, second.deja_presentes) == (0, 3)
    assert second == troisieme
    assert len(depot.operations_visibles(session_bd, principal)) == 3


def test_la_base_refuse_un_doublon_meme_en_forcant(session_bd: Session) -> None:
    """La clé d'idempotence est portée par la BASE, pas par le test « existe déjà ».

    Sans cette contrainte, deux exécutions simultanées pourraient toutes deux constater
    l'absence puis toutes deux insérer.
    """
    principal, recurrence = foyer_avec_recurrence(session_bd, ancre=J(2026, 6, 5))
    materialiser(session_bd, a_la_date=J(2026, 6, 30), foyer_id=principal.foyer_id)

    with pytest.raises(IntegrityError, match="uq_operation_par_echeance"):
        depot_rec.materialiser_echeance(
            session_bd,
            recurrence=recurrence,  # type: ignore[arg-type]
            date_echeance=J(2026, 6, 5),
            etat=EtatOperation.A_CONFIRMER,
        )


def test_une_echeance_future_nest_pas_materialisee(session_bd: Session) -> None:
    """Une prévision qui deviendrait une opération réelle ferait entrer dans le solde
    de l'argent qui n'est pas encore parti."""
    principal, _ = foyer_avec_recurrence(session_bd, ancre=J(2026, 9, 5))
    bilan = materialiser(session_bd, a_la_date=J(2026, 8, 19), foyer_id=principal.foyer_id)
    assert bilan.creees == 0
    assert depot.operations_visibles(session_bd, principal) == []


def test_une_recurrence_terminee_narrete_de_produire(session_bd: Session) -> None:
    principal, _ = foyer_avec_recurrence(
        session_bd, ancre=J(2026, 6, 5), fin=J(2026, 7, 10)
    )
    bilan = materialiser(session_bd, a_la_date=J(2026, 8, 19), foyer_id=principal.foyer_id)
    assert bilan.creees == 2  # juin et juillet, pas août


def test_une_recurrence_desactivee_ne_produit_plus(session_bd: Session) -> None:
    principal, recurrence = foyer_avec_recurrence(session_bd, ancre=J(2026, 6, 5))
    depot_rec.desactiver_recurrence(session_bd, recurrence)  # type: ignore[arg-type]
    session_bd.commit()

    bilan = materialiser(session_bd, a_la_date=J(2026, 8, 19), foyer_id=principal.foyer_id)
    assert bilan.creees == 0


def test_temoin_confirmer_une_echeance_laisse_le_projete_invariant(
    session_bd: Session,
) -> None:
    """LE témoin central du projet, sur des données réelles.

    Confirmer une opération matérialisée doit faire varier le solde réel et la part à
    confirmer en SENS OPPOSÉS, et laisser le solde projeté strictement identique.
    """
    principal, _ = foyer_avec_recurrence(session_bd, ancre=J(2026, 8, 5))
    materialiser(session_bd, a_la_date=J(2026, 8, 19), foyer_id=principal.foyer_id)

    bornes = {"aujourd_hui": J(2026, 8, 19), "fin_de_fenetre": J(2026, 8, 31)}

    def soldes() -> tuple[int, int, int]:
        session_bd.expire_all()
        operations = depot.operations_pour_calcul(session_bd, principal)
        return (
            calculer(Agregat.SOLDE_REEL, operations, **bornes),
            calculer(Agregat.SOLDE_A_CONFIRMER, operations, **bornes),
            calculer(Agregat.SOLDE_PROJETE, operations, **bornes),
        )

    reel_avant, a_confirmer_avant, projete_avant = soldes()

    a_confirmer = depot_rec.operations_a_confirmer(session_bd, principal)
    assert len(a_confirmer) == 1
    depot_rec.confirmer_operation(session_bd, a_confirmer[0])
    session_bd.commit()

    reel_apres, a_confirmer_apres, projete_apres = soldes()

    assert projete_apres == projete_avant, "double comptage à la confirmation"
    assert reel_apres < reel_avant, "le débit confirmé doit entrer dans le solde réel"
    assert a_confirmer_apres > a_confirmer_avant, "la part à confirmer doit se vider"
    assert (reel_apres - reel_avant) == -(a_confirmer_apres - a_confirmer_avant)
    assert a_confirmer_apres == 0


def test_les_operations_a_confirmer_ne_fuient_pas_entre_foyers(session_bd: Session) -> None:
    principal, _ = foyer_avec_recurrence(session_bd, ancre=J(2026, 8, 5))
    materialiser(session_bd, a_la_date=J(2026, 8, 19), foyer_id=principal.foyer_id)

    autre_foyer, autre_utilisateur = creer_utilisateur(session_bd, "b@essai.fr", nom_foyer="B")
    autre = Principal(utilisateur_id=autre_utilisateur, foyer_id=autre_foyer)

    assert len(depot_rec.operations_a_confirmer(session_bd, principal)) == 1
    assert depot_rec.operations_a_confirmer(session_bd, autre) == []
