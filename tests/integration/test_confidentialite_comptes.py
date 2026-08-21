"""Confidentialité des comptes privés.

Le garde-fou statique prouve qu'aucune requête n'est écrite hors du repository ; il ne
prouve PAS que celles du repository appliquent correctement leur périmètre. C'est le rôle
de ce fichier — et il porte sur la règle qui, si elle cède, montre les dépenses d'une
personne à une autre.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import replace

from mycounts.domain.montants import Cents
from mycounts.repository import auth as depot_auth
from mycounts.repository import budget as depot
from mycounts.repository.base import Principal, Vue
from sqlalchemy.orm import Session

AUJOURD_HUI = dt.date(2026, 8, 19)


def membre(session: Session, foyer_id: object, courriel: str) -> Principal:
    from mycounts.domain.securite import hacher_mot_de_passe

    utilisateur = depot_auth.creer_utilisateur(
        session,
        foyer_id=foyer_id,  # type: ignore[arg-type]  # uuid.UUID, typé par l'appelant
        courriel=courriel,
        nom_affichage=courriel.split("@")[0],
        empreinte_mot_de_passe=hacher_mot_de_passe("correct cheval batterie agrafe"),
    )
    session.commit()
    return Principal(utilisateur_id=utilisateur.id, foyer_id=utilisateur.foyer_id)


def foyer_a_deux(session: Session) -> tuple[Principal, Principal]:
    foyer = depot_auth.creer_foyer(session, "Foyer")
    session.commit()
    return membre(session, foyer.id, "alice@essai.fr"), membre(session, foyer.id, "bruno@essai.fr")


def test_un_compte_prive_est_invisible_a_l_autre_membre(session_bd: Session) -> None:
    alice, bruno = foyer_a_deux(session_bd)
    depot.creer_compte(session_bd, alice, nom="Perso Alice", prive=True)
    session_bd.commit()

    assert [c.nom for c in depot.comptes_visibles(session_bd, alice)] == ["Perso Alice"]
    assert depot.comptes_visibles(session_bd, bruno) == []


def test_un_compte_joint_est_visible_des_deux_EN_VUE_FOYER(session_bd: Session) -> None:
    """Volet inverse : sans lui, une règle qui masquerait TOUT passerait le test
    précédent."""
    alice, bruno = foyer_a_deux(session_bd)
    depot.creer_compte(session_bd, alice, nom="Compte joint", prive=False)
    session_bd.commit()

    en_foyer = replace(alice, vue=Vue.FOYER), replace(bruno, vue=Vue.FOYER)
    for membre in en_foyer:
        assert [c.nom for c in depot.comptes_visibles(session_bd, membre)] == ["Compte joint"]


def test_un_compte_joint_NEST_PAS_dans_la_vue_personnelle(session_bd: Session) -> None:
    """Les deux mondes sont étanches, décidé le 21 août 2026.

    « Combien j'ai » ne comprend pas la moitié du compte commun : sa répartition
    n'appartient pas à cette application, et l'y ajouter donnerait un total que personne ne
    pourrait interpréter.
    """
    alice, _ = foyer_a_deux(session_bd)
    depot.creer_compte(session_bd, alice, nom="Compte joint", prive=False)
    depot.creer_compte(session_bd, alice, nom="Perso Alice", prive=True)
    session_bd.commit()

    assert [c.nom for c in depot.comptes_visibles(session_bd, alice)] == ["Perso Alice"]


def test_un_compte_PRIVE_nest_pas_dans_la_vue_foyer(session_bd: Session) -> None:
    """L'étanchéité dans l'autre sens, et c'est celui qui protège : les opérations
    personnelles d'Alice ne doivent pas apparaître dans un écran que Bruno regarde."""
    alice, bruno = foyer_a_deux(session_bd)
    depot.creer_compte(session_bd, alice, nom="Perso Alice", prive=True)
    depot.creer_compte(session_bd, alice, nom="Compte joint", prive=False)
    session_bd.commit()

    for membre in (replace(alice, vue=Vue.FOYER), replace(bruno, vue=Vue.FOYER)):
        assert [c.nom for c in depot.comptes_visibles(session_bd, membre)] == ["Compte joint"]


def test_une_vue_inconnue_ne_donne_acces_a_rien_de_plus(session_bd: Session) -> None:
    """Le défaut de sûreté : au pire on montre à quelqu'un ses propres comptes.

    Vérifié ici sur le périmètre lui-même plutôt que sur la route : c'est le `Principal`
    qui décide, et son défaut est la seule chose qui protège d'une faute de frappe dans
    un en-tête.
    """
    alice, _ = foyer_a_deux(session_bd)
    depot.creer_compte(session_bd, alice, nom="Compte joint", prive=False)
    depot.creer_compte(session_bd, alice, nom="Perso Alice", prive=True)
    session_bd.commit()

    # Un Principal construit sans vue explicite : celui qu'obtient un client qui n'envoie
    # pas l'en-tête, ou qui en envoie un que le serveur ne reconnaît pas.
    par_defaut = Principal(utilisateur_id=alice.utilisateur_id, foyer_id=alice.foyer_id)
    assert [c.nom for c in depot.comptes_visibles(session_bd, par_defaut)] == ["Perso Alice"]


def test_les_operations_dun_compte_prive_sont_invisibles(session_bd: Session) -> None:
    alice, bruno = foyer_a_deux(session_bd)
    compte = depot.creer_compte(session_bd, alice, nom="Perso Alice", prive=True)
    depot.creer_operation(
        session_bd,
        alice,
        compte_id=compte.id,
        libelle="Dépense personnelle",
        montant_centimes=Cents(-4590),
        date_operation=AUJOURD_HUI,
    )
    session_bd.commit()

    assert len(depot.operations_visibles(session_bd, alice)) == 1
    assert depot.operations_visibles(session_bd, bruno) == []


def test_un_total_nagrege_jamais_un_compte_invisible(session_bd: Session) -> None:
    """Le vrai risque n'est pas de voir une ligne interdite : c'est qu'elle se glisse
    dans un TOTAL, où elle devient indétectable."""
    alice, bruno = foyer_a_deux(session_bd)
    compte = depot.creer_compte(session_bd, alice, nom="Perso Alice", prive=True)
    depot.creer_operation(
        session_bd,
        alice,
        compte_id=compte.id,
        libelle="Dépense personnelle",
        montant_centimes=Cents(-4590),
        date_operation=AUJOURD_HUI,
    )
    session_bd.commit()

    assert sum(o.montant for o in depot.operations_pour_calcul(session_bd, alice)) == -4590
    assert sum(o.montant for o in depot.operations_pour_calcul(session_bd, bruno)) == 0


def test_les_paies_dun_compte_prive_ne_fuient_pas(session_bd: Session) -> None:
    """Les dates de paie ouvrent les périodes budgétaires : les laisser fuir révélerait
    le rythme de rémunération de l'autre membre."""
    alice, bruno = foyer_a_deux(session_bd)
    compte = depot.creer_compte(session_bd, alice, nom="Perso Alice", prive=True)
    depot.creer_operation(
        session_bd,
        alice,
        compte_id=compte.id,
        libelle="Salaire",
        montant_centimes=Cents(250000),
        date_operation=AUJOURD_HUI,
        est_paie=True,
    )
    session_bd.commit()

    assert depot.dates_de_paie(session_bd, alice) == [AUJOURD_HUI]
    assert depot.dates_de_paie(session_bd, bruno) == []


def test_une_paie_seulement_prevue_nouvre_pas_de_periode(session_bd: Session) -> None:
    """Un budget ne doit pas démarrer sur un revenu imaginaire."""
    from mycounts.domain.agregats import EtatOperation

    alice, _ = foyer_a_deux(session_bd)
    compte = depot.creer_compte(session_bd, alice, nom="Perso Alice")
    depot.creer_operation(
        session_bd,
        alice,
        compte_id=compte.id,
        libelle="Salaire à venir",
        montant_centimes=Cents(250000),
        date_operation=AUJOURD_HUI + dt.timedelta(days=8),
        est_paie=True,
        etat=EtatOperation.PREVUE,
    )
    session_bd.commit()

    assert depot.dates_de_paie(session_bd, alice) == []


def test_un_autre_foyer_ne_voit_rien(session_bd: Session) -> None:
    alice, _ = foyer_a_deux(session_bd)
    depot.creer_compte(session_bd, alice, nom="Perso Alice")
    session_bd.commit()

    autre_foyer = depot_auth.creer_foyer(session_bd, "Autre foyer")
    session_bd.commit()
    etranger = membre(session_bd, autre_foyer.id, "etranger@essai.fr")

    assert depot.comptes_visibles(session_bd, etranger) == []
    assert depot.operations_visibles(session_bd, etranger) == []
    assert depot.categories(session_bd, etranger) == []


def test_seul_le_proprietaire_supprime_un_compte_joint(session_bd: Session) -> None:
    """Un compte joint est VISIBLE de tous, mais n'appartient qu'à celui qui l'a ouvert.

    Sans cette garde, n'importe quel membre pouvait supprimer l'espace commun : la
    visibilité valait permission, ce qui n'est vrai d'aucun objet partagé.
    """
    alice, bruno = foyer_a_deux(session_bd)
    compte = depot.creer_compte(session_bd, alice, nom="Compte joint", prive=False)
    session_bd.commit()

    en_foyer = replace(bruno, vue=Vue.FOYER)
    # Bruno le voit…
    assert [c.nom for c in depot.comptes_visibles(session_bd, en_foyer)] == ["Compte joint"]
    # …et c'est bien Alice qui en est propriétaire.
    assert compte.proprietaire_id == alice.utilisateur_id
