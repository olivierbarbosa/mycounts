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
from mycounts.domain.recurrence import UniteRecurrence
from mycounts.models.budget import NatureCategorie, TeinteCategorie


class ComptePublic(BaseModel):
    id: uuid.UUID
    nom: str
    prive: bool


class DemandeCompte(BaseModel):
    nom: str = Field(min_length=1, max_length=80)
    prive: bool = True
    solde_ouverture_centimes: int = Field(
        default=0,
        description=(
            "Solde du compte au moment de sa création, en centimes. Enregistré comme une "
            "opération d'ouverture — un solde reste une somme d'opérations. Zéro n'en crée "
            "aucune."
        ),
    )


class CategoriePublique(BaseModel):
    id: uuid.UUID
    nom: str
    nature: NatureCategorie
    teinte: TeinteCategorie


class DemandeCategorie(BaseModel):
    nom: str = Field(min_length=1, max_length=60)
    nature: NatureCategorie
    teinte: TeinteCategorie


class ModificationCategorie(BaseModel):
    """La `nature` est absente volontairement : la changer inverserait le signe attendu
    de toutes les opérations déjà classées, et donc les totaux de mois déjà clos."""

    nom: str | None = Field(default=None, min_length=1, max_length=60)
    teinte: TeinteCategorie | None = None
    archivee: bool | None = None


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
    est_ouverture: bool


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


class DemandeRecurrence(BaseModel):
    compte_id: uuid.UUID
    libelle: str = Field(min_length=1, max_length=140)
    montant_centimes: int = Field(
        description="Entier signé. Négatif = prélèvement, positif = revenu régulier."
    )
    ancre: dt.date = Field(
        description=(
            "Date de la PREMIÈRE échéance. Toutes les suivantes s'en déduisent — jamais "
            "de l'échéance précédente, sinon une récurrence au 31 resterait bloquée au 28 "
            "après son premier février."
        )
    )
    unite: UniteRecurrence
    intervalle: int = Field(default=1, ge=1, le=60)
    categorie_id: uuid.UUID | None = None
    fin: dt.date | None = None


class RecurrencePublique(BaseModel):
    id: uuid.UUID
    compte_id: uuid.UUID
    categorie_id: uuid.UUID | None
    libelle: str
    montant_centimes: int
    ancre: dt.date
    unite: UniteRecurrence
    intervalle: int
    fin: dt.date | None
    active: bool


class EcheanceAgenda(BaseModel):
    """Une échéance à venir, telle qu'affichée dans l'agenda.

    Une échéance n'est PAS une opération : elle n'a pas d'identifiant propre tant qu'elle
    n'a pas été matérialisée. Les confondre ferait croire qu'on peut la modifier
    individuellement, alors qu'elle est recalculée à chaque affichage.
    """

    recurrence_id: uuid.UUID
    libelle: str
    montant_centimes: int
    date_echeance: dt.date
    categorie_id: uuid.UUID | None
