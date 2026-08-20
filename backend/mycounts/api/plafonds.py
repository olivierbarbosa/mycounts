"""Routes des plafonds par catégorie."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from mycounts.api.budget_schemas import DemandePlafond, PlafondPublic
from mycounts.api.dependances import PrincipalCourant, SessionBase
from mycounts.domain.agregats import EtatOperation
from mycounts.domain.calendrier import aujourd_hui
from mycounts.domain.montants import Cents
from mycounts.domain.periode import periode_courante
from mycounts.domain.plafonds import OperationCategorisee, etat_du_plafond
from mycounts.jobs.materialisation import materialiser
from mycounts.repository import auth as depot_auth
from mycounts.repository import budget as depot_budget
from mycounts.repository import plafonds as depot
from mycounts.repository import recurrences as depot_recurrences

routeur = APIRouter(prefix="/plafonds", tags=["plafonds"])


def _etats(session: SessionBase, principal: PrincipalCourant) -> list[PlafondPublic]:
    # Même rattrapage qu'ailleurs : une échéance échue non matérialisée manquerait à la
    # consommation du plafond. Idempotent.
    materialiser(session, foyer_id=principal.foyer_id)

    utilisateur = depot_auth.utilisateur_par_id(session, principal.utilisateur_id)
    periode = periode_courante(
        depot_budget.dates_de_paie(session, principal),
        aujourd_hui=aujourd_hui(),
        paies_par_cycle=utilisateur.paies_par_cycle if utilisateur else 1,
    )
    # Les échéances futures ne sont dans AUCUNE table : la matérialisation ne crée une
    # opération qu'une fois l'échéance échue. Sans cette projection, `a_venir` restait
    # nul quoi qu'il arrive, et l'alerte « il reste 100 € mais 150 € arrivent » — la seule
    # qui prévient avant qu'il soit trop tard — ne pouvait jamais se déclencher.
    #
    # Elles arrivent à l'état `prevue`, que le domaine sait déjà tenir à l'écart des
    # dépenses consommées. Rien à changer de ce côté : ce qui manquait, c'était l'entrée.
    projetees = [
        OperationCategorisee(
            montant=Cents(recurrence.montant_centimes),
            date_operation=jour,
            etat=EtatOperation.PREVUE,
            categorie_id=recurrence.categorie_id,
        )
        for recurrence, jour in depot_recurrences.echeances_projetees(
            session, principal, depuis=aujourd_hui(), jusqu_a=periode.fin
        )
    ]
    operations = [*depot.operations_categorisees(session, principal), *projetees]

    resultat: list[PlafondPublic] = []
    for plafond in depot.plafonds_de(session, principal):
        etat = etat_du_plafond(
            categorie_id=plafond.categorie_id,
            limite=Cents(plafond.montant_centimes),
            operations=operations,
            aujourd_hui=aujourd_hui(),
            fin_de_fenetre=periode.fin,
        )
        resultat.append(
            PlafondPublic(
                id=plafond.id,
                categorie_id=plafond.categorie_id,
                categorie_nom=plafond.categorie.nom,
                limite_centimes=etat.limite,
                consomme_centimes=etat.consomme,
                a_venir_centimes=etat.a_venir,
                restant_centimes=etat.restant,
                part_consommee=etat.part_consommee,
                depasse=etat.depasse,
                depasse_avec_les_echeances=etat.depasse_avec_les_echeances,
            )
        )
    return resultat


@routeur.get("", response_model=list[PlafondPublic])
def lister(session: SessionBase, principal: PrincipalCourant) -> list[PlafondPublic]:
    return _etats(session, principal)


@routeur.put("", response_model=list[PlafondPublic])
def definir(
    demande: DemandePlafond, session: SessionBase, principal: PrincipalCourant
) -> list[PlafondPublic]:
    """Définit ou met à jour le plafond d'une catégorie.

    `PUT` et non `POST` : l'opération est idempotente, un seul plafond existant par
    personne et par catégorie. Rejouer la même demande donne le même état.
    """
    if depot_budget.categorie_visible(session, principal, demande.categorie_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie introuvable.")

    depot.definir_plafond(
        session,
        principal,
        categorie_id=demande.categorie_id,
        montant_centimes=Cents(demande.montant_centimes),
    )
    session.commit()
    return _etats(session, principal)


@routeur.delete("/{plafond_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer(
    plafond_id: uuid.UUID, session: SessionBase, principal: PrincipalCourant
) -> None:
    plafond = depot.plafond_visible(session, principal, plafond_id)
    if plafond is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plafond introuvable.")
    depot.supprimer_plafond(session, plafond)
    session.commit()
