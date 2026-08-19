"""Tests des plafonds.

Le contrôle central est `test_temoin_le_consomme_nabsorbe_pas_les_echeances` : consommé
et à-venir doivent rester deux grandeurs distinctes. Les additionner donnerait un chiffre
plus complet mais faux à lire.
"""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from mycounts.domain.agregats import EtatOperation
from mycounts.domain.montants import Cents
from mycounts.domain.plafonds import EtatPlafond, OperationCategorisee, etat_du_plafond

J = dt.date
AUJOURD_HUI = J(2026, 8, 19)
FIN = J(2026, 8, 31)
COURSES = uuid.uuid4()
TRANSPORT = uuid.uuid4()


def op(
    montant: int,
    *,
    categorie: uuid.UUID | None = COURSES,
    jour: dt.date = AUJOURD_HUI,
    etat: EtatOperation = EtatOperation.CONFIRMEE,
) -> OperationCategorisee:
    return OperationCategorisee(
        montant=Cents(montant), date_operation=jour, etat=etat, categorie_id=categorie
    )


def etat(operations: list[OperationCategorisee], limite: int = 40000) -> EtatPlafond:
    return etat_du_plafond(
        categorie_id=COURSES,
        limite=Cents(limite),
        operations=operations,
        aujourd_hui=AUJOURD_HUI,
        fin_de_fenetre=FIN,
    )


# --- Le témoin central -----------------------------------------------------------


def test_temoin_le_consomme_nabsorbe_pas_les_echeances() -> None:
    """Consommé et à-venir sont deux grandeurs distinctes, jamais fondues.

    Dire « vous avez dépensé 380 € » alors que 150 € ne sont pas encore partis est
    exactement la confusion qui fait cesser de croire l'outil.
    """
    resultat = etat(
        [
            op(-23000),
            op(-15000, jour=J(2026, 8, 25), etat=EtatOperation.PREVUE),
        ]
    )
    assert resultat.consomme == 23000
    assert resultat.a_venir == 15000
    assert resultat.consomme != resultat.consomme + resultat.a_venir


def test_temoin_les_deux_grandeurs_reagissent_a_des_donnees_differentes() -> None:
    """Contrôle inverse : sans échéance prévue, l'à-venir est nul et ne recopie pas le
    consommé. Sans lui, une implémentation qui renverrait deux fois la même valeur
    passerait le témoin ci-dessus."""
    resultat = etat([op(-23000)])
    assert resultat.consomme == 23000
    assert resultat.a_venir == 0


# --- Consommation ----------------------------------------------------------------


def test_les_operations_dune_autre_categorie_sont_ignorees() -> None:
    resultat = etat([op(-10000), op(-99999, categorie=TRANSPORT)])
    assert resultat.consomme == 10000


def test_les_operations_sans_categorie_sont_ignorees() -> None:
    """Une dépense non classée ne consomme aucun plafond : l'imputer au hasard fausserait
    silencieusement le suivi."""
    resultat = etat([op(-10000), op(-5000, categorie=None)])
    assert resultat.consomme == 10000


def test_les_operations_a_confirmer_comptent() -> None:
    """L'argent est parti : l'ignorer sous-estimerait la consommation."""
    resultat = etat([op(-10000), op(-4000, etat=EtatOperation.A_CONFIRMER)])
    assert resultat.consomme == 14000


def test_un_revenu_sur_la_categorie_ne_reduit_pas_la_consommation() -> None:
    """Un remboursement encaissé ne « rend » pas du plafond : sinon un virement reçu
    ferait disparaître des dépenses réelles du suivi."""
    resultat = etat([op(-10000), op(5000)])
    assert resultat.consomme == 10000


def test_un_solde_douverture_ne_consomme_aucun_plafond() -> None:
    ouverture = OperationCategorisee(
        montant=Cents(-15000),
        date_operation=AUJOURD_HUI,
        etat=EtatOperation.CONFIRMEE,
        categorie_id=COURSES,
        est_ouverture=True,
    )
    assert etat([ouverture, op(-4000)]).consomme == 4000


# --- Dépassement et pourcentage --------------------------------------------------


@pytest.mark.parametrize(
    ("depense", "limite", "part", "depasse"),
    [
        (0, 40000, 0, False),
        (-10000, 40000, 25, False),
        (-39900, 40000, 99, False),
        (-40000, 40000, 100, False),  # atteint mais pas dépassé
        (-40001, 40000, 100, True),
        (-80000, 40000, 200, True),
    ],
)
def test_part_consommee_et_depassement(
    depense: int, limite: int, part: int, depasse: bool
) -> None:
    resultat = etat([op(depense)] if depense else [], limite=limite)
    assert resultat.part_consommee == part
    assert resultat.depasse is depasse


def test_la_part_consommee_est_tronquee_pas_arrondie() -> None:
    """À 99,7 %, on affiche 99 : l'interface ne doit jamais annoncer 100 % avant que la
    limite soit réellement atteinte."""
    resultat = etat([op(-39900)], limite=40000)
    assert resultat.part_consommee == 99
    assert isinstance(resultat.part_consommee, int)


def test_le_restant_devient_negatif_au_depassement() -> None:
    assert etat([op(-30000)]).restant == 10000
    assert etat([op(-45000)]).restant == -5000


def test_lalerte_anticipee_tient_compte_des_echeances() -> None:
    """Être à 300 € sur 400 paraît confortable, jusqu'à savoir que 150 € tombent avant
    la fin de la période. C'est l'alerte réellement utile."""
    resultat = etat(
        [op(-30000), op(-15000, jour=J(2026, 8, 25), etat=EtatOperation.PREVUE)]
    )
    assert resultat.depasse is False
    assert resultat.depasse_avec_les_echeances is True


def test_une_echeance_hors_periode_nentre_pas_dans_lalerte() -> None:
    resultat = etat(
        [op(-30000), op(-15000, jour=J(2026, 9, 15), etat=EtatOperation.PREVUE)]
    )
    assert resultat.a_venir == 0
    assert resultat.depasse_avec_les_echeances is False


def test_aucune_operation_donne_un_etat_vierge() -> None:
    resultat = etat([])
    assert (resultat.consomme, resultat.a_venir, resultat.part_consommee) == (0, 0, 0)
    assert resultat.restant == resultat.limite
