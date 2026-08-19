"""API budget, contre PostgreSQL et l'application réelle."""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from mycounts.repository import budget as depot
from mycounts.repository.base import Principal
from sqlalchemy.orm import Session

from tests.integration.test_api_auth import connecter, creer_compte

AUJOURD_HUI = dt.date.today()


def session_ouverte(client: TestClient, session_bd: Session) -> Principal:
    foyer_id, utilisateur_id = creer_compte(session_bd, "a@essai.fr")
    depot.creer_categories_initiales(session_bd, foyer_id)
    session_bd.commit()
    connecter(client, "a@essai.fr")
    return Principal(utilisateur_id=utilisateur_id, foyer_id=foyer_id)


def creer_compte_api(client: TestClient, nom: str = "Courant") -> str:
    reponse = client.post("/comptes", json={"nom": nom, "prive": True})
    assert reponse.status_code == 201
    return str(reponse.json()["id"])


def test_les_routes_budget_exigent_une_session(client: TestClient) -> None:
    for methode, chemin in [
        ("GET", "/comptes"),
        ("POST", "/comptes"),
        ("GET", "/categories"),
        ("GET", "/operations"),
        ("POST", "/operations"),
        ("GET", "/resume"),
    ]:
        assert client.request(methode, chemin).status_code == 401, f"{methode} {chemin}"


def test_le_foyer_nait_avec_ses_categories(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    noms = [c["nom"] for c in client.get("/categories").json()]
    assert "Courses" in noms
    assert "Salaire" in noms


def test_saisir_une_depense_puis_la_relire(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)

    reponse = client.post(
        "/operations",
        json={
            "compte_id": compte_id,
            "libelle": "Courses",
            "montant_centimes": -4590,
            "date_operation": AUJOURD_HUI.isoformat(),
        },
    )
    assert reponse.status_code == 201
    assert reponse.json()["montant_centimes"] == -4590

    listees = client.get("/operations").json()
    assert [o["libelle"] for o in listees] == ["Courses"]


def test_un_montant_nul_est_refuse(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    reponse = client.post(
        "/operations",
        json={
            "compte_id": compte_id,
            "libelle": "Rien",
            "montant_centimes": 0,
            "date_operation": AUJOURD_HUI.isoformat(),
        },
    )
    assert reponse.status_code == 422


def test_une_paie_negative_est_refusee(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    reponse = client.post(
        "/operations",
        json={
            "compte_id": compte_id,
            "libelle": "Salaire",
            "montant_centimes": -250000,
            "date_operation": AUJOURD_HUI.isoformat(),
            "est_paie": True,
        },
    )
    assert reponse.status_code == 422


def test_un_compte_dun_autre_foyer_est_introuvable(
    client: TestClient, session_bd: Session
) -> None:
    """Un identifiant valide chez quelqu'un d'autre doit être refusé exactement comme un
    identifiant inexistant : la distinction révélerait l'existence du compte."""
    autre_foyer, autre_utilisateur = creer_compte(session_bd, "b@essai.fr", nom_foyer="B")
    autre = Principal(utilisateur_id=autre_utilisateur, foyer_id=autre_foyer)
    compte_etranger = depot.creer_compte(session_bd, autre, nom="Perso B")
    session_bd.commit()

    session_ouverte(client, session_bd)
    reponse = client.post(
        "/operations",
        json={
            "compte_id": str(compte_etranger.id),
            "libelle": "Intrusion",
            "montant_centimes": -100,
            "date_operation": AUJOURD_HUI.isoformat(),
        },
    )
    assert reponse.status_code == 404

    inexistant = client.post(
        "/operations",
        json={
            "compte_id": "00000000-0000-0000-0000-000000000000",
            "libelle": "Intrusion",
            "montant_centimes": -100,
            "date_operation": AUJOURD_HUI.isoformat(),
        },
    )
    assert inexistant.status_code == reponse.status_code
    assert inexistant.json() == reponse.json(), "les deux refus doivent être indiscernables"


def test_le_resume_expose_les_quatre_grandeurs(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    paie = AUJOURD_HUI - dt.timedelta(days=5)

    client.post(
        "/operations",
        json={
            "compte_id": compte_id,
            "libelle": "Salaire",
            "montant_centimes": 250000,
            "date_operation": paie.isoformat(),
            "est_paie": True,
        },
    )
    client.post(
        "/operations",
        json={
            "compte_id": compte_id,
            "libelle": "Courses",
            "montant_centimes": -4590,
            "date_operation": AUJOURD_HUI.isoformat(),
        },
    )

    resume = client.get("/resume").json()
    assert resume["periode"]["debut"] == paie.isoformat(), "la période s'ouvre à la paie"
    assert resume["periode"]["fin_estimee"] is True
    assert resume["solde_reel"] == 250000 - 4590
    assert resume["solde_projete"] == 250000 - 4590
    assert resume["solde_a_confirmer"] == 0
    assert resume["depenses_de_periode"] == -4590, "la paie ne doit pas entrer dans les dépenses"


def test_la_liste_est_bornee_a_la_periode_courante(
    client: TestClient, session_bd: Session
) -> None:
    """Une opération d'avant la paie appartient à la période précédente : elle ne doit pas
    apparaître dans la liste du cycle en cours."""
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    paie = AUJOURD_HUI - dt.timedelta(days=5)

    client.post(
        "/operations",
        json={
            "compte_id": compte_id,
            "libelle": "Salaire",
            "montant_centimes": 250000,
            "date_operation": paie.isoformat(),
            "est_paie": True,
        },
    )
    client.post(
        "/operations",
        json={
            "compte_id": compte_id,
            "libelle": "Cycle précédent",
            "montant_centimes": -1000,
            "date_operation": (paie - dt.timedelta(days=3)).isoformat(),
        },
    )

    libelles_periode = [o["libelle"] for o in client.get("/operations").json()]
    assert "Cycle précédent" not in libelles_periode
    assert "Salaire" in libelles_periode

    toutes = [o["libelle"] for o in client.get("/operations?periode_courante=false").json()]
    assert "Cycle précédent" in toutes, "l'opération existe, elle est seulement hors période"


def test_les_montants_circulent_en_centimes_entiers(
    client: TestClient, session_bd: Session
) -> None:
    """Témoin de frontière : un montant décimal en JSON redeviendrait un flottant côté
    client, et l'invariant du projet s'arrêterait à HTTP."""
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    client.post(
        "/operations",
        json={
            "compte_id": compte_id,
            "libelle": "Courses",
            "montant_centimes": -4590,
            "date_operation": AUJOURD_HUI.isoformat(),
        },
    )
    valeur = client.get("/operations").json()[0]["montant_centimes"]
    assert isinstance(valeur, int)
    assert not isinstance(valeur, float)
