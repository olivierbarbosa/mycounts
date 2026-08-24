"""Modification du profil et image de profil.

Le test central est `l'image reçue est réencodée, métadonnées comprises` : une photo de
téléphone transporte la position GPS de l'endroit où elle a été prise, et un avatar est vu
par les autres membres du foyer. Le réencodage efface ces données par omission — rien
n'est recopié — mais rien ne le PROUVE sans une image qui en contient au départ.

Le second qui compte est `changer son mot de passe ferme les autres sessions` : on change
son mot de passe surtout quand quelqu'un d'autre pourrait le connaître, et laisser
l'ancienne session ouverte ailleurs viderait la mesure de son sens.
"""

from __future__ import annotations

import io
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from mycounts.api.dependances import NOM_COOKIE
from mycounts.domain.avatars import COTE, POIDS_MAXIMAL_OCTETS
from mycounts.domain.securite import hacher_mot_de_passe, normaliser_courriel
from mycounts.models.auth import CourrielSortant
from mycounts.repository import auth as depot_auth
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.integration.test_api_auth import MOT_DE_PASSE, connecter, creer_compte
from tests.integration.test_api_budget import connecter_avec_mfa, session_ouverte

COURRIEL = "a@essai.fr"


def image_png(largeur: int = 900, hauteur: int = 600, *, avec_gps: bool = False) -> bytes:
    """Une image de test, éventuellement porteuse de métadonnées comme une vraie photo."""
    tampon = io.BytesIO()
    image = Image.new("RGB", (largeur, hauteur), (30, 120, 200))
    if avec_gps:
        exif = Image.Exif()
        exif[0x0112] = 6  # Orientation : le capteur était tourné.
        exif[0x8825] = {1: "N", 2: (48.0, 51.0, 24.0)}  # Position GPS.
        image.save(tampon, format="JPEG", exif=exif)
    else:
        image.save(tampon, format="PNG")
    return tampon.getvalue()


def envoyer(client: TestClient, donnees: bytes, nom: str = "photo.png"):  # type: ignore[no-untyped-def]
    return client.put("/api/auth/moi/avatar", files={"fichier": (nom, donnees, "image/png")})


def test_renommer_change_le_nom_affiche(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    reponse = client.patch("/api/auth/moi", json={"nom_affichage": "  Olivier B.  "})
    assert reponse.status_code == 200, reponse.text
    # Les espaces de bord sont retirés : ils ne se voient pas et décalent les initiales.
    assert reponse.json()["nom_affichage"] == "Olivier B."
    assert client.get("/api/auth/moi").json()["nom_affichage"] == "Olivier B."


def test_changer_son_mot_de_passe_ferme_les_AUTRES_sessions(
    client: TestClient, session_bd: Session
) -> None:
    """Deux grandeurs, dont une qui doit changer et l'autre non.

    Sans la seconde moitié, un code qui fermerait TOUTES les sessions passerait : l'écran
    renverrait alors vers la connexion juste après avoir annoncé un succès.
    """
    session_ouverte(client, session_bd)

    # Une seconde session pour la même personne, comme un second appareil.
    autre = TestClient(client.app)
    connecter_avec_mfa(autre, session_bd, COURRIEL)
    assert autre.get("/api/auth/moi").status_code == 200

    reponse = client.post(
        "/api/auth/moi/mot-de-passe",
        json={"ancien": MOT_DE_PASSE, "nouveau": "un nouveau mot de passe long"},
    )
    assert reponse.status_code == 204, reponse.text

    # Ce qui DOIT changer : l'autre appareil est déconnecté.
    assert autre.get("/api/auth/moi").status_code == 401
    # Ce qui ne doit PAS changer : celui qui a demandé reste connecté.
    assert client.get("/api/auth/moi").status_code == 200
    # Et le nouveau secret est bien celui qui vaut.
    encore = TestClient(client.app)
    connecter_avec_mfa(encore, session_bd, COURRIEL, "un nouveau mot de passe long")
    assert connecter(TestClient(client.app), COURRIEL, MOT_DE_PASSE).status_code == 401


def test_un_ancien_mot_de_passe_faux_ne_change_rien(
    client: TestClient, session_bd: Session
) -> None:
    """Une session volée ne doit pas permettre d'exclure le propriétaire de son compte."""
    session_ouperte = session_ouverte(client, session_bd)
    assert session_ouperte is not None

    refus = client.post(
        "/api/auth/moi/mot-de-passe",
        json={"ancien": "ce n’est pas le bon", "nouveau": "un nouveau mot de passe long"},
    )
    assert refus.status_code == 400, refus.text
    connecter_avec_mfa(TestClient(client.app), session_bd, COURRIEL, MOT_DE_PASSE)


def test_un_nouveau_mot_de_passe_trop_court_est_refuse(
    client: TestClient, session_bd: Session
) -> None:
    """La borne est celle du DOMAINE, pas une seconde écrite dans le schéma d'API.

    Ce test la mesure à travers la route : si quelqu'un ajoutait un `min_length` dans le
    schéma, il y aurait deux auteurs pour la même règle, et le message changerait sans
    que la règle change.
    """
    session_ouverte(client, session_bd)
    refus = client.post(
        "/api/auth/moi/mot-de-passe", json={"ancien": MOT_DE_PASSE, "nouveau": "court"}
    )
    assert refus.status_code == 400, refus.text
    assert "12 caractères" in refus.json()["detail"]


def test_changer_son_adresse_change_lidentifiant_de_connexion(
    client: TestClient, session_bd: Session
) -> None:
    session_ouverte(client, session_bd)
    reponse = client.post(
        "/api/auth/moi/courriel",
        json={"courriel": "Nouvelle@Essai.FR", "mot_de_passe": MOT_DE_PASSE},
    )
    assert reponse.status_code == 200, reponse.text
    # Normalisée par le domaine : « Nouvelle@Essai.FR » et « nouvelle@essai.fr » sont la
    # même adresse, et deux comptes ne doivent pas pouvoir naître de cette différence.
    assert reponse.json()["courriel"] == "nouvelle@essai.fr"

    non_verifie = connecter(TestClient(client.app), "nouvelle@essai.fr")
    assert non_verifie.status_code == 403
    assert non_verifie.json()["detail"]["motif"] == "courriel_non_verifie"

    session_bd.expire_all()
    courriel = session_bd.execute(select(CourrielSortant)).scalar_one()
    jeton = parse_qs(urlparse(courriel.donnees["lien"]).query)["verification"][0]
    assert client.post("/api/auth/verification", json={"jeton": jeton}).status_code == 200
    connecter_avec_mfa(TestClient(client.app), session_bd, "nouvelle@essai.fr")
    assert connecter(TestClient(client.app), COURRIEL).status_code == 401


def test_une_adresse_deja_prise_est_refusee_sans_le_dire(
    client: TestClient, session_bd: Session
) -> None:
    """Le message reste NEUTRE.

    « Cette adresse existe déjà » permettrait, depuis n'importe quel compte, de savoir qui
    d'autre en a un ici. Le refus doit être clair sur ce qu'il faut faire, muet sur la
    raison.
    """
    alice = session_ouverte(client, session_bd)
    depot_auth.creer_utilisateur(
        session_bd,
        foyer_id=alice.foyer_id,
        courriel=normaliser_courriel("bruno@essai.fr"),
        nom_affichage="Bruno",
        empreinte_mot_de_passe=hacher_mot_de_passe(MOT_DE_PASSE),
        courriel_verifie=True,
    )
    session_bd.commit()

    refus = client.post(
        "/api/auth/moi/courriel",
        json={"courriel": "bruno@essai.fr", "mot_de_passe": MOT_DE_PASSE},
    )
    assert refus.status_code == 409, refus.text
    detail = refus.json()["detail"]
    assert "existe" not in detail.lower() and "déjà" not in detail.lower(), detail
    # Et l'adresse d'origine tient toujours.
    assert client.get("/api/auth/moi").json()["courriel"] == COURRIEL


def test_limage_recue_est_reencodee_metadonnees_comprises(
    client: TestClient, session_bd: Session
) -> None:
    """Le test central. Une photo de téléphone porte la position de son auteur.

    Trois faits mesurés d'un coup, parce qu'ils viennent du même réencodage : le carré
    imposé, le format unique, et surtout l'absence de toute métadonnée. Sans une image qui
    en CONTIENT au départ, l'assertion « il n'y en a pas » serait vraie d'office.
    """
    session_ouverte(client, session_bd)
    assert envoyer(client, image_png(1200, 800, avec_gps=True), "photo.jpg").status_code == 204

    moi = client.get("/api/auth/moi").json()
    assert moi["a_un_avatar"] is True

    servie = client.get(f"/api/auth/utilisateurs/{moi['id']}/avatar")
    assert servie.status_code == 200, servie.text
    assert servie.headers["content-type"] == "image/webp"
    assert "private" in servie.headers["cache-control"]

    rendue = Image.open(io.BytesIO(servie.content))
    assert rendue.size == (COTE, COTE), "l’image doit être ramenée au carré imposé"
    assert rendue.format == "WEBP"
    assert not dict(rendue.getexif()), "des métadonnées ont survécu au réencodage"


def test_un_fichier_qui_nest_pas_une_image_est_refuse(
    client: TestClient, session_bd: Session
) -> None:
    """Un fichier téléversé annonce son type LUI-MÊME.

    Il est ici présenté comme `image/png` et n'en est pas un : seul le décodage peut le
    dire. Sans ce refus, l'application servirait le fichier de n'importe qui sous son
    propre domaine.
    """
    session_ouverte(client, session_bd)
    refus = envoyer(client, b"ceci n'est pas une image, quoi qu'en dise son nom")
    assert refus.status_code == 400, refus.text
    assert client.get("/api/auth/moi").json()["a_un_avatar"] is False


def test_une_image_trop_lourde_est_refusee(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    refus = envoyer(client, b"\x89PNG\r\n\x1a\n" + b"0" * POIDS_MAXIMAL_OCTETS)
    assert refus.status_code == 400, refus.text
    assert "Mo" in refus.json()["detail"]


def test_lavatar_remplace_le_precedent_sans_en_laisser_deux(
    client: TestClient, session_bd: Session
) -> None:
    """La clé primaire est l'identifiant de la personne : la base l'interdit.

    Ce test vaut pour la ROUTE : une implémentation qui insérerait sans remplacer lèverait
    ici, et l'écran afficherait une panne là où l'on voulait simplement changer de photo.
    """
    session_ouverte(client, session_bd)
    assert envoyer(client, image_png(600, 600)).status_code == 204
    assert envoyer(client, image_png(400, 900)).status_code == 204

    moi = client.get("/api/auth/moi").json()
    servie = client.get(f"/api/auth/utilisateurs/{moi['id']}/avatar")
    assert servie.status_code == 200
    assert Image.open(io.BytesIO(servie.content)).size == (COTE, COTE)


def test_retirer_son_avatar_puis_recommencer_dit_quil_ny_en_a_plus(
    client: TestClient, session_bd: Session
) -> None:
    """« Retiré » et « il n'y en avait pas » sont deux réponses différentes."""
    session_ouverte(client, session_bd)
    assert envoyer(client, image_png()).status_code == 204

    assert client.delete("/api/auth/moi/avatar").status_code == 204
    assert client.delete("/api/auth/moi/avatar").status_code == 404
    assert client.get("/api/auth/moi").json()["a_un_avatar"] is False


def test_lavatar_dun_membre_du_foyer_est_visible_pas_celui_dailleurs(
    client: TestClient, session_bd: Session
) -> None:
    """Une image de profil n'est ni publique ni secrète : elle est du foyer.

    Le 404 hors foyer, et non 403 : dire « interdit » confirmerait l'existence du compte à
    qui essaie des identifiants au hasard.
    """
    alice = session_ouverte(client, session_bd)
    assert envoyer(client, image_png()).status_code == 204
    alice_id = client.get("/api/auth/moi").json()["id"]

    # Bruno, dans le MÊME foyer : il voit le portrait d'Alice.
    depot_auth.creer_utilisateur(
        session_bd,
        foyer_id=alice.foyer_id,
        courriel=normaliser_courriel("bruno@essai.fr"),
        nom_affichage="Bruno",
        empreinte_mot_de_passe=hacher_mot_de_passe(MOT_DE_PASSE),
        courriel_verifie=True,
    )
    session_bd.commit()
    bruno = TestClient(client.app)
    connecter_avec_mfa(bruno, session_bd, "bruno@essai.fr")
    assert bruno.get(f"/api/auth/utilisateurs/{alice_id}/avatar").status_code == 200

    # Carole, dans un AUTRE foyer : rien, et pas même l'aveu que le compte existe.
    creer_compte(session_bd, "carole@ailleurs.fr")
    session_bd.commit()
    carole = TestClient(client.app)
    connecter_avec_mfa(carole, session_bd, "carole@ailleurs.fr")
    refus = carole.get(f"/api/auth/utilisateurs/{alice_id}/avatar")
    assert refus.status_code == 404, refus.text


def test_la_liste_des_membres_dit_qui_a_un_avatar(
    client: TestClient, session_bd: Session
) -> None:
    """Sans ce drapeau, l'écran ne peut le savoir qu'en demandant l'image et en recevant
    un 404 : une requête sur deux échouerait par conception."""
    alice = session_ouverte(client, session_bd)
    depot_auth.creer_utilisateur(
        session_bd,
        foyer_id=alice.foyer_id,
        courriel=normaliser_courriel("bruno@essai.fr"),
        nom_affichage="Bruno",
        empreinte_mot_de_passe=hacher_mot_de_passe(MOT_DE_PASSE),
        courriel_verifie=True,
    )
    session_bd.commit()
    assert envoyer(client, image_png()).status_code == 204

    par_nom = {m["nom_affichage"]: m for m in client.get("/api/auth/foyer/membres").json()}
    assert par_nom["Membre"]["a_un_avatar"] is True
    assert par_nom["Bruno"]["a_un_avatar"] is False


def test_les_routes_de_profil_exigent_une_session(client: TestClient) -> None:
    for methode, chemin, corps in [
        ("PATCH", "/api/auth/moi", {"nom_affichage": "X"}),
        ("POST", "/api/auth/moi/mot-de-passe", {"ancien": "a", "nouveau": "b"}),
        ("POST", "/api/auth/moi/courriel", {"courriel": "x@y.fr", "mot_de_passe": "a"}),
        ("DELETE", "/api/auth/moi/avatar", None),
    ]:
        reponse = client.request(methode, chemin, json=corps)
        assert reponse.status_code == 401, f"{methode} {chemin} → {reponse.status_code}"
    assert NOM_COOKIE not in client.cookies
