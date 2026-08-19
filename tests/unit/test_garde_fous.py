"""Témoins des garde-fous.

Un garde-fou qui n'a jamais rougi ne prouve rien. Ces tests vérifient que chacun détecte
bien la faute qu'il prétend détecter — et, tout aussi important, qu'il ne se déclenche
PAS sur le cas voisin légitime. Sans le second volet, un garde-fou qui répondrait
« coupable » à tout passerait pour efficace.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import verifier_pas_de_float, verifier_scope_repository, verifier_secrets
from scripts.verifier_donnees_bancaires import iban_valide, luhn_valide

# Aucun IBAN ni PAN valide n'est écrit en dur ici : le garde-fou n°1 analyse TOUT le
# dépôt, tests compris, et se déclencherait sur ses propres cas. Les valeurs valides sont
# donc calculées à la volée. Exempter ce fichier aurait ouvert un trou par lequel
# n'importe quelle donnée réelle pourrait passer.


def iban_avec_checksum_correct(pays: str, bban: str) -> str:
    """Construit un IBAN dont le mod-97 est valide, sans en écrire un dans le dépôt."""
    reordonne = bban + pays + "00"
    reste = int("".join(str(int(c, 36)) for c in reordonne)) % 97
    return f"{pays}{98 - reste:02d}{bban}"


def carte_avec_luhn_correct(quinze_chiffres: str) -> str:
    total = 0
    for position, caractere in enumerate(reversed(quinze_chiffres)):
        chiffre = int(caractere)
        if position % 2 == 0:  # position paire une fois le contrôle ajouté
            chiffre *= 2
            if chiffre > 9:
                chiffre -= 9
        total += chiffre
    return quinze_chiffres + str((10 - total % 10) % 10)


@pytest.mark.parametrize(
    ("pays", "bban"),
    [("FR", "20041010050500013M026"), ("DE", "370400440532013000"), ("GB", "WEST12345698765432")],
)
def test_iban_valide_detecte(pays: str, bban: str) -> None:
    assert iban_valide(iban_avec_checksum_correct(pays, bban))


@pytest.mark.parametrize(
    "iban",
    [
        "FR0000000000000000000000000",  # checksum délibérément faux : une fixture
        "XX00",
        "PASUNIBAN",
    ],
)
def test_iban_invalide_ignore(iban: str) -> None:
    """Le contrôle doit laisser passer une fixture au checksum faux.

    C'est ce volet qui rend le garde-fou utilisable : sans lui, écrire un test avec un
    numéro de compte fictif ferait échouer la CI et le garde-fou finirait désactivé.
    """
    assert not iban_valide(iban)


def test_iban_un_chiffre_modifie_est_rejete() -> None:
    """Un IBAN valide dont on change un chiffre ne doit plus passer."""
    valide = iban_avec_checksum_correct("FR", "20041010050500013M026")
    altere = valide[:-1] + ("7" if valide[-1] != "7" else "8")
    assert iban_valide(valide)
    assert not iban_valide(altere)


@pytest.mark.parametrize("base", ["453957876362148", "542523343010990"])
def test_carte_luhn_detectee(base: str) -> None:
    assert luhn_valide(carte_avec_luhn_correct(base))


def test_carte_luhn_espacee_detectee() -> None:
    numero = carte_avec_luhn_correct("453957876362148")
    espace = " ".join(numero[i : i + 4] for i in range(0, len(numero), 4))
    assert luhn_valide(espace)


@pytest.mark.parametrize(
    "carte",
    [
        "0000000000000000",  # remplissage
        "123456789",  # trop court
        "1234567890123456789012",  # trop long
    ],
)
def test_non_carte_ignoree(carte: str) -> None:
    assert not luhn_valide(carte)


def test_carte_avec_dernier_chiffre_modifie_est_rejetee() -> None:
    numero = carte_avec_luhn_correct("453957876362148")
    altere = numero[:-1] + str((int(numero[-1]) + 1) % 10)
    assert luhn_valide(numero)
    assert not luhn_valide(altere)


def test_temoin_float_dans_le_domaine(tmp_path: Path) -> None:
    fautif = tmp_path / "fautif.py"
    fautif.write_text("TAUX = 0.2\ndef f(x: float) -> float:\n    return float(x) * 100\n")
    trouvailles = verifier_pas_de_float.infractions(fautif)
    assert trouvailles, "le garde-fou n'a pas vu un flottant : il ne protège rien"
    assert len(trouvailles) >= 4  # le littéral + les trois usages du nom « float »


def test_temoin_float_faux_positif(tmp_path: Path) -> None:
    """Du code entier légitime ne doit pas déclencher le garde-fou."""
    correct = tmp_path / "correct.py"
    correct.write_text("def f(centimes: int) -> int:\n    return centimes * 100\n")
    assert verifier_pas_de_float.infractions(correct) == []


def test_temoin_requete_hors_repository(tmp_path: Path) -> None:
    fautif = tmp_path / "route.py"
    fautif.write_text("def lire(session):\n    return session.execute(select(Operation))\n")
    trouvailles = verifier_scope_repository.infractions(fautif)
    assert trouvailles, "le garde-fou n'a pas vu une requête hors repository"
    assert any("select" in t for t in trouvailles)
    assert any("execute" in t for t in trouvailles)


def test_temoin_requete_hors_repository_faux_positif(tmp_path: Path) -> None:
    correct = tmp_path / "service.py"
    correct.write_text("from mycounts.repository import lire_operations\n\n"
                       "def total(principal):\n    return sum(lire_operations(principal))\n")
    assert verifier_scope_repository.infractions(correct) == []


# --- Garde-fou n°2 : secrets ------------------------------------------------------
#
# Comme pour les IBAN, aucun jeton d'allure réelle n'est écrit en dur : il serait détecté
# par le garde-fou lui-même. Les valeurs sont assemblées à l'exécution.


@pytest.mark.parametrize(
    ("prefixe", "corps", "libelle"),
    [
        ("sk-", "A" * 32, "clé secrète"),
        ("ghp_", "B" * 36, "jeton GitHub"),
        ("xoxb-", "1234567890-abcdefghij", "jeton Slack"),
        ("AKIA", "ABCDEFGHIJKLMNOP", "identifiant AWS"),
    ],
)
def test_temoin_jeton_detecte(prefixe: str, corps: str, libelle: str) -> None:
    ligne = f'CLE = "{prefixe}{corps}"'
    assert verifier_secrets.libelles_de_ligne(ligne), f"{libelle} non détecté"


def test_temoin_mot_de_passe_en_dur_detecte() -> None:
    # Assemblé à l'exécution : écrit en un seul morceau, ce cas ferait rougir le
    # garde-fou n°2 sur ce fichier même.
    v = "Zx9kLm2Qw7pR4tY"  # nom court volontaire : « {v} » fait moins de 8 caractères,
    assert verifier_secrets.libelles_de_ligne(f'password = "{v}"')  # donc la source ici
    # ne constitue pas elle-même un secret affecté en dur.


def test_temoin_cle_privee_detectee() -> None:
    entete = "-----BEGIN " + "RSA PRIVATE KEY-----"
    assert verifier_secrets.libelles_de_ligne(entete)


@pytest.mark.parametrize(
    "ligne",
    [
        'password = "changeme"',
        'api_key = "votre_cle_ici"',
        'token = "<votre-jeton>"',
        'secret = "${SECRET_DEPUIS_ENV}"',
        "def lire_secret() -> str: ...",
    ],
)
def test_faux_positifs_ignores(ligne: str) -> None:
    """Sans ce volet, le garde-fou crierait sur la documentation et finirait désactivé."""
    assert verifier_secrets.libelles_de_ligne(ligne) == []


def test_url_locale_toleree() -> None:
    """`.env.example` doit pouvoir montrer une URL de développement utilisable."""
    ligne = "MYCOUNTS_DATABASE_URL=postgresql+psycopg://mycounts:mycounts@localhost:5434/mycounts"
    assert verifier_secrets.libelles_de_ligne(ligne) == []


@pytest.mark.parametrize("hote", ["db.prod.demo.net", "10.0.0.4", "vps-1234.ovh.net"])
def test_url_distante_avec_identifiants_detectee(hote: str) -> None:
    """C'était un angle mort : une URL de prod avec mot de passe passait inaperçue."""
    motdepasse = "Zx9kLm2Qw7pR"
    # « :// » est coupé pour que cette ligne source ne soit pas elle-même une URL à
    # identifiants. Aucun fichier n'est exempté du garde-fou n°2, pas même celui-ci :
    # une exemption serait exactement le trou par lequel un vrai secret passerait.
    prefixe = "postgresql+psycopg:" + "//"
    ligne = f"DATABASE_URL={prefixe}mycounts:{motdepasse}@{hote}:5432/mycounts"
    assert verifier_secrets.libelles_de_ligne(ligne)


def test_le_mot_exemple_ne_desarme_pas_la_detection_de_jeton() -> None:
    """Régression : « exemple » sur la ligne désarmait toute la détection.

    Un jeton reste un jeton, quel que soit le commentaire qui l'entoure.
    """
    jeton = "ghp_" + "C" * 36
    assert verifier_secrets.libelles_de_ligne(f"# exemple de configuration\nCLE = {jeton}")
