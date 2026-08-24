"""Limitation des échecs d'authentification sans conserver d'identifiant en clair."""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import ipaddress
from enum import StrEnum
from typing import Final

FENETRE: Final = dt.timedelta(minutes=15)
ECHECS_PAR_COUPLE: Final = 10
ECHECS_PAR_ORIGINE: Final = 100


class Portee(StrEnum):
    COUPLE = "couple"
    ORIGINE = "origine"
    ACTION = "action"


def empreinte_hmac(valeur: str, *, cle: str) -> str:
    """Pseudonymise par HMAC ; la durée de rétention reste donc bornée et documentée."""
    if cle == "":
        raise ValueError("La clé HMAC ne peut pas être vide.")
    return hmac.new(cle.encode(), valeur.encode(), hashlib.sha256).hexdigest()


def origine_normalisee(valeur: str) -> str:
    """Groupe une adresse IPv6 par /64, conserve une IPv4 exacte et tolère les tests."""
    try:
        adresse = ipaddress.ip_address(valeur)
    except ValueError:
        return valeur.strip().lower()
    if isinstance(adresse, ipaddress.IPv6Address):
        return str(ipaddress.ip_network(f"{adresse}/64", strict=False))
    return str(adresse)


def debut_de_fenetre(instant: dt.datetime) -> dt.datetime:
    """Borne UTC de la fenêtre fixe contenant l'instant."""
    if instant.tzinfo is None:
        raise ValueError("L'instant de limitation doit porter un fuseau.")
    secondes = int(FENETRE.total_seconds())
    timestamp = int(instant.timestamp())
    return dt.datetime.fromtimestamp(timestamp - timestamp % secondes, tz=dt.UTC)


def maximum_echecs(portee: Portee) -> int:
    if portee in {Portee.COUPLE, Portee.ACTION}:
        return ECHECS_PAR_COUPLE
    return ECHECS_PAR_ORIGINE


def secondes_avant_reessai(instant: dt.datetime) -> int:
    fin = debut_de_fenetre(instant) + FENETRE
    return max(1, int((fin - instant).total_seconds()) + 1)
