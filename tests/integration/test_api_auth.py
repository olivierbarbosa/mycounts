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
from mycounts.models.auth import TentativeConnexion
from mycounts.repository import auth as depot
from sqlalchemy import select
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
        # Ce helper crée un foyer NEUF : son unique membre en est le propriétaire, comme
        # le fait `creer_premier_compte.py`. Laisser le défaut produirait des foyers sans
        # administrateur, un état que la production ne connaît pas.
        est_proprietaire=True,
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


def test_dix_echecs_bloquent_un_identifiant_sans_le_conserver_en_clair(
    client: TestClient, session_bd: Session
) -> None:
    courriel = "cible@essai.fr"
    creer_compte(session_bd, courriel)

    for _ in range(10):
        assert connecter(client, courriel, "mauvais mot de passe entier").status_code == 401

    limite = connecter(client, courriel)
    assert limite.status_code == 429
    assert int(limite.headers["Retry-After"]) > 0

    session_bd.expire_all()
    empreintes = session_bd.execute(select(TentativeConnexion.empreinte)).scalars().all()
    assert empreintes
    assert all(courriel not in empreinte for empreinte in empreintes)


def test_adresse_connue_et_inconnue_recoivent_la_meme_limitation(
    client: TestClient, session_bd: Session
) -> None:
    creer_compte(session_bd, "connue@essai.fr")

    for courriel in ("connue@essai.fr", "inconnue@essai.fr"):
        for _ in range(10):
            connecter(client, courriel, "mauvais mot de passe entier")

    connue = connecter(client, "connue@essai.fr")
    inconnue = connecter(client, "inconnue@essai.fr")
    assert connue.status_code == inconnue.status_code == 429
    assert connue.json() == inconnue.json()


def test_une_connexion_reussie_efface_les_echecs_de_l_identifiant(
    client: TestClient, session_bd: Session
) -> None:
    courriel = "a@essai.fr"
    creer_compte(session_bd, courriel)
    for _ in range(3):
        connecter(client, courriel, "mauvais mot de passe entier")

    assert connecter(client, courriel).status_code == 200

    session_bd.expire_all()
    restants = session_bd.execute(
        select(TentativeConnexion).where(TentativeConnexion.portee == "couple")
    ).scalars().all()
    assert restants == []


def test_une_origine_ne_peut_pas_verrouiller_le_compte_partout(
    client: TestClient, session_bd: Session
) -> None:
    """Connaître l'adresse ne doit pas suffire à interdire l'accès à sa propriétaire."""
    courriel = "cible@essai.fr"
    creer_compte(session_bd, courriel)
    attaque = TestClient(client.app, client=("192.0.2.10", 50_000))
    victime = TestClient(client.app, client=("198.51.100.20", 50_000))

    for _ in range(10):
        assert connecter(attaque, courriel, "mauvais mot de passe entier").status_code == 401
    assert connecter(attaque, courriel).status_code == 429

    assert connecter(victime, courriel).status_code == 200


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
            reponse = connecter(client, courriel, "mauvais mot de passe entier")
            assert reponse.status_code == 401, "la mesure doit encore traverser Argon2"
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
    ancien_jeton = client.cookies[NOM_COOKIE]
    assert client.post("/api/auth/deconnexion").status_code == 204
    assert client.get("/api/auth/moi").status_code == 401

    rejeu = TestClient(client.app)
    rejeu.cookies.set(NOM_COOKIE, ancien_jeton)
    assert rejeu.get("/api/auth/moi").status_code == 401, (
        "l'ancien cookie doit être révoqué côté serveur, pas seulement effacé du navigateur"
    )


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
