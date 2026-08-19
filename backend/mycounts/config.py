"""Configuration de l'application, lue depuis l'environnement.

Aucune valeur secrète n'a de défaut en dur : une variable manquante doit faire échouer
le démarrage, pas basculer sur une valeur de développement en production.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuration(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MYCOUNTS_", env_file=".env", extra="ignore")

    database_url: str
    environnement: str = "developpement"


def charger_configuration() -> Configuration:
    return Configuration()  # type: ignore[call-arg]  # pydantic-settings remplit depuis l'env
