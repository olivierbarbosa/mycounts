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


def test_un_foyer_neuf_na_aucune_categorie(client: TestClient, session_bd: Session) -> None:
    """Aucune catégorie n'est imposée : l'utilisateur crée les siennes."""
    session_ouverte(client, session_bd)
    assert client.get("/categories").json() == []


def test_creer_une_categorie_puis_la_relire(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    reponse = client.post(
        "/categories", json={"nom": "Courses", "nature": "depense", "teinte": "vert"}
    )
    assert reponse.status_code == 201
    assert [c["nom"] for c in client.get("/categories").json()] == ["Courses"]


def test_une_categorie_dun_autre_foyer_est_refusee(
    client: TestClient, session_bd: Session
) -> None:
    """Rattacher une opération à la catégorie d'un autre foyer révélerait son existence."""
    from mycounts.models.budget import NatureCategorie, TeinteCategorie

    autre_foyer, autre_utilisateur = creer_compte(session_bd, "b@essai.fr", nom_foyer="B")
    autre = Principal(utilisateur_id=autre_utilisateur, foyer_id=autre_foyer)
    categorie_etrangere = depot.creer_categorie(
        session_bd, autre, nom="Perso B", nature=NatureCategorie.DEPENSE,
        teinte=TeinteCategorie.ROSE,
    )
    session_bd.commit()

    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    reponse = client.post(
        "/operations",
        json={
            "compte_id": compte_id,
            "libelle": "Intrusion",
            "montant_centimes": -100,
            "date_operation": AUJOURD_HUI.isoformat(),
            "categorie_id": str(categorie_etrangere.id),
        },
    )
    assert reponse.status_code == 404


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


# --- Catégories : cycle de vie complet -------------------------------------------


def test_le_foyer_nait_avec_ses_categories(client: TestClient, session_bd: Session) -> None:
    """Le script de création du foyer amorce la liste par défaut."""
    from mycounts.repository import budget as depot_budget

    foyer_id, utilisateur_id = creer_compte(session_bd, "c@essai.fr", nom_foyer="Avec catégories")
    depot_budget.creer_categories_initiales(session_bd, foyer_id)
    session_bd.commit()
    connecter(client, "c@essai.fr")

    noms = [c["nom"] for c in client.get("/categories").json()]
    assert "Courses" in noms
    assert "Salaire" in noms
    del utilisateur_id


def test_renommer_et_retinter_une_categorie(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    creee = client.post(
        "/categories", json={"nom": "Courses", "nature": "depense", "teinte": "vert"}
    ).json()

    modifiee = client.patch(
        f"/categories/{creee['id']}", json={"nom": "Alimentation", "teinte": "ambre"}
    )
    assert modifiee.status_code == 200
    assert modifiee.json()["nom"] == "Alimentation"
    assert modifiee.json()["teinte"] == "ambre"
    assert modifiee.json()["nature"] == "depense", "la nature n'est pas modifiable"


def test_archiver_une_categorie_la_retire_des_listes(
    client: TestClient, session_bd: Session
) -> None:
    session_ouverte(client, session_bd)
    creee = client.post(
        "/categories", json={"nom": "Courses", "nature": "depense", "teinte": "vert"}
    ).json()
    client.patch(f"/categories/{creee['id']}", json={"archivee": True})
    assert client.get("/categories").json() == []


def test_supprimer_une_categorie_inutilisee(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    creee = client.post(
        "/categories", json={"nom": "Éphémère", "nature": "depense", "teinte": "rose"}
    ).json()
    assert client.delete(f"/categories/{creee['id']}").status_code == 204
    assert client.get("/categories").json() == []


def test_supprimer_une_categorie_utilisee_est_refuse(
    client: TestClient, session_bd: Session
) -> None:
    """Supprimer une catégorie utilisée changerait rétroactivement les totaux d'un mois
    déjà clos. Le refus doit proposer l'archivage."""
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    creee = client.post(
        "/categories", json={"nom": "Courses", "nature": "depense", "teinte": "vert"}
    ).json()
    client.post(
        "/operations",
        json={
            "compte_id": compte_id,
            "libelle": "Courses",
            "montant_centimes": -4590,
            "date_operation": AUJOURD_HUI.isoformat(),
            "categorie_id": creee["id"],
        },
    )

    refus = client.delete(f"/categories/{creee['id']}")
    assert refus.status_code == 409
    assert "archiver" in refus.json()["detail"].lower()
    assert len(client.get("/categories").json()) == 1, "la catégorie doit rester en place"


# --- Solde d'ouverture -----------------------------------------------------------


def test_le_solde_douverture_alimente_le_solde_sans_etre_une_depense(
    client: TestClient, session_bd: Session
) -> None:
    """Un découvert de départ n'est pas une dépense du mois : l'y compter ferait sauter
    tous les plafonds dès la création du compte."""
    session_ouverte(client, session_bd)
    client.post("/comptes", json={"nom": "Courant", "solde_ouverture_centimes": -15000})

    resume = client.get("/resume").json()
    assert resume["solde_reel"] == -15000
    assert resume["depenses_de_periode"] == 0


def test_un_solde_douverture_nul_ne_cree_aucune_operation(
    client: TestClient, session_bd: Session
) -> None:
    session_ouverte(client, session_bd)
    client.post("/comptes", json={"nom": "Vide", "solde_ouverture_centimes": 0})
    assert client.get("/operations?periode_courante=false").json() == []


def test_le_solde_douverture_est_identifiable(client: TestClient, session_bd: Session) -> None:
    """Témoin : sans le marqueur, l'ouverture serait indiscernable d'un vrai revenu et
    fausserait toute analyse des rentrées d'argent."""
    session_ouverte(client, session_bd)
    client.post("/comptes", json={"nom": "Courant", "solde_ouverture_centimes": 120000})
    operations = client.get("/operations?periode_courante=false").json()
    assert len(operations) == 1
    assert operations[0]["est_ouverture"] is True
    assert operations[0]["est_paie"] is False, "une ouverture n'ouvre pas de période"
