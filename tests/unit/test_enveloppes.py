"""Répartition de l'épargne en enveloppes.

Le test central est `le non affecté devient négatif quand l'épargne fond` : c'est la
mesure qui peut rendre la réponse inverse. Forcer ce reste à zéro cacherait exactement ce
qu'il faut voir — que les promesses ne sont plus couvertes par ce qui est en banque.
"""

from __future__ import annotations

from mycounts.domain.enveloppes import Enveloppe, place_disponible, repartir
from mycounts.domain.montants import Cents


def enveloppe(nom: str, montant: int) -> Enveloppe:
    return Enveloppe(nom=nom, montant=Cents(montant))


def test_le_non_affecte_est_ce_qui_reste_libre() -> None:
    etat = repartir(
        Cents(300_000), (enveloppe("Impôts", 90_000), enveloppe("Vacances", 80_000))
    )
    assert etat.affecte == 170_000
    assert etat.non_affecte == 130_000
    assert etat.decouvert is False


def test_le_non_affecte_devient_negatif_quand_lepargne_fond() -> None:
    """Une reprise a entamé des enveloppes : il faut que ça se voie.

    Le témoin oppose deux répartitions AUX MÊMES enveloppes, dont seule l'épargne change.
    Sans lui, un code qui bornerait le reste à zéro passerait le test précédent.
    """
    enveloppes = (enveloppe("Impôts", 90_000), enveloppe("Vacances", 80_000))

    confortable = repartir(Cents(300_000), enveloppes)
    entame = repartir(Cents(120_000), enveloppes)

    assert confortable.non_affecte == 130_000
    assert entame.non_affecte == -50_000, "borner à zéro cacherait que les promesses sautent"
    assert entame.decouvert is True


def test_la_part_se_calcule_sur_lepargne_totale_pas_sur_laffecte() -> None:
    """Rapportée à l'affecté, la dernière enveloppe grossirait à mesure qu'on en supprime.

    Deux répartitions de MÊME enveloppe et de même épargne, l'une avec une seconde
    enveloppe et l'autre sans : la part de la première ne doit pas bouger.
    """
    impots = enveloppe("Impôts", 90_000)

    seule = repartir(Cents(300_000), (impots,))
    accompagnee = repartir(Cents(300_000), (impots, enveloppe("Vacances", 80_000)))

    assert seule.part(impots) == 30
    assert accompagnee.part(impots) == 30, "la part ne dépend pas des voisines"


def test_une_epargne_nulle_ne_divise_pas_par_zero() -> None:
    etat = repartir(Cents(0), (enveloppe("Impôts", 90_000),))
    assert etat.part(etat.enveloppes[0]) == 0
    assert etat.decouvert is True


def test_la_place_disponible_ignore_lenveloppe_quon_modifie() -> None:
    """Sinon, augmenter une enveloppe se heurterait à ses propres euros déjà comptés.

    Le témoin est la première assertion : sans `sauf`, la place vaudrait 130 000 et
    porter l'enveloppe à 200 000 serait refusé alors que l'épargne le permet largement.
    """
    enveloppes = (enveloppe("Impôts", 90_000), enveloppe("Vacances", 80_000))

    assert place_disponible(Cents(300_000), enveloppes) == 130_000
    assert place_disponible(Cents(300_000), enveloppes, sauf="Impôts") == 220_000
