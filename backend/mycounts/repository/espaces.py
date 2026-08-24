"""Espaces financiers, appartenances et cycle de vie des foyers.

Toutes les fonctions qui reçoivent un espace arbitraire revérifient l'appartenance en
base. Un UUID fourni par le client n'est jamais une autorisation.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, cast

from sqlalchemy import CursorResult, delete, func, select
from sqlalchemy.orm import Session

from mycounts.domain.espaces import RoleEspace, TypeEspace
from mycounts.models.auth import (
    Appartenance,
    Espace,
    Foyer,
    InvitationEspace,
    Utilisateur,
)
from mycounts.models.budget import (
    Categorie,
    Compte,
    CorrespondanceImport,
    Enveloppe,
    MouvementEnveloppe,
    Operation,
    Plafond,
    Recurrence,
)
from mycounts.repository.base import Principal


def espaces_de(session: Session, utilisateur_id: uuid.UUID) -> list[tuple[Espace, Appartenance]]:
    lignes = session.execute(
        select(Espace, Appartenance)
        .join(Appartenance, Appartenance.espace_id == Espace.id)
        .where(
            Appartenance.utilisateur_id == utilisateur_id,
            Appartenance.actif.is_(True),
            Espace.actif.is_(True),
        )
        .order_by(Espace.type, Espace.cree_le, Espace.id)
    ).all()
    return [(ligne[0], ligne[1]) for ligne in lignes]


def espace_personnel_de(
    session: Session, utilisateur_id: uuid.UUID
) -> tuple[Espace, Appartenance] | None:
    ligne = session.execute(
        select(Espace, Appartenance)
        .join(Appartenance, Appartenance.espace_id == Espace.id)
        .where(
            Espace.type == TypeEspace.PERSONNEL,
            Espace.proprietaire_personnel_id == utilisateur_id,
            Espace.actif.is_(True),
            Appartenance.utilisateur_id == utilisateur_id,
            Appartenance.actif.is_(True),
        )
        .with_for_update(read=True, of=Appartenance)
    ).one_or_none()
    return None if ligne is None else (ligne[0], ligne[1])


def appartenance_active(
    session: Session, *, utilisateur_id: uuid.UUID, espace_id: uuid.UUID
) -> tuple[Espace, Appartenance] | None:
    ligne = session.execute(
        select(Espace, Appartenance)
        .join(Appartenance, Appartenance.espace_id == Espace.id)
        .where(
            Espace.id == espace_id,
            Espace.actif.is_(True),
            Appartenance.utilisateur_id == utilisateur_id,
            Appartenance.actif.is_(True),
        )
        .with_for_update(read=True, of=Appartenance)
    ).one_or_none()
    return None if ligne is None else (ligne[0], ligne[1])


def principal_pour(
    session: Session, *, utilisateur_id: uuid.UUID, espace_id: uuid.UUID | None
) -> Principal | None:
    """Résout l'espace demandé ; l'absence signifie l'espace personnel.

    Un UUID inconnu ou non autorisé ne retombe volontairement pas ici : l'appelant peut
    alors appliquer le repli personnel sans révéler si cet UUID existe.
    """
    ligne = (
        espace_personnel_de(session, utilisateur_id)
        if espace_id is None
        else appartenance_active(session, utilisateur_id=utilisateur_id, espace_id=espace_id)
    )
    if ligne is None:
        return None
    espace, appartenance = ligne
    return Principal(
        utilisateur_id=utilisateur_id,
        espace_id=espace.id,
        foyer_id=espace.id,  # colonne legacy encore présente pendant la migration
        role=RoleEspace(appartenance.role),
        type_espace=TypeEspace(espace.type),
    )


def creer_espace_personnel(
    session: Session, utilisateur: Utilisateur, *, nom: str | None = None
) -> tuple[Espace, Appartenance]:
    existant = espace_personnel_de(session, utilisateur.id)
    if existant is not None:
        return existant
    espace = Espace(
        type=TypeEspace.PERSONNEL,
        nom=nom or utilisateur.nom_affichage,
        proprietaire_personnel_id=utilisateur.id,
    )
    session.add(espace)
    session.flush()
    # Support des colonnes `foyer_id` maintenues durant la migration progressive.
    session.add(Foyer(id=espace.id, nom=espace.nom))
    appartenance = Appartenance(
        utilisateur_id=utilisateur.id,
        espace_id=espace.id,
        role=RoleEspace.PROPRIETAIRE,
    )
    session.add(appartenance)
    session.flush()
    return espace, appartenance


def creer_foyer(session: Session, principal: Principal, *, nom: str) -> tuple[Espace, Appartenance]:
    espace = Espace(type=TypeEspace.FOYER, nom=nom)
    session.add(espace)
    session.flush()
    session.add(Foyer(id=espace.id, nom=nom))
    appartenance = Appartenance(
        utilisateur_id=principal.utilisateur_id,
        espace_id=espace.id,
        role=RoleEspace.PROPRIETAIRE,
    )
    session.add(appartenance)
    session.flush()
    return espace, appartenance


def membres_de(session: Session, principal: Principal) -> list[tuple[Utilisateur, Appartenance]]:
    lignes = session.execute(
        select(Utilisateur, Appartenance)
        .join(Appartenance, Appartenance.utilisateur_id == Utilisateur.id)
        .where(
            Appartenance.espace_id == principal.espace_id,
            Appartenance.actif.is_(True),
            Utilisateur.actif.is_(True),
        )
        .order_by(Appartenance.rejoint_le, Utilisateur.id)
    ).all()
    return [(ligne[0], ligne[1]) for ligne in lignes]


def creer_invitation(
    session: Session,
    principal: Principal,
    *,
    courriel: str,
    role: RoleEspace,
    empreinte_jeton: str,
    expire_le: dt.datetime,
) -> InvitationEspace:
    if principal.type_espace is not TypeEspace.FOYER or not principal.role.peut_gerer_les_membres:
        raise PermissionError("Droit de gestion des membres requis.")
    if role is RoleEspace.PROPRIETAIRE:
        raise ValueError("La propriété se transfère après l'adhésion.")
    invitation = InvitationEspace(
        espace_id=principal.espace_id,
        courriel_destinataire=courriel,
        role=role,
        empreinte_jeton=empreinte_jeton,
        creee_par_id=principal.utilisateur_id,
        expire_le=expire_le,
    )
    session.add(invitation)
    session.flush()
    return invitation


def invitation_utilisable(
    session: Session,
    *,
    empreinte_jeton: str,
    courriel: str,
    a_l_instant: dt.datetime,
) -> InvitationEspace | None:
    return session.execute(
        select(InvitationEspace)
        .where(
            InvitationEspace.empreinte_jeton == empreinte_jeton,
            InvitationEspace.courriel_destinataire == courriel,
            InvitationEspace.expire_le > a_l_instant,
            InvitationEspace.utilisee_le.is_(None),
        )
        .with_for_update()
    ).scalar_one_or_none()


def accepter_invitation(
    session: Session,
    invitation: InvitationEspace,
    *,
    utilisateur_id: uuid.UUID,
    a_l_instant: dt.datetime,
) -> Appartenance:
    existante = session.execute(
        select(Appartenance).where(
            Appartenance.utilisateur_id == utilisateur_id,
            Appartenance.espace_id == invitation.espace_id,
        )
    ).scalar_one_or_none()
    if existante is None:
        existante = Appartenance(
            utilisateur_id=utilisateur_id,
            espace_id=invitation.espace_id,
            role=invitation.role,
        )
        session.add(existante)
    elif not existante.actif:
        existante.actif = True
        existante.role = invitation.role
    # Une invitation ne change jamais le rôle d'un membre déjà actif : sinon accepter
    # une ancienne invitation « membre » pourrait rétrograder le propriétaire actuel.
    invitation.utilisee_le = a_l_instant
    session.flush()
    return existante


def changer_role(
    session: Session,
    principal: Principal,
    *,
    utilisateur_id: uuid.UUID,
    role: RoleEspace,
) -> Appartenance | None:
    if not principal.role.peut_gerer_les_membres or role is RoleEspace.PROPRIETAIRE:
        raise PermissionError("Rôle non modifiable.")
    cible = session.execute(
        select(Appartenance).where(
            Appartenance.espace_id == principal.espace_id,
            Appartenance.utilisateur_id == utilisateur_id,
            Appartenance.actif.is_(True),
            Appartenance.role != RoleEspace.PROPRIETAIRE,
        )
    ).scalar_one_or_none()
    if cible is not None:
        cible.role = role
        session.flush()
    return cible


def transferer_propriete(
    session: Session, principal: Principal, *, vers_utilisateur_id: uuid.UUID
) -> None:
    if (
        principal.type_espace is not TypeEspace.FOYER
        or principal.role is not RoleEspace.PROPRIETAIRE
    ):
        raise PermissionError("Seul le propriétaire peut transférer le foyer.")
    if vers_utilisateur_id == principal.utilisateur_id:
        raise ValueError("Vous êtes déjà propriétaire du foyer.")
    appartenances = (
        session.execute(
            select(Appartenance)
            .where(
                Appartenance.espace_id == principal.espace_id,
                Appartenance.actif.is_(True),
            )
            .order_by(Appartenance.id)
            .with_for_update()
        )
        .scalars()
        .all()
    )
    proprietaire = next(
        (
            appartenance
            for appartenance in appartenances
            if appartenance.utilisateur_id == principal.utilisateur_id
        ),
        None,
    )
    if proprietaire is None or RoleEspace(proprietaire.role) is not RoleEspace.PROPRIETAIRE:
        raise PermissionError("La propriété du foyer a déjà changé.")
    cible = next(
        (
            appartenance
            for appartenance in appartenances
            if appartenance.utilisateur_id == vers_utilisateur_id
        ),
        None,
    )
    if cible is None:
        raise LookupError("Membre introuvable.")
    proprietaire.role = RoleEspace.ADMINISTRATEUR
    # L'index partiel PostgreSQL garantissant un unique propriétaire n'est pas
    # différable : libérer le rôle avant de l'attribuer au membre cible.
    session.flush([proprietaire])
    cible.role = RoleEspace.PROPRIETAIRE
    session.flush([cible])


def quitter_foyer(session: Session, principal: Principal) -> None:
    if principal.type_espace is not TypeEspace.FOYER:
        raise ValueError("L'espace personnel ne peut pas être quitté.")
    if principal.role is RoleEspace.PROPRIETAIRE:
        raise PermissionError("Transférez d'abord la propriété du foyer.")
    efface = cast(
        "CursorResult[Any]",
        session.execute(
            delete(Appartenance).where(
                Appartenance.espace_id == principal.espace_id,
                Appartenance.utilisateur_id == principal.utilisateur_id,
            )
        ),
    )
    if efface.rowcount != 1:
        raise LookupError("Appartenance introuvable.")


def retirer_membre(session: Session, principal: Principal, *, utilisateur_id: uuid.UUID) -> None:
    if not principal.role.peut_gerer_les_membres:
        raise PermissionError("Droit de gestion des membres requis.")
    if utilisateur_id == principal.utilisateur_id:
        raise ValueError("Utilisez l'action quitter.")
    cible = session.execute(
        select(Appartenance).where(
            Appartenance.espace_id == principal.espace_id,
            Appartenance.utilisateur_id == utilisateur_id,
            Appartenance.actif.is_(True),
        )
    ).scalar_one_or_none()
    if cible is None:
        raise LookupError("Membre introuvable.")
    if RoleEspace(cible.role) is RoleEspace.PROPRIETAIRE:
        raise PermissionError("Le propriétaire ne peut pas être retiré.")
    session.delete(cible)
    session.flush()


def supprimer_foyer(session: Session, principal: Principal) -> None:
    if (
        principal.type_espace is not TypeEspace.FOYER
        or principal.role is not RoleEspace.PROPRIETAIRE
    ):
        raise PermissionError("Seul le propriétaire peut supprimer le foyer.")
    espace_id = principal.espace_id
    # L'ordre explicite garde la suppression lisible malgré les anciennes FK RESTRICT.
    session.execute(delete(MouvementEnveloppe).where(MouvementEnveloppe.espace_id == espace_id))
    session.execute(delete(Enveloppe).where(Enveloppe.espace_id == espace_id))
    session.execute(delete(Operation).where(Operation.espace_id == espace_id))
    session.execute(delete(Recurrence).where(Recurrence.espace_id == espace_id))
    session.execute(delete(Plafond).where(Plafond.espace_id == espace_id))
    session.execute(delete(CorrespondanceImport).where(CorrespondanceImport.espace_id == espace_id))
    session.execute(delete(Compte).where(Compte.espace_id == espace_id))
    session.execute(delete(Categorie).where(Categorie.espace_id == espace_id))
    # `Utilisateur.foyer_id` est une colonne de transition non nullable. Si ce foyer est
    # celui du modèle historique, chaque identité est repointée vers le conteneur legacy
    # de son espace personnel avant de supprimer le foyer. Aucune donnée financière ne
    # bouge : celles-ci sont déjà portées par `espace_id`.
    utilisateurs_legacy = list(
        session.execute(select(Utilisateur).where(Utilisateur.foyer_id == espace_id)).scalars()
    )
    for utilisateur in utilisateurs_legacy:
        personnel = espace_personnel_de(session, utilisateur.id)
        if personnel is None:
            personnel = creer_espace_personnel(session, utilisateur)
        utilisateur.foyer_id = personnel[0].id
        utilisateur.est_proprietaire = False
    session.flush()
    session.execute(delete(Espace).where(Espace.id == espace_id))
    # Le foyer legacy a le même UUID et ne contient plus aucune donnée.
    session.execute(delete(Foyer).where(Foyer.id == espace_id))
    session.flush()


def nombre_proprietaires(session: Session, espace_id: uuid.UUID) -> int:
    return int(
        session.execute(
            select(func.count(Appartenance.id)).where(
                Appartenance.espace_id == espace_id,
                Appartenance.actif.is_(True),
                Appartenance.role == RoleEspace.PROPRIETAIRE,
            )
        ).scalar_one()
    )
