"""Résumé d'une période budgétaire.

**Auteur unique** de l'assemblage « période + opérations → chiffres affichés ». Si chaque
écran refaisait ce calcul, le mobile et le bureau finiraient par afficher deux soldes
différents pour la même journée — et personne ne saurait lequel croire.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass

from mycounts.domain.agregats import Agregat, OperationCalcul, calculer
from mycounts.domain.montants import Cents
from mycounts.domain.periode import Periode, periode_courante


@dataclass(frozen=True)
class ResumePeriode:
    """Ce qu'un écran a le droit d'afficher, et rien de plus."""

    periode: Periode

    solde_projete: Cents
    """Chiffre mis en avant : réel + à confirmer + échéances jusqu'à la fin de période.

    Il ne correspond PAS au solde de la banque, et c'est voulu. L'interface doit toujours
    l'accompagner de sa borne (« projeté au 26/09 ») : un projeté sans date de fin de
    fenêtre est ininterprétable.
    """

    solde_reel: Cents
    """Ce que la banque devrait afficher aujourd'hui. Sert au rapprochement.

    Il est calculé même s'il n'est pas mis en avant : sans lui, un écart avec la banque
    ne serait pas diagnosticable — impossible de dire s'il vient d'une saisie oubliée ou
    d'une échéance qui n'est pas passée.
    """

    solde_a_confirmer: Cents
    """Ce qui est parti sans avoir été vérifié. Doit tendre vers zéro."""

    depenses_de_periode: Cents
    """Base des plafonds par catégorie (lot 4). Négatif ou nul."""

    @property
    def ecart_a_confirmer(self) -> Cents:
        """Différence entre projeté et réel : ce qui reste supposé.

        Grandeur de contrôle : quand elle est nulle, projeté et réel coïncident et le
        rapprochement bancaire doit tomber juste.
        """
        return Cents(self.solde_projete - self.solde_reel)


def resumer(
    operations: Sequence[OperationCalcul],
    paies: Sequence[dt.date],
    *,
    aujourd_hui: dt.date,
    paies_par_cycle: int = 1,
) -> ResumePeriode:
    periode = periode_courante(
        paies, aujourd_hui=aujourd_hui, paies_par_cycle=paies_par_cycle
    )
    bornes = {"aujourd_hui": aujourd_hui, "fin_de_fenetre": periode.fin}
    return ResumePeriode(
        periode=periode,
        solde_projete=calculer(Agregat.SOLDE_PROJETE, operations, **bornes),
        solde_reel=calculer(Agregat.SOLDE_REEL, operations, **bornes),
        solde_a_confirmer=calculer(Agregat.SOLDE_A_CONFIRMER, operations, **bornes),
        depenses_de_periode=calculer(Agregat.DEPENSES_DE_PERIODE, operations, **bornes),
    )
