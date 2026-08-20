"""Schémas des enveloppes.

Aucun de ces schémas ne porte de solde à écrire : le solde se recalcule depuis le journal.
Ce qui entre, ce sont des MOUVEMENTS.
"""

from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, Field

from mycounts.domain.enveloppes import TypeMouvement


class DemandeEnveloppe(BaseModel):
    nom: str = Field(min_length=1, max_length=80)
    categorie_id: uuid.UUID | None = None
    compte_prefere_id: uuid.UUID | None = None
    cible_centimes: int | None = Field(default=None, gt=0)
    date_cible: dt.date | None = None
    allocation_initiale_centimes: int = Field(
        default=0,
        ge=0,
        description=(
            "Somme réservée d'emblée. Enregistrée comme un MOUVEMENT du journal, jamais "
            "comme un solde de départ : sinon ce serait la seule valeur que l'historique "
            "ignore."
        ),
    )
    type_allocation_initiale: TypeMouvement = TypeMouvement.ALLOCATION


class ModificationEnveloppe(BaseModel):
    """Champs absents = inchangés.

    Conséquence assumée : on ne peut pas RETIRER une cible ici, seulement la changer.
    Retirer une cible fait cesser toute recommandation mensuelle — c'est un geste rare et
    lourd de sens, il aura sa propre route plutôt qu'un `null` ambigu.
    """

    nom: str | None = Field(default=None, min_length=1, max_length=80)
    categorie_id: uuid.UUID | None = None
    compte_prefere_id: uuid.UUID | None = None
    cible_centimes: int | None = Field(default=None, gt=0)
    date_cible: dt.date | None = None
    archive: bool | None = None


class DemandeMouvement(BaseModel):
    type: TypeMouvement
    montant_centimes: int = Field(
        gt=0,
        description=(
            "TOUJOURS positif : c'est le type qui dit le sens. Un montant signé rendrait "
            "possible une allocation négative, c'est-à-dire une reprise déguisée."
        ),
    )
    date_mouvement: dt.date | None = None
    libelle: str = Field(default="", max_length=140)


class MouvementPublic(BaseModel):
    id: uuid.UUID
    type: TypeMouvement
    montant_centimes: int
    date_mouvement: dt.date
    libelle: str


class EnveloppePublique(BaseModel):
    id: uuid.UUID
    nom: str
    categorie_id: uuid.UUID | None
    categorie_nom: str | None
    compte_prefere_id: uuid.UUID | None
    cible_centimes: int | None
    date_cible: dt.date | None
    solde_centimes: int
    """Peut être NÉGATIF : une dépense réelle n'est jamais bloquée par une enveloppe
    mal financée."""

    place_centimes: int | None
    """Ce qu'il manque pour atteindre la cible. `None` s'il n'y a pas de cible — et non
    zéro, qui se lirait comme « enveloppe pleine »."""

    part: int
    archive: bool


class RepartitionPublique(BaseModel):
    """L'épargne découpée, et ce qui reste libre."""

    epargne_totale_centimes: int
    reserve_centimes: int
    """Somme des soldes POSITIFS seulement : une enveloppe dans le rouge ne rogne pas ce
    que les autres promettent."""

    non_affecte_centimes: int
    """Peut être négatif : l'argent a fondu sous ce qui était réservé."""

    decouvert: bool
    enveloppes: list[EnveloppePublique]
