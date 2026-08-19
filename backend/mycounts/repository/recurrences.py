"""Accès aux récurrences et à leur matérialisation."""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Sequence

from sqlalchemy import ColumnElement, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mycounts.domain.agregats import EtatOperation
from mycounts.domain.montants import Cents
from mycounts.domain.recurrence import UniteRecurrence
from mycounts.models.budget import Compte, Operation, Recurrence
from mycounts.repository.base import Principal
from mycounts.repository.budget import _comptes_autorises


def creer_recurrence(
    session: Session,
    principal: Principal,
    *,
    compte_id: uuid.UUID,
    libelle: str,
    montant_centimes: Cents,
    ancre: dt.date,
    unite: UniteRecurrence,
    intervalle: int = 1,
    categorie_id: uuid.UUID | None = None,
    fin: dt.date | None = None,
) -> Recurrence:
    recurrence = Recurrence(
        compte_id=compte_id,
        categorie_id=categorie_id,
        cree_par_id=principal.utilisateur_id,
        libelle=libelle,
        montant_centimes=montant_centimes,
        ancre=ancre,
        unite=unite,
        intervalle=intervalle,
        fin=fin,
    )
    session.add(recurrence)
    session.flush()
    return recurrence


def recurrences_visibles(session: Session, principal: Principal) -> list[Recurrence]:
    return list(
        session.execute(
            select(Recurrence)
            .join(Compte, Compte.id == Recurrence.compte_id)
            .where(_comptes_autorises(principal), Recurrence.active.is_(True))
            .order_by(Recurrence.libelle)
        ).scalars()
    )


def recurrence_visible(
    session: Session, principal: Principal, recurrence_id: uuid.UUID
) -> Recurrence | None:
    return session.execute(
        select(Recurrence)
        .join(Compte, Compte.id == Recurrence.compte_id)
        .where(Recurrence.id == recurrence_id, _comptes_autorises(principal))
    ).scalar_one_or_none()


def modifier_recurrence(
    session: Session,
    recurrence: Recurrence,
    *,
    libelle: str | None = None,
    montant_centimes: Cents | None = None,
    ancre: dt.date | None = None,
    unite: UniteRecurrence | None = None,
    intervalle: int | None = None,
    categorie_id: uuid.UUID | None = None,
    fin: dt.date | None = None,
) -> Recurrence:
    """Modifie un prélèvement. Les opérations DÉJÀ matérialisées ne bougent pas.

    Changer le montant d'un abonnement ne réécrit pas les prélèvements passés : ils ont
    eu lieu au montant d'alors. Seules les échéances futures suivent le nouveau réglage.
    Réécrire l'historique ferait changer des soldes de mois déjà clos.
    """
    if libelle is not None:
        recurrence.libelle = libelle
    if montant_centimes is not None:
        recurrence.montant_centimes = montant_centimes
    if ancre is not None:
        recurrence.ancre = ancre
    if unite is not None:
        recurrence.unite = unite
    if intervalle is not None:
        recurrence.intervalle = intervalle
    if categorie_id is not None:
        recurrence.categorie_id = categorie_id
    if fin is not None:
        recurrence.fin = fin
    session.flush()
    return recurrence


def desactiver_recurrence(session: Session, recurrence: Recurrence) -> None:
    """Désactive plutôt que supprimer : les opérations déjà matérialisées gardent leur
    lien, et l'historique reste explicable."""
    recurrence.active = False
    session.flush()


def recurrences_actives(
    session: Session, *, foyer_id: uuid.UUID | None = None
) -> Sequence[Recurrence]:
    """Toutes les récurrences actives, éventuellement restreintes à un foyer.

    Sans périmètre : ce n'est pas une lecture pour un utilisateur, c'est le job de
    matérialisation qui traite l'ensemble. Le filtre par foyer n'existe que pour les
    tests, qui doivent pouvoir isoler leur jeu de données.
    """
    conditions: list[ColumnElement[bool]] = [Recurrence.active.is_(True)]
    if foyer_id is not None:
        conditions.append(Compte.foyer_id == foyer_id)
    return list(
        session.execute(
            select(Recurrence)
            .join(Compte, Compte.id == Recurrence.compte_id)
            .where(*conditions)
            .order_by(Recurrence.cree_le)
        ).scalars()
    )


def dates_deja_materialisees(session: Session, *, recurrence_id: uuid.UUID) -> set[dt.date]:
    """Dates déjà traitées pour cette récurrence, **annulées comprises**.

    C'est délibéré : une échéance annulée doit rester « déjà traitée », sinon le job la
    recréerait au passage suivant et l'annulation ne tiendrait pas une journée.
    """
    return set(
        session.execute(
            select(Operation.date_operation).where(Operation.recurrence_id == recurrence_id)
        ).scalars()
    )


def materialiser_echeance(
    session: Session,
    *,
    recurrence: Recurrence,
    date_echeance: dt.date,
    etat: EtatOperation,
) -> Operation | None:
    """Crée l'opération d'une échéance, ou `None` si une autre l'a déjà créée.

    L'appelant a beau vérifier avant d'insérer que la date n'est pas déjà matérialisée,
    ce contrôle et cette insertion ne sont pas un seul geste : entre les deux, une autre
    requête peut insérer la même ligne. Le cas n'est pas théorique — l'accueil et le
    calendrier matérialisent tous les deux, et le navigateur les appelle en parallèle au
    chargement. L'index unique partiel tenait bon, mais au prix d'une erreur 500.

    Le point de reprise circonscrit l'échec à cette seule insertion : la transaction
    englobante survit, et les échéances suivantes sont matérialisées normalement. `None`
    dit alors « quelqu'un d'autre s'en est chargé », ce qui est le résultat voulu.
    """
    operation = Operation(
        compte_id=recurrence.compte_id,
        categorie_id=recurrence.categorie_id,
        cree_par_id=recurrence.cree_par_id,
        recurrence_id=recurrence.id,
        libelle=recurrence.libelle,
        montant_centimes=recurrence.montant_centimes,
        date_operation=date_echeance,
        etat=etat,
    )
    try:
        with session.begin_nested():
            session.add(operation)
            session.flush()
    except IntegrityError:
        return None
    return operation


def confirmer_operation(session: Session, operation: Operation) -> Operation:
    """Passe une opération de `a_confirmer` à `confirmee`.

    Le montant n'est PAS modifié ici : confirmer, c'est dire « c'est bien passé ainsi ».
    Corriger un montant est une autre action, qui doit se voir comme telle.
    """
    operation.etat = EtatOperation.CONFIRMEE
    session.flush()
    return operation


def operations_a_confirmer(session: Session, principal: Principal) -> list[Operation]:
    return list(
        session.execute(
            select(Operation)
            .join(Compte, Compte.id == Operation.compte_id)
            .where(
                _comptes_autorises(principal),
                Operation.etat == EtatOperation.A_CONFIRMER,
                # Une échéance annulée reste en base pour bloquer sa rematérialisation ;
                # elle n'a rien à faire dans une file d'attente d'action.
                Operation.annulee.is_(False),
            )
            .order_by(Operation.date_operation)
        ).scalars()
    )
