"""Règles pures de limitation des échecs d'authentification."""

from __future__ import annotations

import datetime as dt

import pytest
from mycounts.domain.limitation_auth import (
    Portee,
    debut_de_fenetre,
    empreinte_hmac,
    maximum_echecs,
    origine_normalisee,
    secondes_avant_reessai,
)


def test_empreinte_hmac_stable_mais_dependante_de_la_cle() -> None:
    valeur = "personne@example.fr"
    premiere = empreinte_hmac(valeur, cle="a" * 32)
    assert premiere == empreinte_hmac(valeur, cle="a" * 32)
    assert premiere != empreinte_hmac(valeur, cle="b" * 32)
    assert valeur not in premiere
    assert len(premiere) == 64


def test_empreinte_refuse_une_cle_vide() -> None:
    with pytest.raises(ValueError, match="vide"):
        empreinte_hmac("valeur", cle="")


def test_fenetre_fixe_de_quinze_minutes_et_retry_after() -> None:
    instant = dt.datetime(2026, 8, 24, 12, 14, 59, 500_000, tzinfo=dt.UTC)
    assert debut_de_fenetre(instant) == dt.datetime(2026, 8, 24, 12, 0, tzinfo=dt.UTC)
    assert secondes_avant_reessai(instant) == 1


def test_un_instant_sans_fuseau_est_refuse() -> None:
    with pytest.raises(ValueError, match="fuseau"):
        debut_de_fenetre(dt.datetime(2026, 8, 24, 12, 0))


def test_limites_distinctes_par_identifiant_et_par_origine() -> None:
    assert maximum_echecs(Portee.COUPLE) == 10
    assert maximum_echecs(Portee.ACTION) == 10
    assert maximum_echecs(Portee.ORIGINE) == 100


def test_une_ipv6_changeante_reste_dans_son_reseau_64() -> None:
    assert origine_normalisee("2001:db8:1234:5678::1") == "2001:db8:1234:5678::/64"
    assert origine_normalisee("2001:db8:1234:5678::abcd") == "2001:db8:1234:5678::/64"
    assert origine_normalisee("192.0.2.42") == "192.0.2.42"
