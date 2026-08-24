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
    inscriptions_ouvertes: bool = False
    url_publique: str = "http://localhost:5189"
    smtp_hote: str = ""
    smtp_port: int = 465
    smtp_utilisateur: str = ""
    smtp_mot_de_passe: str = ""
    smtp_ssl: bool = True
    smtp_starttls: bool = False
    courriel_expediteur: str = "no-reply@mycounts.app"
    courriel_support: str = "support@mycounts.app"

    @model_validator(mode="after")
    def _secret_de_limitation_requis_en_production(self) -> Configuration:
        """Les empreintes d'IP et d'email ne doivent pas être attaquables par dictionnaire."""
        if self.environnement != "developpement" and len(self.cle_hmac_auth) < 32:
            raise ValueError(
                "MYCOUNTS_CLE_HMAC_AUTH doit contenir au moins 32 caractères."
            )
        if self.smtp_ssl and self.smtp_starttls:
            raise ValueError("SMTP_SSL et SMTP_STARTTLS ne peuvent pas être actifs ensemble.")
        if self.environnement != "developpement" and not self.url_publique.startswith("https://"):
            raise ValueError("MYCOUNTS_URL_PUBLIQUE doit utiliser HTTPS hors développement.")
        return self

    @property
    def cle_hmac_effective(self) -> str:
        """Clé configurée, ou repli local explicitement limité au développement."""
        return self.cle_hmac_auth or _CLE_HMAC_DEVELOPPEMENT

    @property
    def smtp_configure(self) -> bool:
        """Un worker privé peut démarrer sans SMTP, mais il n'invente aucun transport."""
        return bool(
            self.smtp_hote and self.smtp_utilisateur and self.smtp_mot_de_passe
        )


@lru_cache(maxsize=1)
def charger_configuration() -> Configuration:
    return Configuration()  # type: ignore[call-arg]  # pydantic-settings remplit depuis l'env
