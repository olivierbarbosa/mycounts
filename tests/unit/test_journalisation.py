"""L'identifiant de requête relie une réponse en erreur à sa ligne de journal."""

from __future__ import annotations

import logging
import re

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from mycounts.api.journalisation import EN_TETE_REQUETE, identifier_la_requete

HEXA_8 = re.compile(r"^[0-9a-f]{8}$")


def _application() -> FastAPI:
    app = FastAPI()
    app.middleware("http")(identifier_la_requete)

    @app.get("/ok")
    def ok() -> dict[str, str]:
        return {"statut": "ok"}

    @app.get("/absent")
    def absent() -> None:
        raise HTTPException(status_code=404, detail="Introuvable.")

    @app.get("/casse")
    def casse() -> None:
        raise RuntimeError("montant=123456 ne doit pas sortir")

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_application(), raise_server_exceptions=False)


def test_chaque_reponse_porte_un_identifiant(client: TestClient) -> None:
    reponse = client.get("/ok")
    assert reponse.status_code == 200
    assert HEXA_8.match(reponse.headers[EN_TETE_REQUETE])


def test_deux_requetes_ont_deux_identifiants(client: TestClient) -> None:
    premier = client.get("/ok").headers[EN_TETE_REQUETE]
    second = client.get("/ok").headers[EN_TETE_REQUETE]
    assert premier != second


def test_une_erreur_non_rattrapee_rend_500_avec_le_meme_identifiant_que_le_journal(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR, logger="mycounts.requetes"):
        reponse = client.get("/casse?secret=oui")
    assert reponse.status_code == 500
    identifiant = reponse.headers[EN_TETE_REQUETE]
    assert identifiant in reponse.json()["detail"]
    ligne = caplog.records[-1]
    assert identifiant in ligne.getMessage()
    assert "/casse" in ligne.getMessage()
    # La chaîne de requête ne sort jamais ; le message de l'exception non plus,
    # sauf dans la trace, qui reste dans le journal et jamais dans la réponse.
    assert "secret" not in ligne.getMessage()
    assert "montant" not in reponse.text


def test_une_erreur_http_ordinaire_ne_journalise_rien(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR, logger="mycounts.requetes"):
        reponse = client.get("/absent")
    assert reponse.status_code == 404
    assert HEXA_8.match(reponse.headers[EN_TETE_REQUETE])
    assert caplog.records == []
