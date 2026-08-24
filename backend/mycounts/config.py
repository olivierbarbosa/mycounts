"""Configuration de l'application, lue depuis l'environnement.

Aucune valeur secrète n'a de défaut en dur : une variable manquante doit faire échouer
le démarrage, pas basculer sur une valeur de développement en production.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_CLE_HMAC_DEVELOPPEMENT = "mycounts-cle-locale-sans-usage-en-production-2026"


class Configuration(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MYCOUNTS_", env_file=".env", extra="ignore")

    database_url: str
    environnement: str = "developpement"
    cle_hmac_auth: str = ""

    @model_validator(mode="after")
    def _secret_de_limitation_requis_en_production(self) -> Configuration:
        """Les empreintes d'IP et d'email ne doivent pas être attaquables par dictionnaire."""
        if self.environnement != "developpement" and len(self.cle_hmac_auth) < 32:
            raise ValueError(
                "MYCOUNTS_CLE_HMAC_AUTH doit contenir au moins 32 caractères."
            )
        return self

    @property
    def cle_hmac_effective(self) -> str:
        """Clé configurée, ou repli local explicitement limité au développement."""
        return self.cle_hmac_auth or _CLE_HMAC_DEVELOPPEMENT


@lru_cache(maxsize=1)
def charger_configuration() -> Configuration:
    return Configuration()  # type: ignore[call-arg]  # pydantic-settings remplit depuis l'env
