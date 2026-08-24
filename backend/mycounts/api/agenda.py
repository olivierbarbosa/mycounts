"""Routes des récurrences, de l'agenda et de la confirmation."""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, HTTPException, Query, status

from mycounts.api.budget_schemas import (
    BornesDuMois,
    DemandeRecurrence,
    EcheanceAgenda,
    ModificationRecurrence,
    OperationPublique,
    RecurrencePublique,
)
from mycounts.api.dependances import PrincipalCourant, SessionBase
from mycounts.domain.calendrier import aujourd_hui, bornes_du_mois
from mycounts.domain.montants import Cents
from mycounts.jobs.materialisation import materialiser
from mycounts.repository import budget as depot_budget
from mycounts.repository import recurrences as depot

routeur = APIRouter(tags=["agenda"])

HORIZON_MAXIMAL = 365
"""Un agenda plus lointain qu'un an n'apprend rien : les montants et les abonnements
auront changé. La borne évite aussi qu'une cadence quotidienne produise 10 000 lignes."""


@routeur.get("/recurrences", response_model=list[RecurrencePublique])
def lister_recurrences(
    session: SessionBase, principal: PrincipalCourant
) -> list[RecurrencePublique]:
    return [
        RecurrencePublique.model_validate(r, from_attributes=True)
        for r in depot.recurrences_visibles(session, principal)
    ]


@routeur.post(
    "/recurrences", response_model=RecurrencePublique, status_code=status.HTTP_201_CREATED
)
def creer_recurrence(
    demande: DemandeRecurrence, session: SessionBase, principal: PrincipalCourant
) -> RecurrencePublique:
    if demande.montant_centimes == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Un montant nul ne décrit aucune échéance.",
        )
    if demande.fin is not None and demande.fin < demande.ancre:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La fin d'une récurrence ne peut pas précéder sa première échéance.",
        )
    if depot_budget.compte_visible(session, principal, demande.compte_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable.")
    if demande.categorie_id is not None and (
        depot_budget.categorie_visible(session, principal, demande.categorie_id) is None
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie introuvable.")

    recurrence = depot.creer_recurrence(
        session,
        principal,
        compte_id=demande.compte_id,
        libelle=demande.libelle,
        montant_centimes=Cents(demande.montant_centimes),
        ancre=demande.ancre,
        unite=demande.unite,
        intervalle=demande.intervalle,
        categorie_id=demande.categorie_id,
        fin=demande.fin,
    )
    session.commit()
    return RecurrencePublique.model_validate(recurrence, from_attributes=True)


@routeur.patch("/recurrences/{recurrence_id}", response_model=RecurrencePublique)
def modifier_recurrence(
    recurrence_id: uuid.UUID,
    demande: ModificationRecurrence,
    session: SessionBase,
    principal: PrincipalCourant,
) -> RecurrencePublique:
    """Modifie un prélèvement.

    Les opérations déjà matérialisées ne changent pas : un abonnement dont le tarif
    augmente n'a pas coûté davantage les mois précédents.
    """
    categorie_fournie = "categorie_id" in demande.model_fields_set
    fin_fournie = "fin" in demande.model_fields_set
    recurrence = depot.recurrence_visible(session, principal, recurrence_id)
    if recurrence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Prélèvement introuvable."
        )
    if demande.montant_centimes is not None and demande.montant_centimes == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Un montant nul ne décrit aucune échéance.",
        )
    if demande.categorie_id is not None and (
        depot_budget.categorie_visible(session, principal, demande.categorie_id) is None
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie introuvable.")

    nouvelle_ancre = demande.ancre or recurrence.ancre
    nouvelle_fin = demande.fin if fin_fournie else recurrence.fin
    if nouvelle_fin is not None and nouvelle_fin < nouvelle_ancre:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La fin d'un prélèvement ne peut pas précéder sa première échéance.",
        )

    depot.modifier_recurrence(
        session,
        recurrence,
        libelle=demande.libelle,
        montant_centimes=Cents(demande.montant_centimes)
        if demande.montant_centimes is not None
        else None,
        ancre=demande.ancre,
        unite=demande.unite,
        intervalle=demande.intervalle,
        categorie_id=demande.categorie_id,
        categorie_fournie=categorie_fournie,
        fin=demande.fin,
        fin_fournie=fin_fournie,
    )
    session.commit()
    return RecurrencePublique.model_validate(recurrence, from_attributes=True)


@routeur.delete("/recurrences/{recurrence_id}", status_code=status.HTTP_204_NO_CONTENT)
def arreter_recurrence(
    recurrence_id: uuid.UUID, session: SessionBase, principal: PrincipalCourant
) -> None:
    """Désactive la récurrence. Les opérations déjà matérialisées restent en place :
    supprimer l'historique parce qu'un abonnement s'arrête réécrirait le passé."""
    recurrence = depot.recurrence_visible(session, principal, recurrence_id)
    if recurrence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Récurrence introuvable."
        )
    depot.desactiver_recurrence(session, recurrence)
    session.commit()


@routeur.get("/agenda/mois-en-cours", response_model=BornesDuMois)
def mois_en_cours(principal: PrincipalCourant) -> BornesDuMois:
    """Premier et dernier jour du mois CIVIL courant, bornes incluses.

    Le client ne recalcule pas ces bornes : « aujourd'hui » se lit dans le fuseau
    Europe/Paris, dont le domaine est l'auteur unique. Un navigateur réglé sur un autre
    fuseau afficherait sinon le mauvais mois le 1er et le dernier jour — et l'écran du
    calendrier annoncerait un total que le serveur ne calculerait pas pareil.

    Ce n'est PAS la période budgétaire du foyer, qui va de paie à paie.
    """
    del principal  # L'authentification suffit : la réponse ne dépend d'aucun foyer.
    debut, fin = bornes_du_mois(aujourd_hui())
    return BornesDuMois(debut=debut, fin=fin)


@routeur.get("/agenda", response_model=list[EcheanceAgenda])
def agenda(
    session: SessionBase,
    principal: PrincipalCourant,
    jours: int = Query(default=60, ge=1, le=HORIZON_MAXIMAL),
) -> list[EcheanceAgenda]:
    """Échéances à venir, calculées à la volée.

    Rien n'est stocké : l'agenda est une **projection**, et le recalculer à chaque appel
    garantit qu'il suit toute modification d'une récurrence sans travail de mise à jour.
    """
    # Rattrapage avant lecture : entre le jour d'une échéance et le passage du job,
    # elle n'apparaîtrait ni dans l'agenda (qui commence aujourd'hui) ni dans les
    # opérations (pas encore créée). Un trou où de l'argent disparaît des écrans.
    # L'opération est idempotente, donc sans risque sur une lecture répétée.
    materialiser(session, espace_id=principal.espace_id)

    debut = aujourd_hui()
    fin = debut + dt.timedelta(days=jours)

    resultat = [
        EcheanceAgenda(
            recurrence_id=recurrence.id,
            libelle=recurrence.libelle,
            montant_centimes=recurrence.montant_centimes,
            date_echeance=jour,
            categorie_id=recurrence.categorie_id,
        )
        for recurrence, jour in depot.echeances_projetees(
            session, principal, depuis=debut, jusqu_a=fin
        )
    ]
    resultat.sort(key=lambda e: (e.date_echeance, e.libelle))
    return resultat


@routeur.get("/operations/a-confirmer", response_model=list[OperationPublique])
def lister_a_confirmer(
    session: SessionBase, principal: PrincipalCourant
) -> list[OperationPublique]:
    return [
        OperationPublique.model_validate(o, from_attributes=True)
        for o in depot.operations_a_confirmer(session, principal)
    ]


@routeur.post("/operations/{operation_id}/confirmer", response_model=OperationPublique)
def confirmer(
    operation_id: uuid.UUID, session: SessionBase, principal: PrincipalCourant
) -> OperationPublique:
    """Confirme qu'une échéance matérialisée est bien passée.

    Le montant n'est pas modifiable ici : confirmer, c'est dire « c'est passé ainsi ».
    Le solde projeté ne doit pas bouger — seule la répartition entre réel et à-confirmer
    change.
    """
    operation = next(
        (o for o in depot.operations_a_confirmer(session, principal) if o.id == operation_id),
        None,
    )
    if operation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opération introuvable ou déjà confirmée.",
        )
    depot.confirmer_operation(session, operation)
    session.commit()
    return OperationPublique.model_validate(operation, from_attributes=True)
