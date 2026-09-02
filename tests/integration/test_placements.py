"""Placements : hors quotidien, hors réserve, solde par compte intact.

Le test central est `la réserve des enveloppes ignore un PEA` : c'est la règle du lot
V1-FIN-A1. Un PEA compté dans la réserve promettait aux enveloppes de l'argent qu'on ne
peut reprendre qu'en vendant, peut-être à perte. Le témoin de chaque test est un LIVRET,
qui doit continuer à compter : un code qui ignorerait toute l'épargne passerait sinon.

La migration est mesurée sur de vraies lignes, aller et retour : une migration qu'on n'a
jamais fait redescendre n'est pas réversible, elle est supposée l'être.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from mycounts.domain.comptes import TypeCompte
from mycounts.models.budget import Compte
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.integration.test_api_budget import session_ouverte
from tests.integration.test_api_enveloppes import creer_compte

RACINE = Path(__file__).resolve().parents[2]


def test_la_reserve_des_enveloppes_ignore_un_pea(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    creer_compte(client, "LEP", "lep", ouverture=200_000)
    avant = client.get("/api/enveloppes").json()["epargne_totale_centimes"]

    creer_compte(client, "PEA", "pea", ouverture=900_000)
    apres = client.get("/api/enveloppes").json()["epargne_totale_centimes"]

    assert avant == 200_000, "le LEP reste une épargne disponible"
    assert apres == 200_000, "le PEA n'entre pas dans ce que les enveloppes découpent"


def test_le_quotidien_ignore_un_placement(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    creer_compte(client, "Courant", "compte_courant", ouverture=100_000)
    creer_compte(client, "Assurance vie", "assurance_vie", ouverture=700_000)

    resume = client.get("/api/resume").json()
    assert resume["solde_reel"] == 100_000
    assert resume["solde_projete"] == 100_000


def test_le_solde_par_compte_dun_placement_est_intact(
    client: TestClient, session_bd: Session
) -> None:
    """Sortir un compte des totaux ne doit pas le vider : il garde son solde, ses
    opérations, et se lit toujours compte par compte."""
    session_ouverte(client, session_bd)
    per = creer_compte(client, "PER", "per", ouverture=45_000)

    soldes = {s["compte_id"]: s["solde_centimes"] for s in client.get("/api/comptes/soldes").json()}
    assert soldes[per] == 45_000
    detail = client.get(f"/api/epargne/{per}")
    assert detail.status_code == 200, detail.text


def test_la_page_epargne_rend_les_placements_a_part(
    client: TestClient, session_bd: Session
) -> None:
    """Deux totaux, jamais additionnés : l'un dit ce qu'on peut reprendre demain, l'autre
    ce qu'on a placé."""
    session_ouverte(client, session_bd)
    creer_compte(client, "Livret A", "livret_a", ouverture=300_000)
    creer_compte(client, "PEE", "pee", ouverture=120_000)

    epargne = client.get("/api/epargne").json()
    assert epargne["total_centimes"] == 300_000
    assert [c["nom"] for c in epargne["comptes"]] == ["Livret A"]
    assert [c["nom"] for c in epargne["placements"]] == ["PEE"]
    assert epargne["total_placements_centimes"] == 120_000


def test_la_migration_reclasse_par_produit_et_revient_en_arriere(
    client: TestClient, session_bd: Session
) -> None:
    """Le mapping est explicite, par clé de produit, et le retour arrière remet chaque
    compte là où l'ancien catalogue le lisait — sans toucher aux livrets ni au courant."""
    session_ouverte(client, session_bd)
    pea = creer_compte(client, "PEA", "pea", ouverture=10_000)
    pee = creer_compte(client, "PEE", "pee")
    lep = creer_compte(client, "LEP", "lep")
    courant = creer_compte(client, "Courant", "compte_courant")
    session_bd.close()

    configuration = Config(str(RACINE / "alembic.ini"))

    def etat() -> dict[str, tuple[str, str]]:
        with Session(session_bd.get_bind()) as lecture:
            return {
                str(c.id): (str(c.type_compte), c.produit)
                for c in lecture.execute(select(Compte)).scalars()
            }

    command.downgrade(configuration, "-1")
    try:
        avant = etat()
        assert avant[pea] == (TypeCompte.EPARGNE, "pea"), "l'ancien catalogue : PEA = épargne"
        assert avant[pee] == (TypeCompte.EPARGNE, "autre_epargne"), "produit inconnu avant : Autre"
        assert avant[lep] == (TypeCompte.EPARGNE, "lep")
        assert avant[courant] == (TypeCompte.COURANT, "compte_courant")
    finally:
        command.upgrade(configuration, "head")

    apres = etat()
    assert apres[pea] == (TypeCompte.PLACEMENT, "pea")
    assert apres[lep] == (TypeCompte.EPARGNE, "lep")
    assert apres[courant] == (TypeCompte.COURANT, "compte_courant")
    soldes = {s["compte_id"]: s["solde_centimes"] for s in client.get("/api/comptes/soldes").json()}
    assert soldes[pea] == 10_000, "le solde n'a pas bougé d'un centime"
