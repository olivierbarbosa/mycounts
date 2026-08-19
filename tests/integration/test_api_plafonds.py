"""API des plafonds, contre PostgreSQL et l'application réelle."""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from mycounts.repository.base import Principal
from sqlalchemy.orm import Session

from tests.integration.test_api_budget import creer_compte_api, session_ouverte

AUJOURD_HUI = dt.date.today()


def creer_categorie(client: TestClient, nom: str = "Courses") -> str:
    reponse = client.post(
        "/api/categories", json={"nom": nom, "nature": "depense", "teinte": "vert"}
    )
    assert reponse.status_code == 201, reponse.text
    return str(reponse.json()["id"])


def depenser(client: TestClient, compte_id: str, categorie_id: str, centimes: int) -> None:
    reponse = client.post(
        "/api/operations",
        json={
            "compte_id": compte_id,
            "libelle": "Dépense",
            "montant_centimes": centimes,
            "date_operation": AUJOURD_HUI.isoformat(),
            "categorie_id": categorie_id,
        },
    )
    assert reponse.status_code == 201, reponse.text


def test_les_routes_plafonds_exigent_une_session(client: TestClient) -> None:
    for methode, chemin in [("GET", "/api/plafonds"), ("PUT", "/api/plafonds")]:
        assert client.request(methode, chemin).status_code == 401, f"{methode} {chemin}"


def test_definir_un_plafond_puis_le_relire(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    categorie_id = creer_categorie(client)

    reponse = client.put(
        "/api/plafonds", json={"categorie_id": categorie_id, "montant_centimes": 40000}
    )
    assert reponse.status_code == 200
    plafonds = reponse.json()
    assert len(plafonds) == 1
    assert plafonds[0]["limite_centimes"] == 40000
    assert plafonds[0]["consomme_centimes"] == 0
    assert plafonds[0]["categorie_nom"] == "Courses"


def test_definir_deux_fois_met_a_jour_sans_dupliquer(
    client: TestClient, session_bd: Session
) -> None:
    """PUT idempotent : rejouer la demande donne le même état, pas un second plafond."""
    session_ouverte(client, session_bd)
    categorie_id = creer_categorie(client)

    client.put("/api/plafonds", json={"categorie_id": categorie_id, "montant_centimes": 40000})
    reponse = client.put(
        "/api/plafonds", json={"categorie_id": categorie_id, "montant_centimes": 50000}
    )
    assert len(reponse.json()) == 1
    assert reponse.json()[0]["limite_centimes"] == 50000


def test_la_consommation_suit_les_depenses(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    categorie_id = creer_categorie(client)
    client.put("/api/plafonds", json={"categorie_id": categorie_id, "montant_centimes": 40000})

    depenser(client, compte_id, categorie_id, -12000)
    plafond = client.get("/api/plafonds").json()[0]

    assert plafond["consomme_centimes"] == 12000
    assert plafond["restant_centimes"] == 28000
    assert plafond["part_consommee"] == 30
    assert plafond["depasse"] is False


def test_le_depassement_est_signale(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    categorie_id = creer_categorie(client)
    client.put("/api/plafonds", json={"categorie_id": categorie_id, "montant_centimes": 10000})

    depenser(client, compte_id, categorie_id, -12500)
    plafond = client.get("/api/plafonds").json()[0]

    assert plafond["depasse"] is True
    assert plafond["restant_centimes"] == -2500
    assert plafond["part_consommee"] == 125


def test_une_depense_dune_autre_categorie_ne_compte_pas(
    client: TestClient, session_bd: Session
) -> None:
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    courses = creer_categorie(client, "Courses")
    transport = creer_categorie(client, "Transport")
    client.put("/api/plafonds", json={"categorie_id": courses, "montant_centimes": 40000})

    depenser(client, compte_id, transport, -30000)
    assert client.get("/api/plafonds").json()[0]["consomme_centimes"] == 0


def test_le_solde_douverture_ne_consomme_pas_de_plafond(
    client: TestClient, session_bd: Session
) -> None:
    """Un découvert de départ n'est pas une dépense du mois : l'y compter ferait sauter
    tous les plafonds dès la création du compte."""
    session_ouverte(client, session_bd)
    categorie_id = creer_categorie(client)
    client.post(
        "/api/comptes", json={"nom": "Courant", "solde_ouverture_centimes": -50000}
    )
    client.put("/api/plafonds", json={"categorie_id": categorie_id, "montant_centimes": 10000})

    assert client.get("/api/plafonds").json()[0]["consomme_centimes"] == 0


def test_une_categorie_dun_autre_foyer_est_refusee(
    client: TestClient, session_bd: Session
) -> None:
    from mycounts.models.budget import NatureCategorie, TeinteCategorie
    from mycounts.repository import budget as depot_budget

    from tests.integration.test_api_auth import creer_compte as creer_utilisateur

    autre_foyer, autre_utilisateur = creer_utilisateur(session_bd, "b@essai.fr", nom_foyer="B")
    autre = Principal(utilisateur_id=autre_utilisateur, foyer_id=autre_foyer)
    etrangere = depot_budget.creer_categorie(
        session_bd, autre, nom="Perso B", nature=NatureCategorie.DEPENSE,
        teinte=TeinteCategorie.ROSE,
    )
    session_bd.commit()

    session_ouverte(client, session_bd)
    reponse = client.put(
        "/api/plafonds", json={"categorie_id": str(etrangere.id), "montant_centimes": 10000}
    )
    assert reponse.status_code == 404


def test_les_plafonds_sont_personnels(client: TestClient, session_bd: Session) -> None:
    """Voir le plafond de l'autre membre reviendrait à voir ses intentions de dépense."""
    from mycounts.domain.securite import hacher_mot_de_passe
    from mycounts.repository import auth as depot_auth
    from mycounts.repository import plafonds as depot_plafonds

    principal = session_ouverte(client, session_bd)
    categorie_id = creer_categorie(client)
    client.put("/api/plafonds", json={"categorie_id": categorie_id, "montant_centimes": 40000})

    conjoint = depot_auth.creer_utilisateur(
        session_bd,
        foyer_id=principal.foyer_id,
        courriel="conjoint@essai.fr",
        nom_affichage="Conjoint",
        empreinte_mot_de_passe=hacher_mot_de_passe("correct cheval batterie agrafe"),
    )
    session_bd.commit()
    autre = Principal(utilisateur_id=conjoint.id, foyer_id=principal.foyer_id)

    assert len(depot_plafonds.plafonds_de(session_bd, principal)) == 1
    assert depot_plafonds.plafonds_de(session_bd, autre) == []


def test_un_montant_negatif_est_refuse(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    categorie_id = creer_categorie(client)
    reponse = client.put(
        "/api/plafonds", json={"categorie_id": categorie_id, "montant_centimes": -100}
    )
    assert reponse.status_code == 422


def test_supprimer_un_plafond(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    categorie_id = creer_categorie(client)
    plafond = client.put(
        "/api/plafonds", json={"categorie_id": categorie_id, "montant_centimes": 40000}
    ).json()[0]

    assert client.delete(f"/api/plafonds/{plafond['id']}").status_code == 204
    assert client.get("/api/plafonds").json() == []
