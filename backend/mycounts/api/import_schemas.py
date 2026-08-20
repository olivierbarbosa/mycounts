"""Schémas de l'import de relevé."""

from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, Field

from mycounts.domain.import_releve import SensImporte


class LigneImportPublique(BaseModel):
    """Une ligne proposée. Rien n'est écrit tant qu'elle n'est pas validée."""

    cle: str
    date_operation: dt.date
    libelle: str
    montant_centimes: int
    sens: SensImporte
    categorie_banque: str
    """La catégorie que la BANQUE a posée. Affichée pour aider à choisir celle du foyer,
    jamais appliquée d'office : ce ne sont pas les mêmes catégories, et se tromper
    silencieusement de rangement est pire que de ne rien ranger."""

    deja_importee: bool
    categorie_proposee_id: uuid.UUID | None
    """Ce que le foyer a rangé ainsi la dernière fois. `None` s'il n'a rien appris —
    ranger de travers est pire que ne pas ranger."""

    doublon_probable: str | None
    """Libellé et date d'une opération DÉJÀ enregistrée que cette ligne dupliquerait,
    typiquement un prélèvement saisi comme récurrence. Signalé, jamais décidé."""


class RecurrenceProposee(BaseModel):
    """Un prélèvement régulier repéré dans le relevé, qu'aucune récurrence ne couvre."""

    libelle: str
    montant_centimes: int
    cadence: str
    occurrences: int
    derniere: dt.date


class RevueImport(BaseModel):
    total: int
    nouvelles: int
    deja_importees: int
    lignes: list[LigneImportPublique]
    recurrences_proposees: list[RecurrenceProposee]
    """Repérées dans le relevé, jamais créées d'office : un écran qui ajouterait des
    récurrences tout seul remplirait le calendrier de prélèvements que personne n'a
    validés, et il faudrait ensuite les défaire un par un."""


class LigneAValider(BaseModel):
    """Ce que l'utilisateur retient d'une ligne, après l'avoir vue."""

    cle: str = Field(max_length=200)
    date_operation: dt.date
    libelle: str = Field(min_length=1, max_length=140)
    montant_centimes: int
    categorie_id: uuid.UUID | None = None
    """Choisie par l'utilisateur pendant la revue, ou laissée vide."""

    categorie_banque: str = ""
    """Reprise telle quelle pour APPRENDRE le rangement. Sans elle, le choix de
    l'utilisateur ne servirait qu'à cette ligne-ci et il faudrait tout refaire au prochain
    import."""


class DemandeValidationImport(BaseModel):
    """Les lignes retenues, et le compte où les écrire.

    Le compte est demandé UNE fois pour tout le lot : un relevé porte sur un compte, et le
    faire choisir ligne à ligne transformerait une validation en corvée.
    """

    compte_id: uuid.UUID
    lignes: list[LigneAValider]
