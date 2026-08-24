"""Inscription, vérification et récupération sans conserver les preuves en clair."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from mycounts.config import charger_configuration
from mycounts.domain.securite import empreinte_jeton
from mycounts.models.auth import CourrielSortant, JetonIdentite, Utilisateur
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.integration.test_api_auth import MOT_DE_PASSE


def _ouvrir_les_inscriptions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MYCOUNTS_INSCRIPTIONS_OUVERTES", "true")
    charger_configuration.cache_clear()


def _jeton_du_dernier_courriel(session: Session, *, parametre: str) -> str:
    courriel = session.execute(
        select(CourrielSortant).order_by(CourrielSortant.cree_le.desc()).limit(1)
    ).scalar_one()
    lien = courriel.donnees["lien"]
    return parse_qs(urlparse(lien).query)[parametre][0]


def test_la_beta_fermee_refuse_une_inscription_directe(client: TestClient) -> None:
    reponse = client.post(
        "/api/auth/inscription",
        json={
            "courriel": "nouveau@essai.fr",
            "nom_affichage": "Nouveau",
            "mot_de_passe": MOT_DE_PASSE,
        },
    )
    assert reponse.status_code == 403
    assert "invitation" in reponse.json()["detail"]


def test_inscription_verification_unique_puis_enrolement_mfa_obligatoire(
    client: TestClient, session_bd: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ouvrir_les_inscriptions(monkeypatch)
    try:
        cree = client.post(
            "/api/auth/inscription",
            json={
                "courriel": "Nouveau@Essai.FR",
                "nom_affichage": "Nouveau",
                "mot_de_passe": MOT_DE_PASSE,
            },
        )
        assert cree.status_code == 202, cree.text

        session_bd.expire_all()
        utilisateur = session_bd.execute(select(Utilisateur)).scalar_one()
        assert utilisateur.courriel == "nouveau@essai.fr"
        assert utilisateur.courriel_verifie_le is None
        jeton = _jeton_du_dernier_courriel(session_bd, parametre="verification")
        assert session_bd.execute(
            select(JetonIdentite).where(JetonIdentite.empreinte == empreinte_jeton(jeton))
        ).scalar_one()
        assert jeton not in session_bd.execute(select(JetonIdentite.empreinte)).scalar_one()

        avant = client.post(
            "/api/auth/connexion",
            json={"courriel": "nouveau@essai.fr", "mot_de_passe": MOT_DE_PASSE},
        )
        assert avant.status_code == 403
        assert avant.json()["detail"]["motif"] == "courriel_non_verifie"

        verifie = client.post("/api/auth/verification", json={"jeton": jeton})
        assert verifie.status_code == 200, verifie.text
        assert client.post("/api/auth/verification", json={"jeton": jeton}).status_code == 400

        connecte = client.post(
            "/api/auth/connexion",
            json={"courriel": "nouveau@essai.fr", "mot_de_passe": MOT_DE_PASSE},
        )
        assert connecte.status_code == 200, connecte.text
        assert connecte.json()["enrolement_requis"] is True
        refuse_finance = client.get("/api/comptes")
        assert refuse_finance.status_code == 403
        assert refuse_finance.json()["detail"]["motif"] == "enrolement_second_facteur_requis"
    finally:
        charger_configuration.cache_clear()


def test_recuperation_ne_revele_pas_lexistence_et_le_lien_ne_sert_quune_fois(
    client: TestClient, session_bd: Session
) -> None:
    from tests.integration.test_api_auth import creer_compte

    creer_compte(session_bd, "existant@essai.fr")
    connue = client.post(
        "/api/auth/mot-de-passe-oublie", json={"courriel": "existant@essai.fr"}
    )
    inconnue = client.post(
        "/api/auth/mot-de-passe-oublie", json={"courriel": "absent@essai.fr"}
    )
    assert connue.status_code == inconnue.status_code == 202
    assert connue.json() == inconnue.json()

    session_bd.expire_all()
    jeton = _jeton_du_dernier_courriel(session_bd, parametre="recuperation")
    nouveau = "nouveau secret suffisamment long"
    remplace = client.post(
        "/api/auth/reinitialisation",
        json={"jeton": jeton, "nouveau_mot_de_passe": nouveau},
    )
    assert remplace.status_code == 200, remplace.text
    assert client.post(
        "/api/auth/reinitialisation",
        json={"jeton": jeton, "nouveau_mot_de_passe": "encore un mot de passe valide"},
    ).status_code == 400
    assert client.post(
        "/api/auth/connexion",
        json={"courriel": "existant@essai.fr", "mot_de_passe": nouveau},
    ).status_code == 200
