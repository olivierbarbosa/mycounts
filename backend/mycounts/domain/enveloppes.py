"""Enveloppes : découper l'épargne pour savoir combien est disponible, et pour quoi.

**Ce qu'une enveloppe est.** Une part réservée de l'argent, rattachée à une catégorie de
dépense. « J'ai 3 000 € de côté, dont 900 pour les impôts et 800 pour les vacances. »

**Ce qu'elle n'est PAS.** Un compte. Une enveloppe ne déplace aucun argent :

    Une allocation vers une enveloppe ne crée JAMAIS de mouvement bancaire.

Le compte dit où l'argent EST, l'enveloppe à quoi il est PROMIS, le budget ce qu'on prévoit
d'y mettre. Confondre les trois est l'erreur que tout le module cherche à rendre
impossible.

**Aucun solde n'est stocké.** Il se recalcule depuis un journal de mouvements, exactement
comme le solde d'un compte se recalcule depuis ses opérations. Corriger une enveloppe ne
consiste donc jamais à écrire une nouvelle valeur, mais à ajouter un mouvement — ce qui
laisse un historique lisible six mois plus tard.

**Tous les montants sont positifs.** C'est le TYPE du mouvement qui dit s'il crédite ou
débite. Un montant signé rendrait possible une allocation négative, c'est-à-dire une
reprise déguisée, invisible dans un journal filtré par type.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from mycounts.domain.montants import Cents


class TypeMouvement(StrEnum):
    """Nature d'un mouvement d'enveloppe. Décide du sens, jamais le montant."""

    ALLOCATION = "allocation"
    """Argent réservé dans l'enveloppe."""

    REPRISE = "reprise"
    """Argent repris pour un autre usage."""

    DEPENSE = "depense"
    """Une dépense de la catégorie a puisé dans l'enveloppe."""

    REMBOURSEMENT = "remboursement"
    """Une dépense a été remboursée : l'argent revient dans l'enveloppe."""

    AJUSTEMENT_PLUS = "ajustement_plus"
    AJUSTEMENT_MOINS = "ajustement_moins"
    """Corrections. Elles ne réécrivent pas l'histoire, elles s'y ajoutent."""

    LIBERATION = "liberation"
    """L'enveloppe a atteint sa cible : le surplus redevient disponible ailleurs."""


CREDITE: Final[frozenset[TypeMouvement]] = frozenset(
    {
        TypeMouvement.ALLOCATION,
        TypeMouvement.REMBOURSEMENT,
        TypeMouvement.AJUSTEMENT_PLUS,
    }
)
"""Types qui augmentent le solde. Tout ce qui n'y est pas le diminue.

Écrit comme un ensemble fermé et non comme une suite de `if` : ajouter un type sans
décider de son sens fait échouer `test_chaque_type_a_un_sens`, au lieu de le faire
compter en silence du mauvais côté.
"""


class UsageEnveloppe(StrEnum):
    """À quoi sert l'enveloppe. Décide de ce que la préparation mensuelle lui recommande.

    La distinction n'est pas décorative : une enveloppe de FONCTIONNEMENT se vide chaque
    période par construction, une RÉSERVE s'accumule. Les additionner dans un même total
    « réservé » donnerait un chiffre qui ne veut rien dire — la moitié étant de l'argent
    déjà promis à des dépenses du mois, l'autre de l'argent mis de côté.
    """

    FONCTIONNEMENT = "fonctionnement"
    """Dépenses courantes de la période : courses, essence, sorties."""

    RESERVE = "reserve"
    """Argent mis de côté pour plus tard : vacances, impôts, un objectif daté."""


class Rollover(StrEnum):
    """Ce que devient le solde d'une enveloppe au passage à la période suivante.

    Choisi par Olivier le 20 août 2026, d'après le document de son collègue. Le mode
    DEMANDER n'est pas l'interruption qu'il serait ailleurs : rien ne s'écrit hors de la
    préparation mensuelle, qui est validée explicitement. La question y devient donc une
    ligne de plus dans un écran qu'on parcourt déjà, et non une boîte qui surgit à chaque
    paie.
    """

    REPORT = "report"
    """Le solde reste. Défaut, parce que non destructif : rien ne disparaît sans geste."""

    LIBERATION = "liberation"
    """Le reliquat retourne au non-affecté, et la période repart d'un budget neuf."""

    DEMANDER = "demander"
    """La préparation pose la question, enveloppe par enveloppe."""


@dataclass(frozen=True)
class Mouvement:
    type: TypeMouvement
    montant: Cents
    """TOUJOURS positif. Le sens vient du type."""


@dataclass(frozen=True)
class Enveloppe:
    nom: str
    mouvements: tuple[Mouvement, ...] = ()
    cible: Cents | None = None
    usage: UsageEnveloppe = UsageEnveloppe.FONCTIONNEMENT
    rollover: Rollover = Rollover.REPORT
    priorite: int = 0
    """Ordre de service quand le disponible ne suffit pas. Le PLUS PETIT passe en premier.

    Zéro par défaut, donc toutes à égalité tant qu'on n'y touche pas. À égalité, c'est le
    nom qui tranche — sans quoi l'ordre serait celui de l'insertion en base, c'est-à-dire
    un ordre qu'aucun utilisateur ne peut prévoir ni corriger.
    """

    contribution_mensuelle: Cents | None = None
    """Ce qu'on prévoit d'y mettre à chaque période, quand aucun plafond ne le dit déjà.

    `None` et non zéro : sans contribution ni cible, la préparation ne doit RIEN
    recommander plutôt que de recommander zéro — inventer un montant là où l'utilisateur
    n'en a fixé aucun serait une décision prise à sa place.
    """

    @property
    def solde(self) -> Cents:
        return Cents(
            sum(
                int(m.montant) if m.type in CREDITE else -int(m.montant)
                for m in self.mouvements
            )
        )

    @property
    def place(self) -> Cents | None:
        """Ce qu'il manque pour atteindre la cible, ou `None` si aucune cible.

        `None` et non zéro : une enveloppe sans cible n'est pas une enveloppe pleine, et
        la préparation mensuelle ne doit rien lui recommander plutôt que de recommander
        zéro. Inventer un montant là où l'utilisateur n'en a fixé aucun serait une
        décision prise à sa place.
        """
        if self.cible is None:
            return None
        return Cents(max(0, int(self.cible) - int(self.solde)))


@dataclass(frozen=True)
class Repartition:
    """État de l'argent découpé en enveloppes."""

    epargne_totale: Cents
    enveloppes: tuple[Enveloppe, ...]

    @property
    def reserve(self) -> Cents:
        """Somme des soldes POSITIFS seulement.

        Une enveloppe dans le rouge ne doit pas rogner ce que les autres promettent : si
        les vacances sont à −50, cela n'enlève rien aux 900 € d'impôts. Additionner les
        négatifs ferait apparaître de l'argent disponible qui ne l'est pas.
        """
        return Cents(sum(max(0, int(e.solde)) for e in self.enveloppes))

    @property
    def non_affecte(self) -> Cents:
        """Ce qui reste libre. Peut être NÉGATIF.

        Négatif signifie que l'argent a fondu sous ce qui était réservé. Le forcer à zéro
        cacherait exactement ce qu'il faut voir : que les promesses ne sont plus couvertes.
        """
        return Cents(int(self.epargne_totale) - int(self.reserve))

    @property
    def decouvert(self) -> bool:
        return self.non_affecte < 0

    def part(self, enveloppe: Enveloppe) -> int:
        """Part de l'épargne totale occupée, en pourcentage tronqué.

        Sur l'épargne TOTALE et non sur le réservé : rapportée au réservé, la dernière
        enveloppe paraîtrait grossir à mesure qu'on en supprime d'autres.
        """
        if self.epargne_totale <= 0:
            return 0
        return max(0, int(enveloppe.solde)) * 100 // int(self.epargne_totale)


@dataclass(frozen=True)
class Reliquat:
    """Ce que le passage de période fait au solde d'une enveloppe.

    Un type à part plutôt qu'un `Cents | None` : « rien à libérer » et « il faut demander »
    sont deux réponses différentes que la même valeur `None` aurait confondues, et
    l'appelant les traite différemment — la première ne produit aucune ligne dans la
    préparation, la seconde en produit une qui attend un choix.
    """

    enveloppe: str
    a_liberer: Cents
    """Toujours positif ou nul. Zéro quand le solde est reporté ou déjà négatif."""

    demande_un_choix: bool


def reliquat_au_changement_de_periode(enveloppe: Enveloppe) -> Reliquat:
    """Ce qu'il advient du solde d'une enveloppe quand une nouvelle période s'ouvre.

    Fonction PURE, et c'est délibéré : elle ne décide rien, elle calcule une proposition.
    L'écriture des mouvements appartient à la préparation mensuelle, qu'Olivier a choisi de
    faire valider explicitement — rien ne bouge sans revue, y compris ici.

    Trois cas, et un quatrième qui n'en est pas un :

    - REPORT : rien ne sort. Le solde continue sa vie.
    - LIBERATION : le solde POSITIF retourne au non-affecté.
    - DEMANDER : la préparation posera la question.
    - un solde négatif ou nul ne libère jamais rien, quel que soit le mode. Libérer un
      découvert reviendrait à faire apparaître de l'argent qui n'existe pas, et « demander »
      poserait une question dont les deux réponses sont identiques.
    """
    solde = enveloppe.solde
    if solde <= 0:
        return Reliquat(enveloppe=enveloppe.nom, a_liberer=Cents(0), demande_un_choix=False)

    match enveloppe.rollover:
        case Rollover.REPORT:
            return Reliquat(enveloppe=enveloppe.nom, a_liberer=Cents(0), demande_un_choix=False)
        case Rollover.LIBERATION:
            return Reliquat(enveloppe=enveloppe.nom, a_liberer=solde, demande_un_choix=False)
        case Rollover.DEMANDER:
            return Reliquat(enveloppe=enveloppe.nom, a_liberer=solde, demande_un_choix=True)


def ordre_de_service(enveloppes: Sequence[Enveloppe]) -> tuple[Enveloppe, ...]:
    """Ordre dans lequel servir les enveloppes quand le disponible ne suffit pas.

    Priorité croissante d'abord, puis le NOM. Le nom n'est pas un détail esthétique : sans
    lui, deux enveloppes de même priorité seraient servies dans l'ordre où la base les
    rend, c'est-à-dire un ordre qu'aucun utilisateur ne peut prévoir, et qui peut changer
    d'une requête à l'autre. Un partage d'argent qui dépend de l'ordre des lignes en base
    est un partage qu'on ne peut ni expliquer ni corriger.
    """
    return tuple(sorted(enveloppes, key=lambda e: (e.priorite, e.nom)))


def solde_de(mouvements: Iterable[Mouvement]) -> Cents:
    return Enveloppe(nom="", mouvements=tuple(mouvements)).solde


def repartir(epargne_totale: Cents, enveloppes: Sequence[Enveloppe]) -> Repartition:
    return Repartition(epargne_totale=epargne_totale, enveloppes=tuple(enveloppes))
