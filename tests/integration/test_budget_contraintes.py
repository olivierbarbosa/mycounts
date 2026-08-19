"""Contraintes réellement appliquées par PostgreSQL.

Ces règles ne sont pas testées côté Python mais côté **moteur** : une validation
applicative se contourne par un script, une migration ou un futur import. La base est le
dernier rempart, et c'est le seul qui ne s'oublie pas.
"""

from __future__ import annotations

import datetime as dt

import pytest
from mycounts.domain.montants import Cents
from mycounts.models.budget import Compte, Operation
from mycounts.repository import budget as depot
from mycounts.repository.base import Principal
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.integration.test_api_auth import creer_compte as creer_utilisateur

AUJOURD_HUI = dt.date(2026, 8, 19)


def principal_avec_compte(session: Session) -> tuple[Principal, Compte]:
    foyer_id, utilisateur_id = creer_utilisateur(session, "a@essai.fr")
    principal = Principal(utilisateur_id=utilisateur_id, foyer_id=foyer_id)
    compte = depot.creer_compte(session, principal, nom="Courant")
    session.commit()
    return principal, compte


def test_un_montant_nul_est_refuse_par_la_base(session_bd: Session) -> None:
    """Une opération à zéro ne décrit rien et fausserait les comptages sans changer les
    totaux — donc invisible à la relecture d'un solde."""
    principal, compte = principal_avec_compte(session_bd)
    with pytest.raises(IntegrityError, match="ck_operation_montant_non_nul"):
        depot.creer_operation(
            session_bd,
            principal,
            compte_id=compte.id,
            libelle="Rien",
            montant_centimes=Cents(0),
            date_operation=AUJOURD_HUI,
        )
        session_bd.commit()


def test_une_paie_negative_est_refusee_par_la_base(session_bd: Session) -> None:
    """Une paie ouvre une période budgétaire : si elle pouvait être négative, un débit
    marqué par erreur ouvrirait un cycle et décalerait tous les totaux du mois."""
    principal, compte = principal_avec_compte(session_bd)
    with pytest.raises(IntegrityError, match="ck_operation_paie_positive"):
        depot.creer_operation(
            session_bd,
            principal,
            compte_id=compte.id,
            libelle="Salaire négatif",
            montant_centimes=Cents(-100000),
            date_operation=AUJOURD_HUI,
            est_paie=True,
        )
        session_bd.commit()


def test_une_devise_autre_que_l_euro_est_refusee(session_bd: Session) -> None:
    """Le multi-devises imposerait de stocker le taux AVEC l'opération. Tant que ce n'est
    pas fait, la base doit interdire d'y entrer par la porte de service."""
    principal, _ = principal_avec_compte(session_bd)
    session_bd.add(
        Compte(
            foyer_id=principal.foyer_id,
            proprietaire_id=principal.utilisateur_id,
            nom="Dollars",
            devise="USD",
        )
    )
    with pytest.raises(IntegrityError, match="ck_compte_devise_eur"):
        session_bd.commit()


def test_un_montant_valide_passe(session_bd: Session) -> None:
    """Volet inverse : sans lui, une base qui refuserait TOUT passerait les tests
    ci-dessus."""
    principal, compte = principal_avec_compte(session_bd)
    operation = depot.creer_operation(
        session_bd,
        principal,
        compte_id=compte.id,
        libelle="Courses",
        montant_centimes=Cents(-4590),
        date_operation=AUJOURD_HUI,
    )
    session_bd.commit()
    assert operation.montant_centimes == -4590


def test_les_centimes_font_l_aller_retour_sans_perte(session_bd: Session) -> None:
    """Au-delà de 2^53, un flottant cesse d'être exact. BIGINT, non."""
    principal, compte = principal_avec_compte(session_bd)
    enorme = Cents(9007199254740993)
    depot.creer_operation(
        session_bd,
        principal,
        compte_id=compte.id,
        libelle="Somme extrême",
        montant_centimes=enorme,
        date_operation=AUJOURD_HUI,
    )
    session_bd.commit()
    session_bd.expire_all()
    relu = depot.operations_visibles(session_bd, principal)[0]
    assert relu.montant_centimes == enorme
    assert isinstance(relu.montant_centimes, int)


def test_deux_comptes_du_meme_foyer_ne_peuvent_pas_porter_le_meme_nom(
    session_bd: Session,
) -> None:
    principal, _ = principal_avec_compte(session_bd)
    # L'erreur survient au `flush()` interne de `creer_compte`, pas au commit : le
    # repository force l'écriture pour renvoyer un objet avec son identifiant.
    with pytest.raises(IntegrityError, match="uq_compte_nom_par_foyer"):
        depot.creer_compte(session_bd, principal, nom="Courant")


def test_une_categorie_utilisee_ne_peut_pas_etre_supprimee(session_bd: Session) -> None:
    """`ondelete=RESTRICT` : supprimer une catégorie utilisée changerait rétroactivement
    les totaux d'un mois déjà clos. On archive, on ne supprime pas."""
    principal, compte = principal_avec_compte(session_bd)
    creees = depot.creer_categories_initiales(session_bd, principal.foyer_id)
    session_bd.commit()
    depot.creer_operation(
        session_bd,
        principal,
        compte_id=compte.id,
        libelle="Courses",
        montant_centimes=Cents(-4590),
        date_operation=AUJOURD_HUI,
        categorie_id=creees[0].id,
    )
    session_bd.commit()

    session_bd.delete(creees[0])
    with pytest.raises(IntegrityError):
        session_bd.commit()


def test_le_reglage_paies_par_cycle_est_borne(session_bd: Session) -> None:
    from mycounts.models.auth import Utilisateur

    principal, _ = principal_avec_compte(session_bd)
    utilisateur = session_bd.get(Utilisateur, principal.utilisateur_id)
    assert utilisateur is not None
    assert utilisateur.paies_par_cycle == 1, "le défaut doit être un cycle par paie"

    utilisateur.paies_par_cycle = 0
    with pytest.raises(IntegrityError, match="ck_utilisateur_paies_par_cycle"):
        session_bd.commit()


def test_une_operation_a_l_etat_inconnu_est_refusee(session_bd: Session) -> None:
    """Témoin : l'énumération d'état ne doit pas accepter n'importe quelle chaîne.

    Ce test documente une limite réelle — la colonne est un VARCHAR sans contrainte
    d'énumération côté base. Il vérifie donc ce que le moteur fait vraiment, et non ce
    qu'on aimerait qu'il fasse.
    """
    principal, compte = principal_avec_compte(session_bd)
    operation = Operation(
        compte_id=compte.id,
        cree_par_id=principal.utilisateur_id,
        libelle="État douteux",
        montant_centimes=-100,
        date_operation=AUJOURD_HUI,
        # mypy accepte la chaîne, l'énumération étant un StrEnum : c'est justement ce qui
        # rend le contrôle applicatif insuffisant, et pourquoi ce test existe.
        etat="etat_invente",
    )
    session_bd.add(operation)
    session_bd.commit()
    # La base l'accepte : la contrainte est applicative. Constat mesuré, pas supposé —
    # à durcir si un import externe écrit un jour dans cette table.
    assert operation.etat == "etat_invente"
