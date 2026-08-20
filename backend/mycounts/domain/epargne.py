"""Rythme d'épargne : ce qu'on place, ce qu'on reprend, mois par mois.

**Ce que ce module calcule** : pour chaque mois civil, la somme VERSÉE sur un compte
d'épargne et la somme REPRISE, séparément, ainsi que le solde à la fin du mois.

**Ce qu'il ne calcule PAS**, et pourquoi :

- Aucune projection. Un livret n'a ni échéance ni prélèvement : y projeter quoi que ce
  soit inventerait un argent qui n'arrive de nulle part.
- Aucun intérêt. Les taux changent, se calculent par quinzaine et diffèrent d'un produit à
  l'autre ; un chiffre approché sur de l'argent est pire qu'aucun chiffre.
- Aucun objectif. Réserver une part d'un compte à un projet serait un second système
  comptable à tenir d'accord avec le premier.

**La question à laquelle il répond.** « Est-ce que je place trop tôt dans le mois et je
suis obligé de me resservir ? » Elle se lit dans les mois où l'on a À LA FOIS versé et
repris : l'argent a fait l'aller-retour, donc il n'aurait pas dû partir. Additionner les
deux sous un solde net effacerait exactement ce signal — un mois à +300 puis −300 se lit
comme un mois à zéro, alors qu'il raconte une erreur de calibrage.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from mycounts.domain.montants import Cents


@dataclass(frozen=True)
class MouvementEpargne:
    """Un mouvement de virement sur un compte d'épargne.

    Volontairement détaché du modèle SQLAlchemy : le domaine se teste sans base.
    """

    montant: Cents
    """Signé. Positif = versé sur le compte, négatif = repris."""

    date_operation: dt.date


@dataclass(frozen=True)
class MoisDEpargne:
    premier_jour: dt.date
    verse: Cents
    """Toujours positif : somme des virements ENTRANTS du mois."""

    repris: Cents
    """Toujours POSITIF lui aussi, bien qu'il s'agisse de sorties.

    Deux grandeurs de même signe se comparent d'un coup d'œil et se dessinent en deux
    barres opposées. Un « repris » négatif obligerait chaque lecteur à retenir que le plus
    grand des deux est le plus petit.
    """

    solde_fin: Cents
    """Solde du compte au dernier jour du mois, tous mouvements confondus."""

    @property
    def net(self) -> Cents:
        return Cents(self.verse - self.repris)

    @property
    def aller_retour(self) -> bool:
        """Versé ET repris dans le même mois : l'argent n'aurait pas dû partir.

        C'est le seul signal que cet écran cherche. Il ne dit pas qu'une reprise est une
        faute — une dépense imprévue arrive — mais qu'elle a suivi un versement du même
        mois, ce qui est le symptôme d'un montant placé trop tôt ou trop gros.
        """
        return self.verse > 0 and self.repris > 0


def mois_precedents(jusqu_a: dt.date, combien: int) -> list[dt.date]:
    """Premiers jours des `combien` derniers mois civils, du plus ancien au plus récent.

    Le mois de `jusqu_a` est inclus : c'est celui qu'on est en train de vivre, et c'est
    précisément celui sur lequel on veut savoir si on a déjà dû se resservir.
    """
    mois: list[dt.date] = []
    annee, numero = jusqu_a.year, jusqu_a.month
    for _ in range(combien):
        mois.append(dt.date(annee, numero, 1))
        numero -= 1
        if numero == 0:
            annee, numero = annee - 1, 12
    return list(reversed(mois))


def _mois_de(jour: dt.date) -> dt.date:
    return dt.date(jour.year, jour.month, 1)


def repartir_par_mois(
    mouvements: Iterable[MouvementEpargne],
    *,
    solde_final: Cents,
    mois: Sequence[dt.date],
    tous_les_mouvements: Iterable[MouvementEpargne],
) -> list[MoisDEpargne]:
    """Versé, repris et solde de fin pour chacun des `mois` demandés.

    `mouvements` ne porte que les VIREMENTS — eux seuls disent ce qu'on a délibérément
    placé ou repris. Un intérêt versé par la banque ou une saisie manuelle changent le
    solde sans rien dire de l'effort, et les compter gonflerait un chiffre dont on se sert
    pour juger son propre rythme.

    `solde_final` et `tous_les_mouvements` servent au solde de fin de mois, qui lui compte
    TOUT : on remonte le temps depuis le solde d'aujourd'hui en défaisant les opérations
    postérieures. Recalculer chaque mois depuis l'origine relirait tout l'historique autant
    de fois qu'il y a de mois.
    """
    verses: dict[dt.date, int] = {m: 0 for m in mois}
    repris: dict[dt.date, int] = {m: 0 for m in mois}
    for mouvement in mouvements:
        cle = _mois_de(mouvement.date_operation)
        if cle not in verses:
            continue
        if mouvement.montant > 0:
            verses[cle] += int(mouvement.montant)
        else:
            repris[cle] -= int(mouvement.montant)

    # Solde à la fin de chaque mois, en remontant depuis aujourd'hui. On retire ce qui est
    # daté APRÈS la fin du mois considéré.
    posterieurs = sorted(tous_les_mouvements, key=lambda m: m.date_operation, reverse=True)
    soldes: dict[dt.date, int] = {}
    courant = int(solde_final)
    index = 0
    for premier in reversed(mois):
        fin = _fin_de_mois(premier)
        while index < len(posterieurs) and posterieurs[index].date_operation > fin:
            courant -= int(posterieurs[index].montant)
            index += 1
        soldes[premier] = courant

    return [
        MoisDEpargne(
            premier_jour=premier,
            verse=Cents(verses[premier]),
            repris=Cents(repris[premier]),
            solde_fin=Cents(soldes[premier]),
        )
        for premier in mois
    ]


def _fin_de_mois(premier: dt.date) -> dt.date:
    suivant = (
        dt.date(premier.year + 1, 1, 1)
        if premier.month == 12
        else dt.date(premier.year, premier.month + 1, 1)
    )
    return suivant - dt.timedelta(days=1)
