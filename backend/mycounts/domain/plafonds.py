"""État d'un plafond de catégorie sur une période budgétaire.

**Auteur unique** du calcul « où en suis-je sur ce plafond ». Un plafond ne stocke que sa
limite : la consommation se calcule, comme le solde, et n'est jamais écrite en base.

Deux grandeurs sont exposées **séparément** et ne se mélangent jamais :

- ce qui est **déjà dépensé** (opérations confirmées ou à confirmer) ;
- ce qui est **encore à venir** sur la période (échéances récurrentes prévues).

Les additionner donnerait un chiffre plus complet mais faux à lire : « j'ai dépensé
380 € » alors que 150 € ne sont pas encore partis, c'est exactement le genre de confusion
qui fait cesser de croire l'outil. L'interface peut afficher les deux, jamais leur somme
sous le nom de « dépensé ».
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from mycounts.domain.agregats import Agregat, EtatOperation, OperationCalcul, calculer
from mycounts.domain.montants import Cents


@dataclass(frozen=True)
class OperationCategorisee(OperationCalcul):
    """Opération enrichie de sa catégorie, pour ventiler les plafonds."""

    categorie_id: uuid.UUID | None = None


@dataclass(frozen=True)
class EtatPlafond:
    categorie_id: uuid.UUID
    limite: Cents
    """Toujours positif : un plafond est une limite, pas une dépense."""

    consomme: Cents
    """Positif : valeur absolue de ce qui est déjà sorti sur la catégorie."""

    a_venir: Cents
    """Positif : échéances récurrentes prévues d'ici la fin de période.

    Séparé de `consomme` à dessein — voir l'en-tête du module.
    """

    @property
    def restant(self) -> Cents:
        """Ce qu'il reste avant la limite. Négatif si elle est dépassée."""
        return Cents(self.limite - self.consomme)

    @property
    def depasse(self) -> bool:
        return self.consomme > self.limite

    @property
    def depasse_avec_les_echeances(self) -> bool:
        """Vrai si le plafond sera dépassé une fois les échéances passées.

        C'est l'alerte utile : être à 300 € sur 400 paraît confortable, jusqu'à ce qu'on
        sache que 150 € de prélèvements tombent avant la fin de la période.
        """
        return self.consomme + self.a_venir > self.limite

    @property
    def part_consommee(self) -> int:
        """Pourcentage entier, tronqué vers le bas.

        Division entière, jamais de flottant. La troncature est le bon sens ici : à
        99,7 % on affiche 99, donc l'interface ne dit jamais « 100 % » avant que la limite
        soit réellement atteinte.
        """
        if self.limite <= 0:  # pragma: no cover — interdit par contrainte en base
            return 0
        return self.consomme * 100 // self.limite


def _somme_categorie(
    operations: Iterable[OperationCategorisee],
    categorie_id: uuid.UUID,
    agregat: Agregat,
    *,
    aujourd_hui: dt.date,
    fin_de_fenetre: dt.date,
) -> Cents:
    retenues = [o for o in operations if o.categorie_id == categorie_id]
    return calculer(agregat, retenues, aujourd_hui=aujourd_hui, fin_de_fenetre=fin_de_fenetre)


def etat_du_plafond(
    *,
    categorie_id: uuid.UUID,
    limite: Cents,
    operations: Sequence[OperationCategorisee],
    aujourd_hui: dt.date,
    fin_de_fenetre: dt.date,
) -> EtatPlafond:
    depenses = _somme_categorie(
        operations,
        categorie_id,
        Agregat.DEPENSES_DE_PERIODE,
        aujourd_hui=aujourd_hui,
        fin_de_fenetre=fin_de_fenetre,
    )

    # Les échéances seulement PRÉVUES sont hors de DEPENSES_DE_PERIODE : elles se
    # comptent à part, sans quoi le plafond serait dépassé dès le premier jour par des
    # dépenses qui n'ont pas encore eu lieu.
    a_venir = sum(
        -o.montant
        for o in operations
        if o.categorie_id == categorie_id
        and o.etat is EtatOperation.PREVUE
        and o.montant < 0
        and aujourd_hui <= o.date_operation <= fin_de_fenetre
    )

    return EtatPlafond(
        categorie_id=categorie_id,
        limite=limite,
        consomme=Cents(-depenses),
        a_venir=Cents(a_venir),
    )
