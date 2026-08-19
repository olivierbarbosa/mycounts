"""Base déclarative SQLAlchemy."""

from __future__ import annotations

from typing import Final

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Convention de nommage des contraintes. Sans elle, `alembic revision --autogenerate`
# produit des clés étrangères ANONYMES : la migration s'applique, mais son `downgrade`
# appelle `drop_constraint(None, ...)` et échoue. Une migration qui ne sait pas revenir
# en arrière n'est utilisable qu'une fois.
CONVENTION_DE_NOMMAGE: Final = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENTION_DE_NOMMAGE)
