"""Second facteur : codes à usage unique et codes de secours.

**Pourquoi une bibliothèque et non trente lignes.** La RFC 6238 tient en peu de code, et
c'est précisément le piège : une implémentation maison qui accepte le bon code passe tous
les tests fonctionnels tout en acceptant aussi ce qu'elle ne devrait pas — fenêtre de
tolérance trop large, comparaison non constante, contre-mesure de rejeu absente. Aucun de
ces défauts ne se voit à l'usage.

**Ce que ce module NE fait pas.** Il ne stocke rien et ne décide de rien : il produit un
secret, vérifie un code, fabrique et compare des codes de secours. Le choix d'exiger ou
non le second facteur appartient à l'API, et l'écriture au repository.
"""

from __future__ import annotations

import datetime as dt
import hmac
import secrets
from typing import Final

import pyotp

from mycounts.domain.securite import hacher_mot_de_passe, verifier_mot_de_passe

NOM_EMETTEUR: Final = "mycounts"

# Une période de tolérance de part et d'autre, soit 90 secondes au total.
#
# Zéro rejetterait un code tapé à cheval sur deux périodes — le cas le plus banal, taper
# six chiffres prend plus de temps qu'il n'en reste souvent. Deux ou plus élargirait la
# fenêtre d'un code intercepté sans rien régler pour l'utilisateur honnête. Un est le
# réglage recommandé par la RFC 6238 elle-même.
FENETRE: Final = 1

NOMBRE_DE_CODES_DE_SECOURS: Final = 10

# Cinq octets, soit dix caractères en base32 : 40 bits d'entropie. Ce n'est pas un secret
# choisi par un humain, donc la longueur suffit — mais ils sont HACHÉS en base malgré
# tout, parce qu'un vol de dump donnerait sinon un accès complet à chaque compte.
_OCTETS_PAR_CODE: Final = 5


def engendrer_secret() -> str:
    """Un secret TOTP neuf, en base32 comme l'exigent les applications d'authentification."""
    return str(pyotp.random_base32())


def uri_denrolement(secret: str, courriel: str) -> str:
    """L'URI `otpauth://` que lit une application d'authentification.

    Le nom du compte y figure en clair : c'est ce qui permet de distinguer deux comptes
    dans la même application. L'émetteur aussi, sans quoi la ligne s'affiche sans étiquette
    et devient impossible à retrouver parmi vingt autres.
    """
    return str(pyotp.TOTP(secret).provisioning_uri(name=courriel, issuer_name=NOM_EMETTEUR))


def compteur_du_code_valide(
    secret: str, code: str, *, instant: dt.datetime | None = None
) -> int | None:
    """Rend le compteur RFC 6238 correspondant, ou `None` si le code est faux.

    `pyotp` compare en temps constant. Une comparaison naïve fuirait, par la durée, le
    nombre de chiffres corrects — assez pour retrouver un code six chiffres en six cents
    essais au lieu d'un million. Rendre le compteur permet à l'appelant de consommer le
    code atomiquement et d'en interdire le rejeu.
    """
    nettoye = code.strip().replace(" ", "")
    if not nettoye.isdigit():
        return None

    maintenant = instant or dt.datetime.now(dt.UTC)
    totp = pyotp.TOTP(secret)
    for decalage in range(-FENETRE, FENETRE + 1):
        candidat = maintenant + dt.timedelta(seconds=decalage * totp.interval)
        if totp.verify(nettoye, for_time=candidat, valid_window=0):
            return int(totp.timecode(candidat))
    return None


def engendrer_codes_de_secours() -> list[str]:
    """Dix codes à usage unique, rendus EN CLAIR — la seule et unique fois.

    L'appelant les affiche puis n'en garde que les empreintes. Les rendre une seconde fois
    demanderait de les stocker en clair, ce qui reviendrait à laisser une porte ouverte à
    côté de celle qu'on vient de fermer.

    Le format `xxxxx-xxxxx` n'est pas décoratif : dix caractères d'affilée se recopient mal
    depuis une feuille de papier, et c'est sur du papier que ces codes finissent.
    """
    codes = []
    for _ in range(NOMBRE_DE_CODES_DE_SECOURS):
        brut = secrets.token_hex(_OCTETS_PAR_CODE).upper()
        codes.append(f"{brut[:5]}-{brut[5:]}")
    return codes


def normaliser_code_de_secours(code: str) -> str:
    """Majuscules, sans espaces ni tirets. Recopié à la main, un code arrive comme il peut.

    Refuser « a1b2c 3d4e5 » parce qu'il a été tapé en minuscules avec une espace serait
    refuser pour une raison qui n'a rien à voir avec la sécurité — et le refus arriverait
    au pire moment, celui où l'on a perdu son téléphone.
    """
    return code.strip().upper().replace("-", "").replace(" ", "")


def hacher_code_de_secours(code: str) -> str:
    """Haché comme un mot de passe.

    Argon2 est ici surdimensionné — quarante bits d'aléa ne se cassent pas par
    dictionnaire — mais réutiliser la fonction du projet évite un second algorithme à
    surveiller, et le coût ne se paie qu'à l'usage d'un code, c'est-à-dire presque jamais.
    """
    return hacher_mot_de_passe(_completer(normaliser_code_de_secours(code)))


def code_de_secours_correspond(empreinte: str, code: str) -> bool:
    return verifier_mot_de_passe(empreinte, _completer(normaliser_code_de_secours(code)))


def _completer(code: str) -> str:
    """Rallonge le code jusqu'à la longueur minimale exigée par `hacher_mot_de_passe`.

    Cette longueur protège un secret CHOISI par un humain ; un code de secours n'en est
    pas un. Le suffixe est constant et connu : il n'ajoute aucune entropie et n'en retire
    aucune. L'alternative — abaisser la borne dans `domain/securite` — l'affaiblirait là où
    elle sert vraiment, pour un besoin qui n'est pas le sien.
    """
    return f"{code}::code-de-secours-mycounts"


def comparer_en_temps_constant(attendu: str, fourni: str) -> bool:
    """Pour les comparaisons de chaînes non hachées, quand il y en a."""
    return hmac.compare_digest(attendu, fourni)
