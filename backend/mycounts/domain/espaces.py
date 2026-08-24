"""Rôles et natures des espaces financiers.

Un espace est la frontière d'autorisation. Le type n'accorde aucun droit à lui seul :
les droits viennent toujours de l'appartenance active de l'utilisateur.
"""

from __future__ import annotations

from enum import StrEnum


class TypeEspace(StrEnum):
    PERSONNEL = "personnel"
    FOYER = "foyer"


class RoleEspace(StrEnum):
    PROPRIETAIRE = "proprietaire"
    ADMINISTRATEUR = "administrateur"
    MEMBRE = "membre"

    @property
    def peut_gerer_les_membres(self) -> bool:
        return self in {RoleEspace.PROPRIETAIRE, RoleEspace.ADMINISTRATEUR}

    @property
    def peut_supprimer(self) -> bool:
        return self is RoleEspace.PROPRIETAIRE
