"""Socle des tests d'intégration : vraie base, vraie application."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from mycounts.api.app import app
from mycounts.repository.base import fabrique_de_sessions, moteur
from sqlalchemy import text
from sqlalchemy.orm import Session

TABLES = ("operation", "categorie", "compte", "session_web", "invitation", "utilisateur", "foyer")


@pytest.fixture(autouse=True)
def base_propre() -> Iterator[None]:
    """Vide les tables avant chaque test.

    TRUNCATE plutôt qu'un rollback de transaction : l'application ouvre ses propres
    sessions et valide ses transactions, exactement comme en production. Un test qui
    encapsulerait tout dans une transaction externe testerait un comportement que la
    production n'a pas.
    """
    try:
        with moteur().begin() as connexion:
            connexion.execute(text(f"truncate {', '.join(TABLES)} restart identity cascade"))
    except Exception as erreur:  # noqa: BLE001 — message actionnable
        message = f"PostgreSQL indisponible ({erreur.__class__.__name__})"
        if os.environ.get("CI"):
            pytest.fail(f"{message} — la CI doit fournir une base, pas ignorer les tests")
        pytest.skip(f"{message} — lancer « make db-haut »")
    yield


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


@pytest.fixture
def session_bd() -> Iterator[Session]:
    session = fabrique_de_sessions()()
    try:
        yield session
    finally:
        session.close()
