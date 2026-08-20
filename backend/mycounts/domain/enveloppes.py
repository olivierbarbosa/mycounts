"""Enveloppes : découper l'épargne pour savoir combien est disponible, et pour quoi.

**Ce qu'une enveloppe est.** Une part réservée de l'épargne, rattachée à une catégorie de
dépense. « J'ai 3 000 € de côté, dont 900 pour les impôts et 800 pour les vacances. »

**Ce qu'elle n'est PAS.** Un compte. Une enveloppe ne déplace aucun argent : elle nomme
une part de ce qui est déjà sur les livrets. C'est ce qui l'empêche de devenir un second
système comptable — il n'y a rien à tenir d'accord, puisqu'il n'y a qu'une seule somme.

**L'invariant qui décide de tout.** La somme des enveloppes ne peut jamais dépasser
l'épargne réelle. Sans lui, on se promet de l'argent qui n'existe pas, et l'écran finit
par annoncer 900 € d'impôts provisionnés sur un livret qui n'en contient que 400 — c'est
l'échec classique de la méthode des enveloppes, et il est silencieux.

Le **non affecté** est donc une grandeur de premier plan, pas un reste : c'est la seule
qui dise ce qu'on peut encore réserver.
"""

from __future__ import annotations

from dataclasses import dataclass

from mycounts.domain.montants import Cents


@dataclass(frozen=True)
class Enveloppe:
    nom: str
    montant: Cents
    """Part de l'épargne réservée. Toujours positive."""


@dataclass(frozen=True)
class Repartition:
    """État d'une épargne découpée en enveloppes."""

    epargne_totale: Cents
    affecte: Cents
    enveloppes: tuple[Enveloppe, ...]

    @property
    def non_affecte(self) -> Cents:
        """Ce qui reste libre. Peut être NÉGATIF.

        Négatif signifie que l'épargne a fondu sous ce qui était réservé — une reprise a
        entamé des enveloppes. Le forcer à zéro cacherait exactement ce qu'il faut voir :
        que les promesses ne sont plus couvertes.
        """
        return Cents(self.epargne_totale - self.affecte)

    @property
    def decouvert(self) -> bool:
        return self.non_affecte < 0

    def part(self, enveloppe: Enveloppe) -> int:
        """Part de l'épargne totale occupée par cette enveloppe, en pourcentage tronqué.

        Sur l'épargne TOTALE et non sur l'affecté : une enveloppe doit se comparer à ce
        qu'on possède, pas à ce qu'on a déjà distribué. Rapportée à l'affecté, la dernière
        enveloppe créée paraîtrait grossir à mesure qu'on en supprime d'autres.
        """
        if self.epargne_totale <= 0:
            return 0
        return int(enveloppe.montant) * 100 // int(self.epargne_totale)


def repartir(epargne_totale: Cents, enveloppes: tuple[Enveloppe, ...]) -> Repartition:
    return Repartition(
        epargne_totale=epargne_totale,
        affecte=Cents(sum(int(e.montant) for e in enveloppes)),
        enveloppes=enveloppes,
    )


def place_disponible(
    epargne_totale: Cents, enveloppes: tuple[Enveloppe, ...], *, sauf: str | None = None
) -> Cents:
    """Ce qu'on peut encore réserver, en ignorant éventuellement une enveloppe.

    `sauf` sert à la MODIFICATION : réévaluer une enveloppe de 200 à 300 ne doit pas se
    heurter à ses propres 200 déjà comptés. Sans ce paramètre, augmenter une enveloppe
    serait refusé alors que la place existe.
    """
    deja = sum(int(e.montant) for e in enveloppes if e.nom != sauf)
    return Cents(int(epargne_totale) - deja)
