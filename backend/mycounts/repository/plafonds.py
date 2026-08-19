"""Accès aux plafonds de catégorie."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from mycounts.domain.montants import Cents
from mycounts.domain.plafonds import OperationCategorisee
from mycounts.models.budget import Categorie, Compte, Operation, Plafond
from mycounts.repository.base import Principal
from mycounts.repository.budget import _comptes_autorises


def plafonds_de(session: Session, principal: Principal) -> list[Plafond]:
    """Plafonds de l'appelant.

    Le périmètre porte sur `utilisateur_id` et non sur le foyer : un plafond est
    personnel, et voir celui de l'autre membre reviendrait à voir ses intentions de
    dépense.
    """
    return list(
        session.execute(
            select(Plafond)
            .join(Categorie, Categorie.id == Plafond.categorie_id)
            .where(
                Plafond.utilisateur_id == principal.utilisateur_id,
                Categorie.foyer_id == principal.foyer_id,
            )
            .order_by(Categorie.nom)
        ).scalars()
    )


def plafond_visible(
    session: Session, principal: Principal, plafond_id: uuid.UUID
) -> Plafond | None:
    return session.execute(
        select(Plafond).where(
            Plafond.id == plafond_id, Plafond.utilisateur_id == principal.utilisateur_id
        )
    ).scalar_one_or_none()


def plafond_pour_categorie(
    session: Session, principal: Principal, categorie_id: uuid.UUID
) -> Plafond | None:
    return session.execute(
        select(Plafond).where(
            Plafond.utilisateur_id == principal.utilisateur_id,
            Plafond.categorie_id == categorie_id,
        )
    ).scalar_one_or_none()


def definir_plafond(
    session: Session,
    principal: Principal,
    *,
    categorie_id: uuid.UUID,
    montant_centimes: Cents,
) -> Plafond:
    """Crée le plafond, ou met à jour le sien s'il existe déjà.

    Un seul plafond par personne et par catégorie (contrainte d'unicité) : deux limites
    concurrentes sur la même catégorie n'auraient aucun sens et l'interface devrait en
    choisir une arbitrairement.
    """
    existant = plafond_pour_categorie(session, principal, categorie_id)
    if existant is not None:
        existant.montant_centimes = montant_centimes
        session.flush()
        return existant

    plafond = Plafond(
        utilisateur_id=principal.utilisateur_id,
        categorie_id=categorie_id,
        montant_centimes=montant_centimes,
    )
    session.add(plafond)
    session.flush()
    return plafond


def supprimer_plafond(session: Session, plafond: Plafond) -> None:
    session.delete(plafond)
    session.flush()


def operations_categorisees(
    session: Session, principal: Principal
) -> list[OperationCategorisee]:
    """Vue des opérations prête pour le calcul des plafonds.

    Sans borne de date : les agrégats appliquent eux-mêmes leurs bornes, et deux endroits
    qui filtreraient le temps finiraient par ne plus filtrer pareil.
    """
    lignes = session.execute(
        select(Operation)
        .join(Compte, Compte.id == Operation.compte_id)
        .where(_comptes_autorises(principal))
    ).scalars()

    return [
        OperationCategorisee(
            montant=Cents(o.montant_centimes),
            date_operation=o.date_operation,
            etat=o.etat,
            est_ouverture=o.est_ouverture,
            annulee=o.annulee,
            categorie_id=o.categorie_id,
        )
        for o in lignes
    ]
