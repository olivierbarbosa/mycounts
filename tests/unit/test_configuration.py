"""Les secrets indispensables doivent faire échouer le démarrage, pas une requête."""

from __future__ import annotations

import pytest
from mycounts.config import Configuration
from pydantic import ValidationError


def test_une_cle_hmac_courte_est_refusee_en_production() -> None:
    with pytest.raises(ValidationError, match="MYCOUNTS_CLE_HMAC_AUTH"):
        Configuration(
            database_url="postgresql+psycopg://localhost/mycounts",
            environnement="production",
            cle_hmac_auth="trop-courte",
        )


def test_le_developpement_peut_utiliser_la_cle_locale() -> None:
    configuration = Configuration(
        database_url="postgresql+psycopg://localhost/mycounts",
        environnement="developpement",
    )
    assert configuration.cle_hmac_auth == ""
    assert len(configuration.cle_hmac_effective) >= 32
