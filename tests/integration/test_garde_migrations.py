"""L'API refuse de démarrer sur une base qui n'est pas à jour.

Sans ce garde-fou, une base en retard laisse l'application démarrer normalement et
échouer à la première requête touchant une colonne absente : une erreur 500 opaque,
très loin de sa cause. Voir ERREURS.md #022.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from mycounts.api.app import BaseNonMigree, verifier_migrations_appliquees
from mycounts.repository.base import moteur
from sqlalchemy import text


@pytest.fixture
def revision_de_la_base() -> Iterator[None]:
    """Rend à la base sa révision d'origine, quoi qu'il arrive dans le test."""
    with moteur().begin() as connexion:
        origine = connexion.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    yield
    with moteur().begin() as connexion:
        connexion.execute(text("UPDATE alembic_version SET version_num = :v"), {"v": origine})


def test_une_base_a_jour_laisse_demarrer() -> None:
    verifier_migrations_appliquees()


def test_une_base_en_retard_empeche_le_demarrage(revision_de_la_base: None) -> None:
    with moteur().begin() as connexion:
        connexion.execute(text("UPDATE alembic_version SET version_num = 'une_revision_depassee'"))

    with pytest.raises(BaseNonMigree) as echec:
        verifier_migrations_appliquees()

    # Le message doit nommer la commande à lancer : c'est ce qui distingue un
    # garde-fou utile d'une panne de plus à diagnostiquer.
    assert "make migrer" in str(echec.value)
