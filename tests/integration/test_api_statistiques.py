"""Statistiques, contre PostgreSQL.

Le test qui compte est `un virement n'est pas une dépense` : une première version du filtre
lisait les drapeaux par `getattr(..., défaut)` et rendait `False` pour un attribut qui
n'existe pas, si bien que toute mise de côté serait entrée dans les statistiques comme un
achat. Le typage l'a rattrapé ; ce test l'empêche de revenir.
"""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.integration.test_api_budget import session_ouverte

AUJOURD_HUI = dt.date.today()


def creer_compte(client: TestClient, nom: str, produit: str = "compte_courant") -> str:
    reponse = client.post("/api/comptes", json={"nom": nom, "prive": True, "produit": produit})
    assert reponse.status_code == 201, reponse.text
    return str(reponse.json()["id"])


def creer_categorie(client: TestClient, nom: str) -> str:
    reponse = client.post(
        "/api/categories", json={"nom": nom, "nature": "depense", "teinte": "vert"}
    )
    assert reponse.status_code == 201, reponse.text
    return str(reponse.json()["id"])


def depenser(
    client: TestClient, compte: str, libelle: str, centimes: int, categorie: str | None = None
) -> None:
    reponse = client.post(
        "/api/operations",
        json={
            "compte_id": compte,
            "libelle": libelle,
            "montant_centimes": -abs(centimes),
            "date_operation": AUJOURD_HUI.isoformat(),
            "categorie_id": categorie,
        },
    )
    assert reponse.status_code == 201, reponse.text


def test_les_depenses_se_repartissent_par_categorie(
    client: TestClient, session_bd: Session
) -> None:
    session_ouverte(client, session_bd)
    compte = creer_compte(client, "Courant")
    courses = creer_categorie(client, "Courses")
    depenser(client, compte, "Carrefour", 6_000, courses)
    depenser(client, compte, "Divers", 4_000)

    stats = client.get("/api/statistiques").json()
    postes = {p["categorie"]: p for p in stats["postes"]}
    assert postes["Courses"]["montant_centimes"] == 6_000
    assert postes["Courses"]["part"] == 60
    # « Sans catégorie » est un poste comme les autres, jamais masqué.
    assert postes[None]["montant_centimes"] == 4_000


def test_un_virement_nest_pas_une_depense(client: TestClient, session_bd: Session) -> None:
    """La règle du projet, appliquée aux statistiques : l'argent n'a pas quitté le foyer.

    Le compter ferait apparaître une dépense à chaque mise de côté, et gonflerait le total
    d'un montant que l'utilisateur n'a jamais dépensé.
    """
    session_ouverte(client, session_bd)
    courant = creer_compte(client, "Courant")
    livret = creer_compte(client, "Livret", "livret_a")
    depenser(client, courant, "Carrefour", 5_000)

    avant = client.get("/api/statistiques").json()
    reponse = client.post(
        "/api/virements",
        json={
            "compte_source_id": courant,
            "compte_destination_id": livret,
            "montant_centimes": 20_000,
            "date_operation": AUJOURD_HUI.isoformat(),
            "libelle": "Mise de côté",
        },
    )
    assert reponse.status_code == 201, reponse.text

    apres = client.get("/api/statistiques").json()
    assert apres["total_centimes"] == avant["total_centimes"]
    assert apres["nombre_de_depenses"] == avant["nombre_de_depenses"]


def test_un_solde_douverture_nest_pas_une_depense(
    client: TestClient, session_bd: Session
) -> None:
    """Un découvert de départ est un amorçage, pas un achat du mois."""
    session_ouverte(client, session_bd)
    reponse = client.post(
        "/api/comptes",
        json={
            "nom": "Amorce",
            "prive": True,
            "produit": "compte_courant",
            "solde_ouverture_centimes": -30_000,
        },
    )
    assert reponse.status_code == 201, reponse.text

    stats = client.get("/api/statistiques").json()
    assert stats["total_centimes"] == 0


def test_le_goutte_a_goutte_est_signale(client: TestClient, session_bd: Session) -> None:
    """Trois passages au même endroit, dont le total surprend."""
    session_ouverte(client, session_bd)
    compte = creer_compte(client, "Courant")
    for _ in range(3):
        depenser(client, compte, "Sushi Shop", 2_500)

    stats = client.get("/api/statistiques").json()
    constat = next(c for c in stats["constats"] if c["motif"] == "goutte_a_goutte")
    assert constat["sujet"] == "Sushi Shop"
    assert constat["montant_centimes"] == 7_500
    assert constat["detail"] == 3


def test_le_cout_annuel_des_abonnements_est_calcule(
    client: TestClient, session_bd: Session
) -> None:
    """Le chiffre que les douzièmes rendent invisible : 12 € par mois font 144 € par an."""
    session_ouverte(client, session_bd)
    compte = creer_compte(client, "Courant")
    reponse = client.post(
        "/api/recurrences",
        json={
            "compte_id": compte,
            "libelle": "Abonnement",
            "montant_centimes": -1_200,
            "ancre": AUJOURD_HUI.isoformat(),
            "unite": "mois",
            "intervalle": 1,
        },
    )
    assert reponse.status_code == 201, reponse.text

    stats = client.get("/api/statistiques").json()
    assert stats["cout_annuel_des_abonnements_centimes"] == 14_400
    assert any(c["motif"] == "abonnements" for c in stats["constats"])


def test_un_revenu_recurrent_ne_compte_PAS_dans_les_abonnements(
    client: TestClient, session_bd: Session
) -> None:
    """Un salaire mensuel est une récurrence lui aussi. L'additionner aux abonnements
    produirait un total qui ne veut rien dire."""
    session_ouverte(client, session_bd)
    compte = creer_compte(client, "Courant")
    client.post(
        "/api/recurrences",
        json={
            "compte_id": compte,
            "libelle": "Salaire",
            "montant_centimes": 250_000,
            "ancre": AUJOURD_HUI.isoformat(),
            "unite": "mois",
            "intervalle": 1,
        },
    )

    stats = client.get("/api/statistiques").json()
    assert stats["cout_annuel_des_abonnements_centimes"] == 0
