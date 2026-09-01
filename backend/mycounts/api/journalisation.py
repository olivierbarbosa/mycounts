"""Journalisation applicative : format des lignes et identifiant de requête.

Ce que ce module fait :

- donner un horodatage, un niveau et un nom à chaque ligne que l'application écrit.
  Sans configuration, le journal ``mycounts`` n'avait AUCUN gestionnaire sous uvicorn :
  ses avertissements sortaient par le gestionnaire de dernier recours, sans date, et
  ses ``info`` n'existaient pas ;
- poser sur chaque réponse un en-tête ``X-Mycounts-Requete``, huit caractères, qui
  permet de retrouver dans le journal la ligne d'une erreur qu'un utilisateur rapporte
  avec une capture d'écran ;
- journaliser toute erreur non rattrapée avec cet identifiant, la méthode et le
  CHEMIN — jamais la chaîne de requête, jamais le corps, jamais un cookie. Un chemin
  ne contient qu'un identifiant opaque, pas un montant.

Ce qu'il ne fait pas : envoyer quoi que ce soit hors de la machine. Les 5xx sont lus
dans les journaux Docker par ``infra/surveiller.sh``, qui alerte.
"""

from __future__ import annotations

import logging
import secrets
from collections.abc import Awaitable, Callable
from typing import Final

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_journal = logging.getLogger("mycounts.requetes")

EN_TETE_REQUETE: Final = "X-Mycounts-Requete"
FORMAT: Final = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configurer_le_journal() -> None:
    """Donne un gestionnaire au journal racine s'il n'en a pas.

    Sous pytest, la capture en pose déjà un : on ne le double pas, sinon chaque ligne
    sortirait deux fois. Sous uvicorn, la racine est nue — c'est le cas visé.
    """
    if logging.getLogger().handlers:
        return
    logging.basicConfig(level=logging.INFO, format=FORMAT)


async def identifier_la_requete(
    requete: Request, suite: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Intergiciel HTTP : identifiant sur chaque réponse, ligne de journal sur chaque 5xx."""
    identifiant = secrets.token_hex(4)
    try:
        reponse = await suite(requete)
    except Exception:
        # `exception` emporte la trace. Le corps rendu ne dit rien de la cause : la
        # cause est dans le journal, l'identifiant est le lien entre les deux.
        _journal.exception(
            "Requête %s en échec : %s %s", identifiant, requete.method, requete.url.path
        )
        return JSONResponse(
            {"detail": f"Erreur interne (requête {identifiant})."},
            status_code=500,
            headers={EN_TETE_REQUETE: identifiant},
        )
    reponse.headers[EN_TETE_REQUETE] = identifiant
    if reponse.status_code >= 500:
        _journal.error(
            "Requête %s : %s %s → %s",
            identifiant,
            requete.method,
            requete.url.path,
            reponse.status_code,
        )
    return reponse
