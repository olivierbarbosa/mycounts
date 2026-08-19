"""Contrats de l'API budget.

Les montants circulent en **centimes entiers** (`montant_centimes`), jamais en euros
décimaux : un `12.50` en JSON redeviendrait un flottant côté client, et l'invariant du
projet s'arrêterait à la frontière HTTP.
"""

from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, Field

from mycounts.domain.agregats import EtatOperation
from mycounts.models.budget import NatureCategorie, TeinteCategorie


class ComptePublic(BaseModel):
    id: uuid.UUID
    nom: str
    prive: bool


class DemandeCompte(BaseModel):
    nom: str = Field(min_length=1, max_length=80)
    prive: bool = True


class CategoriePublique(BaseModel):
    id: uuid.UUID
    nom: str
    nature: NatureCategorie
    teinte: TeinteCategorie


class DemandeCategorie(BaseModel):
    nom: str = Field(min_length=1, max_length=60)
    nature: NatureCategorie
    teinte: TeinteCategorie


class DemandeOperation(BaseModel):
    compte_id: uuid.UUID
    libelle: str = Field(min_length=1, max_length=140)
    montant_centimes: int = Field(
        description="Entier signé. Négatif = sortie, positif = entrée. Zéro refusé."
    )
    date_operation: dt.date
    categorie_id: uuid.UUID | None = None
    est_paie: bool = False


class OperationPublique(BaseModel):
    id: uuid.UUID
    compte_id: uuid.UUID
    categorie_id: uuid.UUID | None
    libelle: str
    montant_centimes: int
    date_operation: dt.date
    etat: EtatOperation
    est_paie: bool


class PeriodePublique(BaseModel):
    debut: dt.date
    fin: dt.date
    fin_estimee: bool


class ResumePublic(BaseModel):
    """Les quatre grandeurs, toutes exposées.

    Le solde réel est renvoyé même si l'interface met le projeté en avant : sans lui,
    aucun écart avec la banque ne serait diagnosticable.
    """

    periode: PeriodePublique
    solde_projete: int
    solde_reel: int
    solde_a_confirmer: int
    depenses_de_periode: int
