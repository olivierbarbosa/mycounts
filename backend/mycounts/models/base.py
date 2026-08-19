"""Base déclarative SQLAlchemy.

Aucune table métier au lot 0 : elles arrivent avec les lots qui les utilisent.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
