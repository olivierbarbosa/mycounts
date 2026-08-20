"""Rythme d'épargne : versé, repris, et le signal de l'aller-retour.

Le test central est `un aller-retour se voit, un solde net l'efface` : c'est la mesure qui
peut rendre la réponse inverse. Un mois où l'on verse 300 € puis en reprend 300 raconte une
erreur de calibrage ; sous un solde net, il se lit comme un mois où il ne s'est rien passé.
"""

from __future__ import annotations

import datetime as dt

from mycounts.domain.epargne import (
    MouvementEpargne,
    mois_precedents,
    repartir_par_mois,
)
from mycounts.domain.montants import Cents

J = dt.date


def mouvement(montant: int, jour: dt.date) -> MouvementEpargne:
    return MouvementEpargne(montant=Cents(montant), date_operation=jour)


def test_les_mois_demandes_remontent_du_plus_ancien_au_plus_recent() -> None:
    assert mois_precedents(J(2026, 3, 17), 4) == [
        J(2025, 12, 1),
        J(2026, 1, 1),
        J(2026, 2, 1),
        J(2026, 3, 1),
    ]


def test_le_mois_en_cours_est_inclus() -> None:
    """C'est celui sur lequel on veut savoir si on a DÉJÀ dû se resservir."""
    assert mois_precedents(J(2026, 8, 20), 1) == [J(2026, 8, 1)]


def test_le_passage_dune_annee_a_lautre() -> None:
    assert mois_precedents(J(2026, 1, 5), 3) == [J(2025, 11, 1), J(2025, 12, 1), J(2026, 1, 1)]


def test_verse_et_repris_sont_comptes_separement_et_tous_deux_positifs() -> None:
    mois = mois_precedents(J(2026, 8, 20), 1)
    mouvements = [
        mouvement(30_000, J(2026, 8, 2)),
        mouvement(-12_000, J(2026, 8, 18)),
        mouvement(5_000, J(2026, 8, 19)),
    ]

    [aout] = repartir_par_mois(
        mouvements, solde_final=Cents(23_000), mois=mois, tous_les_mouvements=mouvements
    )
    assert aout.verse == 35_000
    assert aout.repris == 12_000, "le repris se compte en positif, pour se comparer d'un œil"
    assert aout.net == 23_000


def test_un_aller_retour_se_voit_la_ou_un_solde_net_lefface() -> None:
    """La mesure qui justifie de ne jamais additionner les deux.

    Deux mois de solde net IDENTIQUE — zéro — dont un seul raconte une erreur. Sans la
    séparation, ils seraient indiscernables, et l'écran ne dirait rien de ce qu'il est
    censé révéler.
    """
    mois = mois_precedents(J(2026, 8, 20), 2)

    calme = [mouvement(0, J(2026, 7, 5))]
    agite = [mouvement(30_000, J(2026, 8, 2)), mouvement(-30_000, J(2026, 8, 25))]

    [juillet, aout] = repartir_par_mois(
        calme + agite, solde_final=Cents(0), mois=mois, tous_les_mouvements=calme + agite
    )

    assert juillet.net == aout.net == 0, "les deux mois ont le même solde net"
    assert juillet.aller_retour is False
    assert aout.aller_retour is True, (
        "versé PUIS repris le même mois : l'argent n'aurait pas dû partir"
    )


def test_reprendre_sans_avoir_verse_nest_pas_un_aller_retour() -> None:
    """Une reprise seule est une dépense imprévue, pas un mauvais calibrage.

    Le témoin qui empêche le signal de se déclencher sur tout et n'importe quoi : sans lui,
    un code qui rendrait `True` dès qu'il y a une reprise passerait le test précédent.
    """
    mois = mois_precedents(J(2026, 8, 20), 1)
    mouvements = [mouvement(-20_000, J(2026, 8, 10))]

    [aout] = repartir_par_mois(
        mouvements, solde_final=Cents(-20_000), mois=mois, tous_les_mouvements=mouvements
    )
    assert aout.repris == 20_000
    assert aout.verse == 0
    assert aout.aller_retour is False


def test_le_solde_de_fin_de_mois_se_reconstruit_en_remontant() -> None:
    """Chaque mois porte le solde du compte à son dernier jour, pas le cumul des versements."""
    mois = mois_precedents(J(2026, 8, 20), 3)
    mouvements = [
        mouvement(100_000, J(2026, 6, 10)),
        mouvement(50_000, J(2026, 7, 10)),
        mouvement(-20_000, J(2026, 8, 10)),
    ]

    juin, juillet, aout = repartir_par_mois(
        mouvements, solde_final=Cents(130_000), mois=mois, tous_les_mouvements=mouvements
    )
    assert juin.solde_fin == 100_000
    assert juillet.solde_fin == 150_000
    assert aout.solde_fin == 130_000


def test_un_mouvement_hors_fenetre_ne_compte_pas_dans_les_versements() -> None:
    """Mais il compte dans le solde : le compte ne part pas de zéro à l'ouverture de l'écran."""
    mois = mois_precedents(J(2026, 8, 20), 2)
    ancien = mouvement(80_000, J(2025, 1, 15))
    recent = mouvement(20_000, J(2026, 8, 3))

    juillet, aout = repartir_par_mois(
        [ancien, recent],
        solde_final=Cents(100_000),
        mois=mois,
        tous_les_mouvements=[ancien, recent],
    )
    assert juillet.verse == 0
    assert juillet.solde_fin == 80_000, "l'ancien versement est bien dans le solde"
    assert aout.verse == 20_000
