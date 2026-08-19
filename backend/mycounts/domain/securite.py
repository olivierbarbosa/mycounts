"""Primitives de sécurité : mots de passe, jetons, codes d'invitation.

Auteur **unique** de ces règles. Recopier un hachage ou une durée d'expiration ailleurs,
c'est garantir qu'un jour l'une des deux copies utilisera des paramètres plus faibles
sans que personne ne le remarque.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import secrets
from typing import Final

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Paramètres Argon2id. Volontairement au-dessus des minimas OWASP (19 Mio / 2 passes) :
# cette application ne connaît qu'une poignée de connexions par jour, le coût CPU est
# sans importance ici alors que la résistance au cassage hors ligne, elle, compte.
_HACHEUR: Final = PasswordHasher(time_cost=3, memory_cost=64 * 1024, parallelism=2)

LONGUEUR_MINIMALE_MOT_DE_PASSE: Final = 12
"""12 caractères, sans exigence de composition.

Les règles de composition (« une majuscule, un chiffre, un symbole ») produisent des mots
de passe plus courts et plus prévisibles ; la longueur est le seul facteur qui compte
vraiment. Le choix est écrit ici pour qu'il ne se rediscute pas à chaque écran.
"""

DUREE_SESSION: Final = dt.timedelta(days=30)
DUREE_INVITATION: Final = dt.timedelta(days=7)

_OCTETS_JETON: Final = 32  # 256 bits


class MotDePasseTropCourt(ValueError):
    """Mot de passe en dessous de la longueur minimale."""


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    if len(mot_de_passe) < LONGUEUR_MINIMALE_MOT_DE_PASSE:
        raise MotDePasseTropCourt(
            f"Le mot de passe doit faire au moins {LONGUEUR_MINIMALE_MOT_DE_PASSE} caractères."
        )
    return _HACHEUR.hash(mot_de_passe)


def verifier_mot_de_passe(empreinte: str, mot_de_passe: str) -> bool:
    """Vérifie un mot de passe. Ne lève jamais : renvoie False sur toute anomalie.

    Une empreinte corrompue ou vide doit refuser l'accès, pas faire remonter une erreur
    500 qui révélerait au passage que le compte existe.
    """
    try:
        return _HACHEUR.verify(empreinte, mot_de_passe)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def empreinte_a_renouveler(empreinte: str) -> bool:
    """Indique si l'empreinte a été produite avec des paramètres désormais plus faibles."""
    try:
        return _HACHEUR.check_needs_rehash(empreinte)
    except InvalidHashError:
        return True


def engendrer_jeton() -> str:
    """Jeton opaque de 256 bits, en base64 URL."""
    return secrets.token_urlsafe(_OCTETS_JETON)


def empreinte_jeton(jeton: str) -> str:
    """Empreinte SHA-256 d'un jeton.

    SHA-256 suffit et Argon2 serait ici une erreur de raisonnement : un hachage lent
    protège un secret CHOISI par un humain contre l'attaque par dictionnaire. Un jeton de
    256 bits aléatoires n'a pas de dictionnaire. Le ralentir ne ferait que ralentir chaque
    requête authentifiée.
    """
    return hashlib.sha256(jeton.encode("utf-8")).hexdigest()


def jetons_equivalents(attendu: str, fourni: str) -> bool:
    """Comparaison à temps constant, pour ne pas fuiter par la durée de la comparaison."""
    return hmac.compare_digest(attendu, fourni)


def normaliser_courriel(courriel: str) -> str:
    """Forme canonique d'une adresse : sans espaces, en minuscules.

    Sans cette normalisation, « A@b.fr » et « a@b.fr » créeraient deux comptes que la
    contrainte d'unicité SQL ne verrait pas comme un doublon.
    """
    return courriel.strip().lower()


def maintenant() -> dt.datetime:
    """Instant courant en UTC.

    Les horodatages techniques (création, expiration) sont en UTC ; seules les dates
    civiles d'opération relèvent d'Europe/Paris — voir domain/calendrier.py.
    """
    return dt.datetime.now(tz=dt.UTC)


def expiration_session(depuis: dt.datetime | None = None) -> dt.datetime:
    return (depuis or maintenant()) + DUREE_SESSION


def expiration_invitation(depuis: dt.datetime | None = None) -> dt.datetime:
    return (depuis or maintenant()) + DUREE_INVITATION


def est_expire(echeance: dt.datetime, a_l_instant: dt.datetime | None = None) -> bool:
    """Vrai si l'échéance est atteinte ou dépassée.

    Comparaison inclusive : une session dont l'expiration vaut exactement l'instant
    courant est expirée. Une borne « strictement après » laisserait passer une requête à
    la milliseconde près, et ce genre de cas ne se reproduit jamais quand on le cherche.
    """
    if echeance.tzinfo is None:
        raise ValueError("Une échéance sans fuseau ne peut pas être comparée.")
    return echeance <= (a_l_instant or maintenant())
