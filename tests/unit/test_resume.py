"""Tests du résumé de période."""

from __future__ import annotations

import datetime as dt

from mycounts.domain.agregats import EtatOperation, OperationCalcul
from mycounts.domain.montants import Cents
from mycounts.domain.resume import resumer

J = dt.date
AUJOURD_HUI = J(2026, 8, 19)
PAIE = J(2026, 7, 28)


def op(
    montant: int, jour: dt.date, etat: EtatOperation = EtatOperation.CONFIRMEE
) -> OperationCalcul:
    return OperationCalcul(montant=Cents(montant), date_operation=jour, etat=etat)


def test_le_resume_utilise_la_periode_de_paie_et_non_le_mois_civil() -> None:
    resultat = resumer([], [PAIE], aujourd_hui=AUJOURD_HUI)
    assert resultat.periode.debut == PAIE
    assert resultat.periode.debut != J(2026, 8, 1), "le mois civil n'est pas la période"
    assert resultat.periode.fin_estimee, "sans paie suivante, la fin est une estimation"


def test_les_quatre_grandeurs_sont_coherentes() -> None:
    operations = [
        op(250000, PAIE),
        op(-4590, AUJOURD_HUI),
        op(-12000, AUJOURD_HUI, EtatOperation.A_CONFIRMER),
        op(-3000, J(2026, 8, 25), EtatOperation.PREVUE),
    ]
    r = resumer(operations, [PAIE], aujourd_hui=AUJOURD_HUI)

    assert r.solde_reel == 250000 - 4590
    assert r.solde_a_confirmer == -12000
    assert r.solde_projete == 250000 - 4590 - 12000 - 3000
    assert r.depenses_de_periode == -4590 - 12000
    assert r.ecart_a_confirmer == r.solde_projete - r.solde_reel


def test_temoin_confirmer_une_echeance_laisse_le_projete_intact() -> None:
    """Le témoin central, rejoué au niveau du résumé.

    Il ne suffit pas qu'il tienne dans `agregats` : c'est ce module que les écrans
    appellent, et c'est donc ici que le double comptage se verrait.
    """
    avant = [op(250000, PAIE), op(-12000, AUJOURD_HUI, EtatOperation.A_CONFIRMER)]
    apres = [op(250000, PAIE), op(-12000, AUJOURD_HUI, EtatOperation.CONFIRMEE)]

    a = resumer(avant, [PAIE], aujourd_hui=AUJOURD_HUI)
    b = resumer(apres, [PAIE], aujourd_hui=AUJOURD_HUI)

    assert a.solde_projete == b.solde_projete, "double comptage à la confirmation"
    assert b.solde_reel < a.solde_reel
    assert b.solde_a_confirmer > a.solde_a_confirmer
    assert b.ecart_a_confirmer == 0, "tout confirmé : projeté et réel doivent coïncider"


def test_sans_operation_tout_est_a_zero() -> None:
    r = resumer([], [PAIE], aujourd_hui=AUJOURD_HUI)
    assert (r.solde_projete, r.solde_reel, r.solde_a_confirmer, r.depenses_de_periode) == (
        0,
        0,
        0,
        0,
    )


def test_une_echeance_hors_periode_nest_pas_projetee() -> None:
    """La fenêtre de projection s'arrête à la fin de la période, pas à l'infini."""
    hors = op(-99999, J(2026, 10, 15), EtatOperation.PREVUE)
    r = resumer([hors], [PAIE], aujourd_hui=AUJOURD_HUI)
    assert r.solde_projete == 0


def test_plusieurs_paies_par_cycle_changent_la_fenetre() -> None:
    """Témoin : le réglage doit avoir un effet observable, sinon il ne sert à rien."""
    paies = [J(2026, 8, 1), J(2026, 8, 15)]
    un = resumer([], paies, aujourd_hui=AUJOURD_HUI, paies_par_cycle=1)
    deux = resumer([], paies, aujourd_hui=AUJOURD_HUI, paies_par_cycle=2)
    assert un.periode.debut == J(2026, 8, 15)
    assert deux.periode.debut == J(2026, 8, 1)
    assert un.periode != deux.periode
