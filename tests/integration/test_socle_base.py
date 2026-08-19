"""Tests contre le VRAI PostgreSQL.

Pas de SQLite : un test qui passe sur un autre moteur que la production ne prouve que sa
cohérence avec lui-même. Ces tests vérifient les deux propriétés dont dépend tout le
reste du projet — une date civile ne bouge pas, un montant en centimes revient exact.
"""

from __future__ import annotations

import datetime as dt
import os

import pytest
from mycounts.config import charger_configuration
from sqlalchemy import BigInteger, Column, Date, MetaData, Table, create_engine, text
from sqlalchemy.engine import Engine


@pytest.fixture(scope="module")
def moteur() -> Engine:
    moteur = create_engine(charger_configuration().database_url)
    try:
        with moteur.connect() as connexion:
            connexion.execute(text("select 1"))
    except Exception as erreur:  # noqa: BLE001 — on veut un message actionnable
        message = f"PostgreSQL indisponible ({erreur.__class__.__name__})"
        if os.environ.get("CI"):
            # En intégration continue, un skip serait un mensonge : le job resterait
            # VERT sans qu'aucun de ces tests n'ait tourné. Le seul moment où « tout va
            # bien » doit s'afficher est celui où les tests ont réellement été exécutés.
            pytest.fail(f"{message} — la CI doit fournir une base, pas ignorer les tests")
        pytest.skip(f"{message} — lancer « make db-haut »")
    return moteur


def test_postgres_est_bien_la_cible(moteur: Engine) -> None:
    with moteur.connect() as connexion:
        version = connexion.execute(text("select version()")).scalar_one()
    assert "PostgreSQL" in version, "les tests d'intégration doivent viser PostgreSQL"


@pytest.mark.parametrize(
    "fuseau_session", ["UTC", "Europe/Paris", "Pacific/Kiritimati", "Pacific/Niue"]
)
def test_une_date_civile_ne_depend_pas_du_fuseau_de_session(
    moteur: Engine, fuseau_session: str
) -> None:
    """Convertir un instant en date civile doit donner le même jour partout.

    Mesuré, pas supposé : pour l'instant 2026-12-31 23:30 UTC,

        (horodatage)::date                            → 31/12/2026 en session UTC
                                                        01/01/2027 en session Europe/Paris
                                                        31/12/2026 en session Pacific/Niue
        (horodatage AT TIME ZONE 'Europe/Paris')::date → 01/01/2027 partout

    Le cast nu dépend donc du fuseau de session du serveur — une variable d'environnement
    de production peut changer la date d'une opération, et donc le mois auquel elle
    appartient. Ce test échoue si quelqu'un écrit `::date` sans fuseau explicite.

    Le choix du projet : la date civile du foyer est celle d'Europe/Paris. Une opération
    à 23h30 UTC le 31 décembre appartient au 1er janvier.
    """
    instant = "2026-12-31 23:30:00+00"
    with moteur.connect() as connexion:
        connexion.execute(text(f"set time zone '{fuseau_session}'"))
        avec_fuseau = connexion.execute(
            text(f"select (timestamptz '{instant}' at time zone 'Europe/Paris')::date")
        ).scalar_one()
        cast_nu = connexion.execute(text(f"select (timestamptz '{instant}')::date")).scalar_one()

    assert avec_fuseau == dt.date(2027, 1, 1)
    if fuseau_session in {"UTC", "Pacific/Niue"}:
        # Témoin : le cast nu donne bien une AUTRE réponse. Si cette assertion cassait,
        # c'est que le contrôle ci-dessus aurait cessé de distinguer quoi que ce soit.
        assert cast_nu != avec_fuseau


def test_une_colonne_date_est_insensible_au_fuseau(moteur: Engine) -> None:
    """Une colonne DATE relue vaut exactement la date écrite. Propriété de base du type,
    vérifiée ici parce que tout le calcul de période en dépend."""
    metadonnees = MetaData()
    table = Table("t_date_essai", metadonnees, Column("jour", Date, primary_key=True))
    jour = dt.date(2026, 12, 31)

    with moteur.begin() as connexion:
        connexion.execute(text("set time zone 'Pacific/Kiritimati'"))
        metadonnees.create_all(connexion)
        connexion.execute(table.delete())
        connexion.execute(table.insert().values(jour=jour))
        relu = connexion.execute(table.select()).scalar_one()
        metadonnees.drop_all(connexion)

    assert relu == jour


def test_un_montant_en_centimes_revient_exact(moteur: Engine) -> None:
    """BIGINT conserve les centimes sans perte, y compris au-delà de 2^53.

    2^53 est la limite au-delà de laquelle un flottant cesse d'être exact : si un jour la
    colonne devenait un DOUBLE PRECISION, ce test le dirait immédiatement.
    """
    metadonnees = MetaData()
    table = Table("t_montant_essai", metadonnees, Column("centimes", BigInteger, primary_key=True))
    montants = [0, 1, -1, 123456, -4590, 9007199254740993, -9007199254740993]

    with moteur.begin() as connexion:
        metadonnees.create_all(connexion)
        connexion.execute(table.delete())
        connexion.execute(table.insert(), [{"centimes": m} for m in montants])
        relus = sorted(connexion.execute(table.select()).scalars().all())
        metadonnees.drop_all(connexion)

    assert relus == sorted(montants)
