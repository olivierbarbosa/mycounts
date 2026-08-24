"""Sondes de disponibilité de la base.

La route de santé n'a aucun périmètre utilisateur, mais sa requête vit quand même dans le
repository : garder un seul endroit autorisé à parler SQL évite qu'une exception
d'infrastructure devienne un précédent pour les routes métier.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def verifier_base(session: Session) -> None:
    """Effectue un aller-retour réel vers PostgreSQL."""
    session.execute(text("select 1")).scalar_one()
