"""Route des statistiques de dépense et des constats.

Ce fichier ne calcule rien : il lit, convertit, et laisse `domain/statistiques.py` décider.
La séparation compte ici plus qu'ailleurs, parce que les seuils du coaching sont
exactement le genre de valeur qu'on veut pouvoir relire et discuter sans traverser une
route HTTP pour les trouver.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence

from fastapi import APIRouter

from mycounts.api.dependances import PrincipalCourant, SessionBase
from mycounts.api.statistiques_schemas import (
    ConstatPublic,
    PostePublic,
    StatistiquesPubliques,
)
from mycounts.domain.calendrier import aujourd_hui
from mycounts.domain.montants import Cents
from mycounts.domain.recurrence import Cadence, UniteRecurrence
from mycounts.domain.statistiques import DepenseCalcul, constats, repartition
from mycounts.models.budget import Operation
from mycounts.repository import budget as depot
from mycounts.repository import recurrences as depot_recurrences

routeur = APIRouter(tags=["statistiques"])

"""Nombre d'échéances par an, pour chaque unité de récurrence.

Écrit comme une table plutôt que comme une suite de `if` : une unité ajoutée au domaine
sans son facteur fera lever un `KeyError` immédiat, au lieu d'être comptée en silence
comme si elle tombait une fois par an.
"""
ECHEANCES_PAR_AN: dict[UniteRecurrence, int] = {
    UniteRecurrence.JOUR: 365,
    UniteRecurrence.SEMAINE: 52,
    UniteRecurrence.MOIS: 12,
    UniteRecurrence.AN: 1,
}


def _en_depenses(operations: Sequence[Operation]) -> list[DepenseCalcul]:
    """Ne garde que les DÉPENSES, en montant positif.

    Sont écartés : les revenus, les VIREMENTS — l'argent n'a pas quitté le foyer, et le
    compter ferait apparaître une dépense à chaque mise de côté —, les soldes d'ouverture,
    qui sont un amorçage et non un achat, et les ajustements, qui corrigent un écart de
    saisie plutôt que de décrire une dépense.

    Typé sur `Operation` et non sur `object` : une première version lisait ces drapeaux par
    `getattr(..., défaut)`, ce qui compilait, passait mypy — et rendait `False` pour un
    `est_virement` qui n'existe pas. Les virements seraient tous entrés dans les
    statistiques comme des dépenses. Un accès dynamique à un attribut qu'on croit connaître
    est un typage qu'on s'est retiré à soi-même.
    """
    retenues: list[DepenseCalcul] = []
    for operation in operations:
        if operation.montant_centimes >= 0:
            continue
        if operation.est_ouverture or operation.est_ajustement:
            continue
        if operation.virement_id is not None:
            continue
        retenues.append(
            DepenseCalcul(
                libelle=operation.libelle,
                montant=Cents(-operation.montant_centimes),
                categorie=None if operation.categorie is None else operation.categorie.nom,
            )
        )
    return retenues


def _cout_annuel_des_abonnements(session: SessionBase, principal: PrincipalCourant) -> Cents:
    """Ce que les prélèvements récurrents coûtent sur douze mois.

    C'est le chiffre que les douzièmes rendent invisible : trois euros par mois se lisent
    comme trois euros, jamais comme trente-six. Seules les SORTIES sont comptées — un
    salaire mensuel est une récurrence lui aussi, et l'additionner ferait un total qui ne
    veut rien dire.
    """
    total = 0
    for recurrence in depot_recurrences.recurrences_visibles(session, principal):
        if recurrence.montant_centimes >= 0:
            continue
        if recurrence.fin is not None and recurrence.fin < aujourd_hui():
            continue
        cadence = Cadence(
            unite=UniteRecurrence(recurrence.unite), intervalle=recurrence.intervalle
        )
        par_an = ECHEANCES_PAR_AN[cadence.unite] // max(1, cadence.intervalle)
        total += -recurrence.montant_centimes * par_an
    return Cents(total)


@routeur.get("/statistiques", response_model=StatistiquesPubliques)
def statistiques(session: SessionBase, principal: PrincipalCourant) -> StatistiquesPubliques:
    """Où va l'argent sur la période, et ce que l'addition mentale rate.

    La période PRÉCÉDENTE est lue elle aussi, et sert uniquement de point de comparaison :
    sans elle, « 320 € de sorties » ne dit pas si c'est beaucoup. C'est la comparaison qui
    porte l'information, pas le chiffre seul.
    """
    from mycounts.api.budget import resume_de_la_periode

    resume = resume_de_la_periode(session, principal)
    debut, fin = resume.periode.debut, resume.periode.fin
    duree = fin - debut

    # La période précédente est déduite par la DURÉE de la courante, et non par un mois
    # civil : les périodes vont de paie à paie et n'ont pas toutes la même longueur.
    fin_precedente = debut - dt.timedelta(days=1)
    debut_precedent = fin_precedente - duree

    depenses = _en_depenses(
        depot.operations_visibles(session, principal, depuis=debut, jusqu_a=fin)
    )
    precedentes = _en_depenses(
        depot.operations_visibles(
            session, principal, depuis=debut_precedent, jusqu_a=fin_precedente
        )
    )

    postes = repartition(depenses, precedentes)
    abonnements = _cout_annuel_des_abonnements(session, principal)
    releves = constats(depenses, postes, cout_annuel_des_abonnements=abonnements)

    total = Cents(sum(int(p.montant) for p in postes))
    total_precedent = Cents(sum(int(d.montant) for d in precedentes))

    return StatistiquesPubliques(
        debut=debut,
        fin=fin,
        total_centimes=int(total),
        total_precedent_centimes=int(total_precedent),
        nombre_de_depenses=len(depenses),
        cout_annuel_des_abonnements_centimes=int(abonnements),
        postes=[
            PostePublic(
                categorie=poste.categorie,
                montant_centimes=int(poste.montant),
                part=poste.part,
                montant_precedent_centimes=(
                    None if poste.montant_precedent is None else int(poste.montant_precedent)
                ),
                variation=poste.variation,
            )
            for poste in postes
        ],
        constats=[
            ConstatPublic(
                motif=constat.motif,
                sujet=constat.sujet,
                montant_centimes=int(constat.montant),
                detail=constat.detail,
            )
            for constat in releves
        ],
    )
