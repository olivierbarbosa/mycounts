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
    foyer_nom: str
    """Le nom en clair, parce que l'écran doit l'AFFICHER avant de le faire retaper : une
    confirmation qui demande un nom sans le montrer se termine par un abandon, pas par une
    réflexion."""

    est_proprietaire: bool
    """Décidé par le serveur. L'écran s'en sert pour montrer ou cacher la zone de danger,
    mais l'autorisation réelle est revérifiée à chaque appel — cacher un bouton n'a jamais
    empêché personne d'appeler la route."""


class MembrePublic(BaseModel):
    """Un membre du foyer, tel que les autres membres peuvent le voir.

    Ni mot de passe, ni session, ni solde : savoir avec qui l'on partage un compte joint
    ne donne aucun droit sur l'argent de l'autre, et cette classe est l'endroit où cette
    limite est visible.
    """

    id: uuid.UUID
    nom_affichage: str
    courriel: str
    cree_le: dt.datetime
    est_vous: bool
    """Marqué par le SERVEUR et non déduit à l'écran : le client connaît son nom, pas son
    identifiant, et deux membres peuvent porter le même nom d'affichage."""

    est_proprietaire: bool
    """Qui administre le foyer. Visible de tous les membres, comme la liste elle-même :
    savoir à qui s'adresser pour une invitation n'est pas une information sensible."""


class InvitationCreee(BaseModel):
    """Le code n'est renvoyé qu'ici, une seule fois.

    Seule son empreinte est conservée : ni la base ni les journaux ne permettent de le
    retrouver ensuite.
    """

    code: str
    expire_le: dt.datetime


class DemandeSuppressionCompte(BaseModel):
    """Confirmation d'une destruction sans retour.

    L'adresse est redemandée en clair. Ce n'est pas un secret — l'écran l'affiche juste
    au-dessus du champ — et ce n'est pas censé l'être : la barrière ne protège pas contre
    quelqu'un qui voudrait supprimer son compte, elle protège contre quelqu'un qui ne le
    voudrait PAS et dont le doigt a glissé. Un bouton, même rouge, même précédé d'un
    « êtes-vous sûr ? », se traverse d'un geste réflexe ; retaper une adresse ne
    s'improvise pas.

    C'est l'adresse et non le nom du foyer, depuis le 21 août 2026 : ce qu'on détruit ici
    est SON compte. Faire retaper le nom du foyer pour effacer sa propre identité
    désignait la mauvaise chose, et c'est précisément la confusion que ce lot défait.
    """

    courriel: str = Field(min_length=1, max_length=254)
