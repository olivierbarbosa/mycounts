"""Contrats d'entrée et de sortie de l'API.

Le serveur fait foi : ces schémas sont la seule définition du contrat, et le client
génère ses types depuis l'OpenAPI produit ici. Aucun type n'est écrit à la main côté
client.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from mycounts.domain.securite import LONGUEUR_MINIMALE_MOT_DE_PASSE, normaliser_courriel

Courriel = Annotated[str, AfterValidator(normaliser_courriel)]
"""Adresse validée ET normalisée par le domaine, pas par un validateur parallèle.

Utiliser `EmailStr` ici aurait donné deux auteurs à la même règle : le schéma d'un côté,
les scripts de l'autre — et ils ont effectivement divergé (ERREURS.md #009)."""


class DemandeConnexion(BaseModel):
    courriel: Courriel
    mot_de_passe: str = Field(min_length=1)


class DemandeAdhesion(BaseModel):
    """Rejoindre un foyer avec un code d'invitation."""

    code: str = Field(min_length=8, max_length=64)
    courriel: Courriel
    nom_affichage: str = Field(min_length=1, max_length=80)
    mot_de_passe: str = Field(min_length=LONGUEUR_MINIMALE_MOT_DE_PASSE)


class UtilisateurPublic(BaseModel):
    id: uuid.UUID
    courriel: str
    nom_affichage: str
    foyer_id: uuid.UUID


class InvitationCreee(BaseModel):
    """Le code n'est renvoyé qu'ici, une seule fois.

    Seule son empreinte est conservée : ni la base ni les journaux ne permettent de le
    retrouver ensuite.
    """

    code: str
    expire_le: dt.datetime
