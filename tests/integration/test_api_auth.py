"""Tests de l'API d'authentification, contre PostgreSQL et l'application réelle."""

from __future__ import annotations

import datetime as dt
import time
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient
from mycounts.api.dependances import NOM_COOKIE
from mycounts.domain.securite import hacher_mot_de_passe, normaliser_courriel
from mycounts.repository import auth as depot
from sqlalchemy.orm import Session

MOT_DE_PASSE = "correct cheval batterie agrafe"


def creer_compte(
    session: Session, courriel: str, *, nom_foyer: str = "Foyer", nom: str = "Membre"
) -> tuple[uuid.UUID, uuid.UUID]:
    foyer = depot.creer_foyer(session, nom_foyer)
    utilisateur = depot.creer_utilisateur(
        session,
        foyer_id=foyer.id,
        courriel=normaliser_courriel(courriel),
        nom_affichage=nom,
        empreinte_mot_de_passe=hacher_mot_de_passe(MOT_DE_PASSE),
    )
    session.commit()
    return foyer.id, utilisateur.id


def connecter(
    client: TestClient, courriel: str, mot_de_passe: str = MOT_DE_PASSE
) -> httpx.Response:
    # TestClient est typé de façon lâche par Starlette ; le cast rend explicite le type
    # réellement renvoyé plutôt que de le taire.
    reponse: httpx.Response = client.post(
        "/api/auth/connexion", json={"courriel": courriel, "mot_de_passe": mot_de_passe}
    )
    return reponse


def test_connexion_reussie(client: TestClient, session_bd: Session) -> None:
    creer_compte(session_bd, "a@essai.fr")
    reponse = connecter(client, "a@essai.fr")
    assert reponse.status_code == 200
    assert reponse.json()["courriel"] == "a@essai.fr"
    assert NOM_COOKIE in reponse.cookies


def test_le_cookie_de_session_est_httponly_et_samesite(
    client: TestClient, session_bd: Session
) -> None:
    """Un cookie lisible par JavaScript serait volé par le premier XSS venu."""
    creer_compte(session_bd, "a@essai.fr")
    entete = connecter(client, "a@essai.fr").headers["set-cookie"].lower()
    assert "httponly" in entete
    assert "samesite=lax" in entete
    assert "path=/" in entete


def test_le_cookie_ne_contient_pas_le_mot_de_passe(client: TestClient, session_bd: Session) -> None:
    creer_compte(session_bd, "a@essai.fr")
    reponse = connecter(client, "a@essai.fr")
    assert MOT_DE_PASSE not in reponse.headers["set-cookie"]


@pytest.mark.parametrize(
    ("courriel", "mot_de_passe"),
    [
        ("a@essai.fr", "mauvais mot de passe entier"),
        ("inconnu@essai.fr", MOT_DE_PASSE),
        ("inconnu@essai.fr", "mauvais mot de passe entier"),
    ],
)
def test_connexion_refusee(
    client: TestClient, session_bd: Session, courriel: str, mot_de_passe: str
) -> None:
    creer_compte(session_bd, "a@essai.fr")
    reponse = connecter(client, courriel, mot_de_passe)
    assert reponse.status_code == 401
    assert NOM_COOKIE not in reponse.cookies


def test_les_deux_motifs_de_refus_sont_indiscernables(
    client: TestClient, session_bd: Session
) -> None:
    """Adresse inconnue et mot de passe faux doivent produire la MÊME réponse.

    Un message différent permettrait d'énumérer les comptes existants du foyer.
    """
    creer_compte(session_bd, "a@essai.fr")
    inconnu = connecter(client, "inconnu@essai.fr")
    faux = connecter(client, "a@essai.fr", "mauvais mot de passe entier")
    assert inconnu.status_code == faux.status_code
    assert inconnu.json() == faux.json()


def test_le_temps_de_reponse_ne_trahit_pas_l_existence_du_compte(
    client: TestClient, session_bd: Session
) -> None:
    """Témoin du leurre Argon2.

    Sans l'empreinte-leurre, une adresse inconnue répondrait sans hacher (~1 ms) alors
    qu'une adresse connue paierait Argon2 (~60 ms) : un rapport de plusieurs dizaines,
    directement observable depuis l'extérieur. La tolérance est large (facteur 4) pour ne
    pas rendre le test instable en CI, tout en restant très loin du rapport qu'aurait une
    implémentation sans leurre.
    """
    creer_compte(session_bd, "a@essai.fr")

    def duree(courriel: str) -> float:
        debut = time.perf_counter()
        for _ in range(3):
            connecter(client, courriel, "mauvais mot de passe entier")
        return time.perf_counter() - debut

    duree(  # tour de chauffe : le premier appel paie les imports et la connexion
        "a@essai.fr"
    )
    connu = duree("a@essai.fr")
    inconnu = duree("inconnu@essai.fr")
    rapport = max(connu, inconnu) / min(connu, inconnu)
    assert rapport < 4, f"écart de temps trop marqué ({rapport:.1f}×) : le leurre ne joue pas"


def test_moi_exige_une_session(client: TestClient) -> None:
    assert client.get("/api/auth/moi").status_code == 401


def test_moi_renvoie_l_utilisateur_connecte(client: TestClient, session_bd: Session) -> None:
    creer_compte(session_bd, "a@essai.fr", nom="Olivier")
    connecter(client, "a@essai.fr")
    reponse = client.get("/api/auth/moi")
    assert reponse.status_code == 200
    assert reponse.json()["nom_affichage"] == "Olivier"


def test_deconnexion_efface_le_cookie(client: TestClient, session_bd: Session) -> None:
    creer_compte(session_bd, "a@essai.fr")
    connecter(client, "a@essai.fr")
    assert client.post("/api/auth/deconnexion").status_code == 204
    assert client.get("/api/auth/moi").status_code == 401


def test_un_jeton_inconnu_est_refuse(client: TestClient) -> None:
    client.cookies.set(NOM_COOKIE, "jeton-inexistant-mais-bien-forme")
    assert client.get("/api/auth/moi").status_code == 401


def test_une_session_expiree_est_refusee(client: TestClient, session_bd: Session) -> None:
    """L'expiration est filtrée en SQL : une session périmée ne remonte jamais."""
    from mycounts.domain.securite import empreinte_jeton, engendrer_jeton

    _, utilisateur_id = creer_compte(session_bd, "a@essai.fr")
    jeton = engendrer_jeton()
    depot.enregistrer_session_web(
        session_bd,
        utilisateur_id=utilisateur_id,
        empreinte=empreinte_jeton(jeton),
        expire_le=dt.datetime.now(tz=dt.UTC) - dt.timedelta(seconds=1),
    )
    session_bd.commit()

    client.cookies.set(NOM_COOKIE, jeton)
    assert client.get("/api/auth/moi").status_code == 401
