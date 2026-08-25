"""API des espaces personnels et foyers multiples."""

from __future__ import annotations

import uuid
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, status

from mycounts.api.dependances import PrincipalCourant, SessionBase
from mycounts.api.espaces_schemas import (
    DemandeAcceptationInvitation,
    DemandeCreationEspace,
    DemandeInvitationEspace,
    DemandeRole,
    DemandeSuppressionEspace,
    DemandeTransfertPropriete,
    EspacePublic,
    InvitationEspaceCreee,
    MembreEspacePublic,
)
from mycounts.config import charger_configuration
from mycounts.domain.espaces import RoleEspace, TypeEspace
from mycounts.domain.securite import (
    empreinte_jeton,
    engendrer_jeton,
    expiration_invitation,
    maintenant,
)
from mycounts.models.auth import Appartenance, Espace
from mycounts.repository import auth as depot_auth
from mycounts.repository import budget as depot_budget
from mycounts.repository import espaces as depot
from mycounts.repository import identite as depot_identite

routeur = APIRouter(prefix="/espaces", tags=["espaces"])


def _public(espace: Espace, appartenance: Appartenance) -> EspacePublic:
    # Les objets viennent du repository ; centraliser la conversion garde l'API libre de
    # requêtes SQL tout en conservant des types de sortie stricts.
    return EspacePublic(
        id=espace.id,
        type=TypeEspace(espace.type),
        nom=espace.nom,
        role=RoleEspace(appartenance.role),
    )


@routeur.get("", response_model=list[EspacePublic])
def lister_espaces(session: SessionBase, principal: PrincipalCourant) -> list[EspacePublic]:
    return [_public(e, a) for e, a in depot.espaces_de(session, principal.utilisateur_id)]


@routeur.post("", response_model=EspacePublic, status_code=status.HTTP_201_CREATED)
def creer_un_foyer(
    demande: DemandeCreationEspace,
    session: SessionBase,
    principal: PrincipalCourant,
) -> EspacePublic:
    espace, appartenance = depot.creer_foyer(session, principal, nom=demande.nom.strip())
    depot_budget.creer_categories_initiales(session, espace.id)
    session.commit()
    return _public(espace, appartenance)


@routeur.get("/membres", response_model=list[MembreEspacePublic])
def lister_les_membres(
    session: SessionBase, principal: PrincipalCourant
) -> list[MembreEspacePublic]:
    return [
        MembreEspacePublic(
            id=utilisateur.id,
            nom_affichage=utilisateur.nom_affichage,
            courriel=utilisateur.courriel,
            role=RoleEspace(appartenance.role),
            est_vous=utilisateur.id == principal.utilisateur_id,
            rejoint_le=appartenance.rejoint_le,
        )
        for utilisateur, appartenance in depot.membres_de(session, principal)
    ]


@routeur.post(
    "/invitations",
    response_model=InvitationEspaceCreee,
    status_code=status.HTTP_201_CREATED,
)
def inviter(
    demande: DemandeInvitationEspace,
    session: SessionBase,
    principal: PrincipalCourant,
) -> InvitationEspaceCreee:
    jeton = engendrer_jeton()
    expire_le = expiration_invitation()
    try:
        invitation = depot.creer_invitation(
            session,
            principal,
            courriel=demande.courriel,
            role=demande.role,
            empreinte_jeton=empreinte_jeton(jeton),
            expire_le=expire_le,
        )
    except (PermissionError, ValueError) as cause:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(cause)) from cause
    courant = depot.appartenance_active(
        session,
        utilisateur_id=principal.utilisateur_id,
        espace_id=principal.espace_id,
    )
    if courant is None:  # pragma: no cover - le principal vient de cette appartenance
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Espace indisponible.")
    configuration = charger_configuration()
    lien = (
        f"{configuration.url_publique.rstrip('/')}/?"
        + urlencode({"invitation": jeton})
    )
    depot_identite.mettre_en_file(
        session,
        utilisateur_id=principal.utilisateur_id,
        cle_idempotence=f"invitation_espace:{invitation.id}",
        destinataire=demande.courriel,
        modele="invitation_espace",
        donnees={"nom": "Bonjour", "lien": lien, "foyer": courant[0].nom},
    )
    session.commit()
    return InvitationEspaceCreee(jeton=jeton, expire_le=expire_le)


@routeur.post("/invitations/accepter", response_model=EspacePublic)
def accepter(
    demande: DemandeAcceptationInvitation,
    session: SessionBase,
    principal: PrincipalCourant,
) -> EspacePublic:
    utilisateur = depot_auth.utilisateur_par_id(session, principal.utilisateur_id)
    if utilisateur is None:  # pragma: no cover - session déjà validée
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    invitation = depot.invitation_utilisable(
        session,
        empreinte_jeton=empreinte_jeton(demande.jeton),
        courriel=utilisateur.courriel,
        a_l_instant=maintenant(),
    )
    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invitation inconnue, expirée, utilisée ou destinée à une autre adresse.",
        )
    appartenance = depot.accepter_invitation(
        session,
        invitation,
        utilisateur_id=principal.utilisateur_id,
        a_l_instant=maintenant(),
    )
    trouve = depot.appartenance_active(
        session,
        utilisateur_id=principal.utilisateur_id,
        espace_id=invitation.espace_id,
    )
    if trouve is None:  # pragma: no cover - créé juste au-dessus
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    session.commit()
    return _public(trouve[0], appartenance)


@routeur.patch("/membres/{utilisateur_id}", response_model=MembreEspacePublic)
def modifier_le_role(
    utilisateur_id: uuid.UUID,
    demande: DemandeRole,
    session: SessionBase,
    principal: PrincipalCourant,
) -> MembreEspacePublic:
    try:
        appartenance = depot.changer_role(
            session, principal, utilisateur_id=utilisateur_id, role=demande.role
        )
    except PermissionError as cause:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(cause)) from cause
    utilisateur = depot_auth.utilisateur_par_id(session, utilisateur_id)
    if appartenance is None or utilisateur is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membre introuvable.")
    session.commit()
    return MembreEspacePublic(
        id=utilisateur.id,
        nom_affichage=utilisateur.nom_affichage,
        courriel=utilisateur.courriel,
        role=RoleEspace(appartenance.role),
        est_vous=utilisateur.id == principal.utilisateur_id,
        rejoint_le=appartenance.rejoint_le,
    )


@routeur.post("/propriete", status_code=status.HTTP_204_NO_CONTENT)
def transferer(
    demande: DemandeTransfertPropriete,
    session: SessionBase,
    principal: PrincipalCourant,
) -> None:
    try:
        depot.transferer_propriete(session, principal, vers_utilisateur_id=demande.utilisateur_id)
    except PermissionError as cause:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(cause)) from cause
    except ValueError as cause:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(cause)) from cause
    except LookupError as cause:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(cause)) from cause
    session.commit()


@routeur.delete("/membres/moi", status_code=status.HTTP_204_NO_CONTENT)
def quitter(session: SessionBase, principal: PrincipalCourant) -> None:
    try:
        depot.quitter_foyer(session, principal)
    except ValueError as cause:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(cause)) from cause
    except PermissionError as cause:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(cause)) from cause
    session.commit()


@routeur.delete("/membres/{utilisateur_id}", status_code=status.HTTP_204_NO_CONTENT)
def exclure(
    utilisateur_id: uuid.UUID,
    session: SessionBase,
    principal: PrincipalCourant,
) -> None:
    try:
        depot.retirer_membre(session, principal, utilisateur_id=utilisateur_id)
    except (PermissionError, ValueError) as cause:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(cause)) from cause
    except LookupError as cause:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(cause)) from cause
    session.commit()


@routeur.delete("/{espace_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer(
    espace_id: uuid.UUID,
    demande: DemandeSuppressionEspace,
    session: SessionBase,
    principal: PrincipalCourant,
) -> None:
    if espace_id != principal.espace_id or principal.type_espace is not TypeEspace.FOYER:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foyer introuvable.")
    courant = next(
        (e for e, _ in depot.espaces_de(session, principal.utilisateur_id) if e.id == espace_id),
        None,
    )
    if courant is None or demande.nom.strip() != courant.nom:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Retapez exactement le nom du foyer.",
        )
    try:
        depot.supprimer_foyer(session, principal)
    except PermissionError as cause:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(cause)) from cause
    session.commit()
