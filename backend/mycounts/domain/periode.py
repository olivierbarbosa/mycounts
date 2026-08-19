"""Période budgétaire — de paie à paie, pas du 1er au 31.

**Auteur unique** de la question « à quelle période appartient ce jour ? ».
`calendrier.bornes_du_mois()` reste le mois CIVIL et ne doit jamais servir de substitut :
c'est ainsi qu'un écran afficherait un mois pendant qu'un autre en calculerait un autre.

Trois règles, décidées et non déduites :

1. Une période s'ouvre à la `date_operation` d'une paie, **jamais** au jour de sa saisie.
   Saisir avec trois jours de retard ne déplace donc aucune borne.
2. Avec `paies_par_cycle` > 1 (quinzaine, prime), seule une paie sur N ouvre un cycle ;
   les autres sont des revenus à l'intérieur. Sans ça, une prime ferait repartir tous les
   plafonds à zéro en plein mois.
3. Tant que la paie suivante n'est pas saisie, la fin est **estimée** — et l'estimation
   est signalée comme telle, jamais présentée comme une date connue.
"""

from __future__ import annotations

import calendar
import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass

from mycounts.domain.calendrier import bornes_du_mois


@dataclass(frozen=True)
class Periode:
    """Intervalle budgétaire, bornes **incluses**."""

    debut: dt.date
    fin: dt.date
    fin_estimee: bool
    """Vrai tant que la paie suivante n'a pas été saisie.

    L'interface doit l'afficher : un solde projeté dont la borne est supposée ne se lit
    pas comme un solde projeté dont la borne est connue.
    """

    def contient(self, jour: dt.date) -> bool:
        return self.debut <= jour <= self.fin


def ajouter_un_mois(jour: dt.date) -> dt.date:
    """Même quantième le mois suivant, ramené au dernier jour si celui-ci n'existe pas.

    Le 31 janvier donne le 28 (ou 29) février, pas une erreur ni un débordement sur mars.
    Sans cette règle, une paie du 31 produirait une période d'un jour tous les deux mois.
    """
    mois = jour.month % 12 + 1
    annee = jour.year + (1 if jour.month == 12 else 0)
    dernier = calendar.monthrange(annee, mois)[1]
    return dt.date(annee, mois, min(jour.day, dernier))


def dates_ouvrantes(paies: Sequence[dt.date], *, paies_par_cycle: int = 1) -> list[dt.date]:
    """Sous-ensemble des paies qui ouvrent une période.

    L'ancrage est la **première paie saisie** (BOUCLE.md, décision D2) : on prend ensuite
    une paie sur `paies_par_cycle`.
    """
    if paies_par_cycle < 1:
        raise ValueError("Il faut au moins une paie par cycle.")
    ordonnees = sorted(paies)
    return ordonnees[::paies_par_cycle]


def periodes(
    paies: Sequence[dt.date], *, aujourd_hui: dt.date, paies_par_cycle: int = 1
) -> list[Periode]:
    """Toutes les périodes déductibles des paies connues, de la plus ancienne à la plus
    récente.

    Sans aucune paie, on retombe sur le mois civil, marqué comme estimé : il faut bien
    afficher quelque chose au premier lancement, mais il ne faut surtout pas faire croire
    que la borne est connue (BOUCLE.md, décision D4).
    """
    ouvrantes = dates_ouvrantes(paies, paies_par_cycle=paies_par_cycle)
    if not ouvrantes:
        debut, fin = bornes_du_mois(aujourd_hui)
        return [Periode(debut=debut, fin=fin, fin_estimee=True)]

    resultat: list[Periode] = []
    for indice, debut in enumerate(ouvrantes):
        suivante = ouvrantes[indice + 1] if indice + 1 < len(ouvrantes) else None
        if suivante is not None:
            resultat.append(
                Periode(debut=debut, fin=suivante - dt.timedelta(days=1), fin_estimee=False)
            )
        else:
            resultat.append(
                Periode(
                    debut=debut,
                    fin=ajouter_un_mois(debut) - dt.timedelta(days=1),
                    fin_estimee=True,
                )
            )
    return resultat


def periode_contenant(
    jour: dt.date, paies: Sequence[dt.date], *, aujourd_hui: dt.date, paies_par_cycle: int = 1
) -> Periode:
    """Période à laquelle `jour` appartient.

    Un jour antérieur à la toute première paie n'appartient à aucune période observée :
    on lui en fabrique une qui se termine la veille de cette première paie. Le renvoyer
    dans la première période le compterait dans un budget qui n'avait pas commencé.
    """
    toutes = periodes(paies, aujourd_hui=aujourd_hui, paies_par_cycle=paies_par_cycle)
    for periode in toutes:
        if periode.contient(jour):
            return periode

    premiere = toutes[0]
    if jour < premiere.debut:
        debut, _ = bornes_du_mois(jour)
        return Periode(
            debut=min(debut, jour),
            fin=premiere.debut - dt.timedelta(days=1),
            fin_estimee=True,
        )

    # Au-delà de la dernière période estimée : on prolonge de mois en mois plutôt que de
    # renvoyer une erreur, sinon une échéance lointaine n'aurait aucune période d'accueil.
    derniere = toutes[-1]
    debut = derniere.debut
    while True:
        fin = ajouter_un_mois(debut) - dt.timedelta(days=1)
        if debut <= jour <= fin:
            return Periode(debut=debut, fin=fin, fin_estimee=True)
        debut = ajouter_un_mois(debut)


def periode_courante(
    paies: Sequence[dt.date], *, aujourd_hui: dt.date, paies_par_cycle: int = 1
) -> Periode:
    return periode_contenant(
        aujourd_hui, paies, aujourd_hui=aujourd_hui, paies_par_cycle=paies_par_cycle
    )
