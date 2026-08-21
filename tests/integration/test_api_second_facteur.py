"""Second facteur : enrôlement, connexion, codes de secours.

Le test central est `activer exige un premier code valide` : sans cette preuve, une heure
fausse sur le téléphone ou un QR scanné à moitié verrouillerait le compte — le serveur
croirait l'enrôlement fait, et plus aucun code ne fonctionnerait. C'est le seul défaut de
ce module qu'on ne peut pas réparer depuis l'application.

Ce que ce fichier NE couvre pas : le rendu du QR. Un SVG est une image ; qu'il soit
correct se vérifie en le scannant, pas en comparant des chaînes. L'URI qu'il encode, lui,
est mesuré.
"""

from __future__ import annotations

import pyotp
from fastapi.testclient import TestClient
from mycounts.domain.second_facteur import NOMBRE_DE_CODES_DE_SECOURS
from sqlalchemy.orm import Session

from tests.integration.test_api_auth import MOT_DE_PASSE, connecter
from tests.integration.test_api_budget import session_ouverte

COURRIEL = "a@essai.fr"


def enroler(client: TestClient) -> tuple[str, list[str]]:
    """Parcours complet d'enrôlement. Rend le secret et les codes de secours."""
    propose = client.post("/api/auth/moi/second-facteur/preparer")
    assert propose.status_code == 200, propose.text
    secret = propose.json()["secret"]

    active = client.post(
        "/api/auth/moi/second-facteur/activer", json={"code": pyotp.TOTP(secret).now()}
    )
    assert active.status_code == 200, active.text
    return secret, active.json()["codes_de_secours"]


def test_activer_exige_un_premier_code_valide(client: TestClient, session_bd: Session) -> None:
    """Le test central : la preuve que l'application est bien configurée.

    Sans elle, le serveur croirait l'enrôlement fait et le compte serait perdu — c'est le
    seul défaut de ce module qu'on ne peut pas réparer depuis l'application.
    """
    session_ouverte(client, session_bd)
    client.post("/api/auth/moi/second-facteur/preparer")

    refus = client.post("/api/auth/moi/second-facteur/activer", json={"code": "000000"})
    assert refus.status_code == 400, refus.text
    assert "heure" in refus.json()["detail"], "le message doit dire quoi vérifier"

    # Et le second facteur n'est PAS actif : un enrôlement raté ne verrouille rien.
    assert client.get("/api/auth/moi/second-facteur").json()["actif"] is False
    assert connecter(TestClient(client.app), COURRIEL).status_code == 200


def test_preparer_deux_fois_engendre_un_secret_neuf(
    client: TestClient, session_bd: Session
) -> None:
    """On rappelle cette route quand la première tentative a échoué. Réutiliser le secret
    laisserait la moitié du travail faite avec une application dont on ne sait plus ce
    qu'elle contient."""
    session_ouverte(client, session_bd)
    premier = client.post("/api/auth/moi/second-facteur/preparer").json()["secret"]
    second = client.post("/api/auth/moi/second-facteur/preparer").json()["secret"]
    assert premier != second


def test_une_fois_actif_le_code_est_exige_a_la_connexion(
    client: TestClient, session_bd: Session
) -> None:
    """Les trois réponses possibles, distinctes — c'est le point.

    « Il faut maintenant un code » et « ce code est faux » ne se confondent pas : l'écran
    afficherait sinon « code incorrect » à quelqu'un qui n'en a encore saisi aucun. Le
    motif est machine-lisible pour cette raison.
    """
    session_ouverte(client, session_bd)
    secret, _ = enroler(client)

    neuf = TestClient(client.app)
    sans_code = neuf.post(
        "/api/auth/connexion", json={"courriel": COURRIEL, "mot_de_passe": MOT_DE_PASSE}
    )
    assert sans_code.status_code == 401
    assert sans_code.json()["detail"]["motif"] == "second_facteur_requis"

    faux = neuf.post(
        "/api/auth/connexion",
        json={"courriel": COURRIEL, "mot_de_passe": MOT_DE_PASSE, "code": "000000"},
    )
    assert faux.status_code == 401
    assert faux.json()["detail"]["motif"] == "second_facteur_invalide"

    bon = neuf.post(
        "/api/auth/connexion",
        json={
            "courriel": COURRIEL,
            "mot_de_passe": MOT_DE_PASSE,
            "code": pyotp.TOTP(secret).now(),
        },
    )
    assert bon.status_code == 200, bon.text


def test_un_mot_de_passe_faux_reste_indiscernable_meme_avec_le_second_facteur(
    client: TestClient, session_bd: Session
) -> None:
    """La règle d'origine tient : un mot de passe faux ne doit pas révéler que le compte
    existe, ni qu'il a un second facteur. Le contrôle du mot de passe passe donc AVANT."""
    session_ouverte(client, session_bd)
    enroler(client)

    neuf = TestClient(client.app)
    refus = neuf.post(
        "/api/auth/connexion", json={"courriel": COURRIEL, "mot_de_passe": "ce n’est pas le bon"}
    )
    assert refus.status_code == 401
    assert refus.json()["detail"] == "Identifiants incorrects.", (
        "un mot de passe faux ne doit pas révéler l’existence d’un second facteur"
    )


def test_un_code_de_secours_ouvre_la_session_et_ne_sert_QUUNE_fois(
    client: TestClient, session_bd: Session
) -> None:
    """Le chemin de celui qui a perdu son téléphone, et sa limite.

    Les deux moitiés comptent : un code qui n'ouvrirait rien serait inutile, un code
    rejouable ne serait plus à usage unique — et l'intercepter une fois suffirait à entrer
    indéfiniment.
    """
    session_ouverte(client, session_bd)
    _, codes = enroler(client)
    assert len(codes) == NOMBRE_DE_CODES_DE_SECOURS

    premier = TestClient(client.app)
    ouverture = premier.post(
        "/api/auth/connexion",
        json={"courriel": COURRIEL, "mot_de_passe": MOT_DE_PASSE, "code": codes[0]},
    )
    assert ouverture.status_code == 200, ouverture.text

    second = TestClient(client.app)
    rejeu = second.post(
        "/api/auth/connexion",
        json={"courriel": COURRIEL, "mot_de_passe": MOT_DE_PASSE, "code": codes[0]},
    )
    assert rejeu.status_code == 401, "un code de secours ne sert qu’une fois"

    # Et il en reste neuf, ce que l'écran doit pouvoir dire.
    assert premier.get("/api/auth/moi/second-facteur").json()["codes_de_secours_restants"] == 9


def test_un_code_de_secours_se_tape_comme_on_peut(
    client: TestClient, session_bd: Session
) -> None:
    """Recopié depuis une feuille de papier, un code arrive en minuscules, avec des espaces.

    Le refuser pour cette raison serait refuser au pire moment — celui où l'on a perdu son
    téléphone — et pour un motif qui n'a rien à voir avec la sécurité.
    """
    session_ouverte(client, session_bd)
    _, codes = enroler(client)
    maladroit = codes[0].lower().replace("-", " ")

    neuf = TestClient(client.app)
    reponse = neuf.post(
        "/api/auth/connexion",
        json={"courriel": COURRIEL, "mot_de_passe": MOT_DE_PASSE, "code": maladroit},
    )
    assert reponse.status_code == 200, reponse.text


def test_desactiver_exige_un_code_en_cours(client: TestClient, session_bd: Session) -> None:
    """Une session ouverte ne suffit pas.

    C'est contre l'usage d'une session volée que le second facteur existe : le retirer sans
    preuve de possession annulerait la protection depuis l'endroit même qu'elle protège.
    """
    session_ouverte(client, session_bd)
    secret, _ = enroler(client)

    refus = client.request(
        "DELETE", "/api/auth/moi/second-facteur", json={"code": "000000"}
    )
    assert refus.status_code == 401, refus.text
    assert client.get("/api/auth/moi/second-facteur").json()["actif"] is True

    retrait = client.request(
        "DELETE", "/api/auth/moi/second-facteur", json={"code": pyotp.TOTP(secret).now()}
    )
    assert retrait.status_code == 204, retrait.text
    assert client.get("/api/auth/moi/second-facteur").json()["actif"] is False
    # Et les codes de secours sont partis avec : des portes oubliées ne doivent pas rester.
    assert client.get("/api/auth/moi/second-facteur").json()["codes_de_secours_restants"] == 0


def test_preparer_est_refuse_quand_le_facteur_est_deja_actif(
    client: TestClient, session_bd: Session
) -> None:
    """Régénérer un secret depuis une session ouverte permettrait de remplacer le facteur
    sans posséder l'ancien, ce qui le viderait de son sens."""
    session_ouverte(client, session_bd)
    enroler(client)
    refus = client.post("/api/auth/moi/second-facteur/preparer")
    assert refus.status_code == 409, refus.text


def test_lenrolement_rend_de_quoi_configurer_sans_camera(
    client: TestClient, session_bd: Session
) -> None:
    """Le secret en clair ET l'URI : une application sans caméra ne peut rien scanner, et
    refuser la saisie manuelle exclurait l'ordinateur de bureau."""
    session_ouverte(client, session_bd)
    propose = client.post("/api/auth/moi/second-facteur/preparer").json()

    assert propose["secret"]
    assert propose["uri"].startswith("otpauth://totp/")
    assert "mycounts" in propose["uri"], "l’émetteur doit figurer, sinon la ligne est anonyme"
    assert COURRIEL.replace("@", "%40") in propose["uri"] or COURRIEL in propose["uri"]
    assert propose["qr_svg"].lstrip().startswith("<?xml") or "<svg" in propose["qr_svg"]
