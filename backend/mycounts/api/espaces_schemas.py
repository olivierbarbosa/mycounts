"""Contrats publics des espaces financiers."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from mycounts.domain.espaces import RoleEspace, TypeEspace
from mycounts.domain.securite import normaliser_courriel


class EspacePublic(BaseModel):
    id: uuid.UUID
    type: TypeEspace
    nom: str
    role: RoleEspace


class DemandeCreationEspace(BaseModel):
    nom: str = Field(min_length=1, max_length=120)


class MembreEspacePublic(BaseModel):
    id: uuid.UUID
    nom_affichage: str
    courriel: str
    role: RoleEspace
    est_vous: bool
    rejoint_le: dt.datetime


class DemandeInvitationEspace(BaseModel):
    courriel: Annotated[str, AfterValidator(normaliser_courriel)]
    role: RoleEspace = RoleEspace.MEMBRE


class InvitationEspaceCreee(BaseModel):
    jeton: str
    expire_le: dt.datetime


class DemandeAcceptationInvitation(BaseModel):
    jeton: str = Field(min_length=8, max_length=128)


class DemandeRole(BaseModel):
    role: RoleEspace


class DemandeTransfertPropriete(BaseModel):
    utilisateur_id: uuid.UUID


class DemandeSuppressionEspace(BaseModel):
    nom: str = Field(min_length=1, max_length=120)
