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

    code: str | None = None
    """Code à six chiffres, ou code de secours. Absent au premier envoi.

    Un seul champ pour les deux : l'utilisateur qui a perdu son téléphone tape son code de
    secours là où il tapait ses six chiffres, sans avoir à trouver un second formulaire.
    Le serveur essaie le TOTP d'abord, le code de secours ensuite — leurs formats ne se
    confondent pas."""

    faire_confiance: bool = False
    nom_appareil: str | None = Field(default=None, max_length=120)


class DemandeInscription(BaseModel):
    courriel: Courriel
    nom_affichage: str = Field(min_length=1, max_length=80)
    mot_de_passe: str = Field(min_length=LONGUEUR_MINIMALE_MOT_DE_PASSE)


class DemandeJetonIdentite(BaseModel):
    jeton: str = Field(min_length=20, max_length=200)


class DemandeRecuperation(BaseModel):
    courriel: Courriel


class DemandeReinitialisation(BaseModel):
    jeton: str = Field(min_length=20, max_length=200)
    nouveau_mot_de_passe: str = Field(min_length=LONGUEUR_MINIMALE_MOT_DE_PASSE)
    code: str | None = None


class AccuseIdentite(BaseModel):
    message: str


class DemandeActivationSecondFacteur(BaseModel):
    """Le premier code, celui qui prouve que l'application est bien configurée."""

    code: str = Field(min_length=6, max_length=10)
    faire_confiance: bool = False
    nom_appareil: str | None = Field(default=None, max_length=120)


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

    a_un_avatar: bool = False
    """Dit à l'écran s'il doit demander l'image ou dessiner les initiales.

    Sans ce drapeau, le client ne peut le découvrir qu'en demandant l'image et en
    recevant un 404 : une requête sur deux échouerait par conception, et la console
    afficherait une erreur à chaque affichage d'un membre sans portrait — du bruit qui
    finit par masquer les vraies pannes."""

    avatar_version: str | None = None
    """Change à chaque envoi, pour que le navigateur redemande l'image.

    Servie par le SERVEUR et non comptée par l'écran : le portrait paraît à trois endroits
    et l'image d'un autre membre peut changer sans qu'on ait rien fait ici. Un compteur
    local ne rafraîchirait que le formulaire qui l'incrémente, et la bulle garderait
    l'ancienne photo — l'`ETag` ne suffit pas, une image déjà dans le DOM n'est pas
    redemandée tant que son URL ne bouge pas."""

    courriel_verifie: bool = True
    second_facteur_actif: bool = False
    enrolement_requis: bool = False


class AppareilPublic(BaseModel):
    id: uuid.UUID
    nom: str
    cree_le: dt.datetime
    vu_le: dt.datetime
    expire_le: dt.datetime


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

    a_un_avatar: bool = False
    """Dit à l'écran s'il doit demander l'image ou dessiner les initiales.

    Sans ce drapeau, le client ne peut le découvrir qu'en demandant l'image et en
    recevant un 404 : une requête sur deux échouerait par conception, et la console
    afficherait une erreur à chaque affichage d'un membre sans portrait — du bruit qui
    finit par masquer les vraies pannes."""

    avatar_version: str | None = None
    """Change à chaque envoi, pour que le navigateur redemande l'image.

    Servie par le SERVEUR et non comptée par l'écran : le portrait paraît à trois endroits
    et l'image d'un autre membre peut changer sans qu'on ait rien fait ici. Un compteur
    local ne rafraîchirait que le formulaire qui l'incrémente, et la bulle garderait
    l'ancienne photo — l'`ETag` ne suffit pas, une image déjà dans le DOM n'est pas
    redemandée tant que son URL ne bouge pas."""


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


class DemandeRenommage(BaseModel):
    """Le nom affiché, et lui seul.

    Séparé du changement d'adresse et de mot de passe : ceux-là exigent le mot de passe
    en cours, celui-ci non. Les réunir dans un seul corps obligerait à redemander le mot
    de passe pour corriger une faute de frappe dans son prénom.
    """

    nom_affichage: str = Field(min_length=1, max_length=80)


class DemandeChangementMotDePasse(BaseModel):
    """L'ancien est exigé, et ce n'est pas une formalité.

    Une session volée — un téléphone laissé déverrouillé — permettrait sinon de changer le
    mot de passe sans le connaître, donc d'exclure le propriétaire de son propre compte.
    La longueur minimale du NOUVEAU est tenue par le domaine, auteur unique de la règle :
    la répéter ici en ferait une seconde, et les deux divergeraient.
    """

    ancien: str = Field(min_length=1)
    nouveau: str = Field(min_length=1)


class DemandeChangementCourriel(BaseModel):
    """L'adresse de connexion. Le mot de passe est exigé pour la même raison que ci-dessus.

    Aucune vérification n'est possible : l'application n'envoie pas de courriel. Une
    adresse mal tapée verrouille donc le compte à la déconnexion suivante — l'écran le dit
    avant de valider, c'est la seule protection qu'on puisse offrir.
    """

    courriel: Courriel
    mot_de_passe: str = Field(min_length=1)


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


class EnrolementPropose(BaseModel):
    """De quoi configurer une application d'authentification.

    Le secret est rendu EN CLAIR, et c'est nécessaire : sans lui, impossible de configurer
    une application qui ne peut pas scanner — un ordinateur de bureau sans caméra, une
    application qui n'accepte que la saisie manuelle. Il ne sort qu'une fois, vers
    quelqu'un déjà authentifié par mot de passe, sur sa propre session.
    """

    secret: str
    uri: str
    """`otpauth://…`, à ouvrir directement depuis un téléphone."""

    qr_svg: str
    """Le même URI en QR, en SVG inline. Rendu par le serveur : le générer côté client
    demanderait une bibliothèque de plus, pour une image que seul le serveur connaît
    déjà."""


class SecondFacteurActive(BaseModel):
    """Les dix codes de secours, montrés UNE seule fois.

    Les rendre une seconde fois demanderait de les stocker en clair — une porte ouverte à
    côté de celle qu'on vient de fermer. L'écran doit donc insister pour qu'on les note
    avant de fermer.
    """

    codes_de_secours: list[str]


class EtatSecondFacteur(BaseModel):
    actif: bool
    codes_de_secours_restants: int
    """Ce qui reste après usage. Zéro n'est pas une alerte décorative : sans téléphone et
    sans code, il n'existe aucun chemin de retour."""
