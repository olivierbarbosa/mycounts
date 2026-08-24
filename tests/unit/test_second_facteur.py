"""Vérification du compteur TOTP, nécessaire à l'anti-rejeu."""

from __future__ import annotations

import datetime as dt

import pyotp
from mycounts.domain.second_facteur import FENETRE, compteur_du_code_valide


def test_un_code_valide_rend_son_compteur_exact() -> None:
    secret = pyotp.random_base32()
    instant = dt.datetime(2026, 8, 24, 12, 0, tzinfo=dt.UTC)
    totp = pyotp.TOTP(secret)

    compteur = compteur_du_code_valide(secret, totp.at(instant), instant=instant)

    assert compteur == totp.timecode(instant)


def test_la_fenetre_rend_le_compteur_du_code_pas_celui_du_serveur() -> None:
    """Deux codes tolérés doivent rester deux compteurs consommables distincts."""
    assert FENETRE == 1
    secret = pyotp.random_base32()
    instant = dt.datetime(2026, 8, 24, 12, 0, tzinfo=dt.UTC)
    voisin = instant - dt.timedelta(seconds=30)
    totp = pyotp.TOTP(secret)

    compteur = compteur_du_code_valide(secret, totp.at(voisin), instant=instant)

    assert compteur == totp.timecode(voisin)


def test_un_code_malforme_na_pas_de_compteur() -> None:
    assert compteur_du_code_valide(pyotp.random_base32(), "12-ab") is None
