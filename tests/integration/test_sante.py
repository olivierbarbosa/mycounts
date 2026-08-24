"""La santé HTTP mesure PostgreSQL, pas seulement le processus Python."""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from mycounts.models.auth import TentativeConnexion
from mycounts.repository import sante as depot_sante
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


def test_health_confirme_un_aller_retour_postgresql(client: TestClient) -> None:
    reponse = client.get("/health")
    assert reponse.status_code == 200
    assert reponse.json() == {"statut": "ok"}


def test_health_refuse_un_processus_isole_de_sa_base(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def base_coupee(_: object) -> None:
        raise SQLAlchemyError("PostgreSQL hors service")

    monkeypatch.setattr(depot_sante, "verifier_base", base_coupee)

    reponse = client.get("/health")
    assert reponse.status_code == 503
    assert reponse.json()["detail"] == "Base de données indisponible."


def test_health_purge_les_compteurs_de_securite_expires(
    client: TestClient, session_bd: Session
) -> None:
    session_bd.add(
        TentativeConnexion(
            empreinte="a" * 64,
            portee="origine",
            fenetre_debut=dt.datetime.now(dt.UTC) - dt.timedelta(hours=2),
            echecs=1,
        )
    )
    session_bd.commit()

    assert client.get("/health").status_code == 200

    session_bd.expire_all()
    assert session_bd.execute(
        select(func.count()).select_from(TentativeConnexion)
    ).scalar_one() == 0
