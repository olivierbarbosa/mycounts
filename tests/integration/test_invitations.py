"""Entrée dans un foyer par invitation. Aucune inscription publique n'existe."""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from mycounts.domain.securite import empreinte_jeton
from mycounts.repository import auth as depot
from sqlalchemy.orm import Session

from tests.integration.test_api_auth import MOT_DE_PASSE, creer_compte
from tests.integration.test_api_budget import connecter_avec_mfa

NOUVEAU = {
    "courriel": "conjoint@essai.fr",
    "nom_affichage": "Conjoint",
    "mot_de_passe": MOT_DE_PASSE,
}


def obtenir_code(client: TestClient) -> str:
    reponse = client.post("/api/auth/invitations")
    assert reponse.status_code == 201
    return str(reponse.json()["code"])


def test_creer_une_invitation_exige_une_session(client: TestClient) -> None:
    assert client.post("/api/auth/invitations").status_code == 401


def test_le_code_n_est_pas_stocke_en_clair(client: TestClient, session_bd: Session) -> None:
    """Une fuite de la base ne doit pas permettre de rejoindre un foyer."""
    creer_compte(session_bd, "a@essai.fr")
    connecter_avec_mfa(client, session_bd, "a@essai.fr")
    code = obtenir_code(client)

    invitation = depot.invitation_utilisable(
        session_bd, empreinte_code=empreinte_jeton(code), a_l_instant=dt.datetime.now(tz=dt.UTC)
    )
    assert invitation is not None
    assert invitation.empreinte_code != code
    assert code not in invitation.empreinte_code


def test_rejoindre_avec_un_code_valide(client: TestClient, session_bd: Session) -> None:
    foyer_id, _ = creer_compte(session_bd, "a@essai.fr")
    connecter_avec_mfa(client, session_bd, "a@essai.fr")
    code = obtenir_code(client)
    client.post("/api/auth/deconnexion")

    reponse = client.post("/api/auth/rejoindre", json={"code": code, **NOUVEAU})
    assert reponse.status_code == 201
    corps = reponse.json()
    assert corps["courriel"] == "conjoint@essai.fr"
    assert corps["foyer_id"] == str(foyer_id), "le nouveau membre doit rejoindre LE foyer invitant"
    assert client.get("/api/auth/moi").status_code == 200, (
        "l'adhésion ouvre directement une session"
    )


def test_un_code_ne_sert_qu_une_fois(client: TestClient, session_bd: Session) -> None:
    creer_compte(session_bd, "a@essai.fr")
    connecter_avec_mfa(client, session_bd, "a@essai.fr")
    code = obtenir_code(client)
    client.post("/api/auth/deconnexion")

    assert client.post("/api/auth/rejoindre", json={"code": code, **NOUVEAU}).status_code == 201
    client.post("/api/auth/deconnexion")
    seconde = client.post(
        "/api/auth/rejoindre", json={"code": code, "courriel": "tiers@essai.fr",
                                 "nom_affichage": "Tiers", "mot_de_passe": MOT_DE_PASSE}
    )
    assert seconde.status_code == 403


def test_un_code_expire_est_refuse(client: TestClient, session_bd: Session) -> None:
    from mycounts.domain.securite import engendrer_jeton

    foyer_id, utilisateur_id = creer_compte(session_bd, "a@essai.fr")
    code = engendrer_jeton()
    depot.creer_invitation(
        session_bd,
        foyer_id=foyer_id,
        creee_par_id=utilisateur_id,
        empreinte_code=empreinte_jeton(code),
        expire_le=dt.datetime.now(tz=dt.UTC) - dt.timedelta(seconds=1),
    )
    session_bd.commit()

    assert client.post("/api/auth/rejoindre", json={"code": code, **NOUVEAU}).status_code == 403


def test_un_code_inconnu_est_refuse(client: TestClient) -> None:
    reponse = client.post(
        "/api/auth/rejoindre", json={"code": "code-totalement-invente-mais-long", **NOUVEAU}
    )
    assert reponse.status_code == 403


def test_une_adresse_deja_prise_est_refusee(client: TestClient, session_bd: Session) -> None:
    creer_compte(session_bd, "a@essai.fr")
    connecter_avec_mfa(client, session_bd, "a@essai.fr")
    code = obtenir_code(client)
    client.post("/api/auth/deconnexion")

    reponse = client.post(
        "/api/auth/rejoindre",
        json={"code": code, "courriel": "A@Essai.FR", "nom_affichage": "Doublon",
              "mot_de_passe": MOT_DE_PASSE},
    )
    assert reponse.status_code == 409, "la casse ne doit pas permettre de créer un doublon"


def test_un_mot_de_passe_trop_court_est_refuse(client: TestClient, session_bd: Session) -> None:
    creer_compte(session_bd, "a@essai.fr")
    connecter_avec_mfa(client, session_bd, "a@essai.fr")
    code = obtenir_code(client)
    client.post("/api/auth/deconnexion")

    reponse = client.post(
        "/api/auth/rejoindre",
        json={"code": code, "courriel": "b@essai.fr", "nom_affichage": "B",
              "mot_de_passe": "court"},
    )
    assert reponse.status_code == 422
