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


class ModificationOperation(BaseModel):
    """Champs corrigeables d'une opération.

    `compte_id` et `est_paie` sont absents à dessein. Déplacer une opération changerait
    le solde de deux comptes ; basculer une opération en paie déplacerait les bornes de
    toutes les périodes suivantes, donc des totaux déjà consultés. Ces deux corrections
    passent par une suppression et une nouvelle saisie, où elles se voient.
    """

    libelle: str | None = Field(default=None, min_length=1, max_length=140)
    montant_centimes: int | None = None
    date_operation: dt.date | None = None
    categorie_id: uuid.UUID | None = None


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
    recurrence_id: uuid.UUID | None = None


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


class ModificationRecurrence(BaseModel):
    """Champs modifiables d'un prélèvement.

    Le `compte_id` est absent : déplacer un prélèvement d'un compte à l'autre changerait
    le solde de deux comptes rétroactivement. On arrête et on recrée.
    """

    libelle: str | None = Field(default=None, min_length=1, max_length=140)
    montant_centimes: int | None = None
    ancre: dt.date | None = None
    unite: UniteRecurrence | None = None
    intervalle: int | None = Field(default=None, ge=1, le=60)
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


class BornesDuMois(BaseModel):
    """Premier et dernier jour du mois **civil** courant, bornes incluses.

    Distinct de la période budgétaire, qui va de paie à paie : confondre les deux fait
    afficher un mois à un écran pendant qu'un autre en calcule un différent.
    """

    debut: dt.date
    fin: dt.date


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


class DemandePlafond(BaseModel):
    categorie_id: uuid.UUID
    montant_centimes: int = Field(
        gt=0,
        description="Limite en centimes, toujours positive : c'est une limite, pas une dépense.",
    )


class PlafondPublic(BaseModel):
    """État complet d'un plafond sur la période courante.

    `consomme` et `a_venir` sont exposés séparément et ne doivent JAMAIS être additionnés
    sous le nom de « dépensé » : annoncer 380 € dépensés alors que 150 € ne sont pas
    encore partis est la confusion qui fait cesser de croire l'outil.
    """

    id: uuid.UUID
    categorie_id: uuid.UUID
    categorie_nom: str
    limite_centimes: int
    consomme_centimes: int
    a_venir_centimes: int
    restant_centimes: int
    part_consommee: int
    depasse: bool
    depasse_avec_les_echeances: bool
