"""Modification et retrait d'une opération.

Le test central est `test_temoin_une_echeance_annulee_ne_revient_pas` : c'est la mesure
qui distingue une annulation d'une suppression. Une suppression sèche paraîtrait juste
jusqu'au passage suivant du job, qui recréerait la ligne sans que rien ne l'explique.
"""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from mycounts.domain.calendrier import aujourd_hui
from mycounts.jobs.materialisation import materialiser
from sqlalchemy.orm import Session

from tests.integration.test_api_agenda import creer_recurrence_api
from tests.integration.test_api_budget import creer_compte_api, session_ouverte

AUJOURD_HUI = aujourd_hui()


def saisir(client: TestClient, compte_id: str, libelle: str, centimes: int) -> dict:  # type: ignore[type-arg]
    reponse = client.post(
        "/api/operations",
        json={
            "compte_id": compte_id,
            "libelle": libelle,
            "montant_centimes": centimes,
            "date_operation": AUJOURD_HUI.isoformat(),
        },
    )
    assert reponse.status_code == 201, reponse.text
    return dict(reponse.json())


def test_les_routes_exigent_une_session(client: TestClient) -> None:
    faux = "00000000-0000-0000-0000-000000000000"
    assert client.patch(f"/api/operations/{faux}", json={}).status_code == 401
    assert client.delete(f"/api/operations/{faux}").status_code == 401


def test_modifier_une_operation(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    operation = saisir(client, compte_id, "Cousres", -4590)

    reponse = client.patch(
        f"/api/operations/{operation['id']}",
        json={"libelle": "Courses", "montant_centimes": -5290},
    )
    assert reponse.status_code == 200
    assert reponse.json()["libelle"] == "Courses"
    assert reponse.json()["montant_centimes"] == -5290


def test_retirer_la_categorie_dune_operation(client: TestClient, session_bd: Session) -> None:
    """`null` signifie retirer ; un champ absent signifie conserver.

    Le formulaire envoie réellement `categorie_id: null`. Le repository traitait
    auparavant cette valeur comme un champ absent et annonçait un succès sans rien faire.
    """
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    categorie = client.post(
        "/api/categories",
        json={"nom": "Courses", "nature": "depense", "teinte": "vert"},
    ).json()
    operation = client.post(
        "/api/operations",
        json={
            "compte_id": compte_id,
            "libelle": "Marché",
            "montant_centimes": -4590,
            "date_operation": AUJOURD_HUI.isoformat(),
            "categorie_id": categorie["id"],
        },
    ).json()

    inchangee = client.patch(f"/api/operations/{operation['id']}", json={}).json()
    assert inchangee["categorie_id"] == categorie["id"]

    retiree = client.patch(
        f"/api/operations/{operation['id']}", json={"categorie_id": None}
    )
    assert retiree.status_code == 200, retiree.text
    assert retiree.json()["categorie_id"] is None


def test_la_modification_met_a_jour_les_soldes(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    operation = saisir(client, compte_id, "Courses", -4590)

    avant = client.get("/api/resume").json()["solde_reel"]
    client.patch(f"/api/operations/{operation['id']}", json={"montant_centimes": -1000})
    apres = client.get("/api/resume").json()["solde_reel"]

    assert apres - avant == 3590, "le solde doit suivre la correction, au centime près"


def test_supprimer_une_saisie_manuelle_la_retire_vraiment(
    client: TestClient, session_bd: Session
) -> None:
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    operation = saisir(client, compte_id, "Erreur", -1000)

    assert client.delete(f"/api/operations/{operation['id']}").status_code == 204
    assert client.get("/api/operations").json() == []
    assert client.get("/api/resume").json()["solde_reel"] == 0


def test_temoin_une_echeance_annulee_ne_revient_pas(
    client: TestClient, session_bd: Session
) -> None:
    """LE contrôle de cette étape.

    Une opération issue d'un prélèvement est annulée et CONSERVÉE. Si elle était
    supprimée, le job la recréerait au passage suivant : la clé d'idempotence
    `uq_operation_par_echeance` ne la verrait plus. Le job est donc rejoué trois fois.
    """
    principal = session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    creer_recurrence_api(client, compte_id, AUJOURD_HUI - dt.timedelta(days=1))
    materialiser(session_bd, foyer_id=principal.foyer_id)

    matérialisée = client.get("/api/operations?periode_courante=false").json()[0]
    assert matérialisée["recurrence_id"] is not None

    assert client.delete(f"/api/operations/{matérialisée['id']}").status_code == 204

    for _ in range(3):
        materialiser(session_bd, foyer_id=principal.foyer_id)

    assert client.get("/api/operations?periode_courante=false").json() == [], (
        "l'échéance annulée est revenue : l'annulation ne tient pas"
    )
    assert client.get("/api/operations/a-confirmer").json() == []


def test_une_operation_annulee_sort_de_tous_les_totaux(
    client: TestClient, session_bd: Session
) -> None:
    principal = session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    creer_recurrence_api(client, compte_id, AUJOURD_HUI - dt.timedelta(days=1))
    materialiser(session_bd, foyer_id=principal.foyer_id)

    operation = client.get("/api/operations?periode_courante=false").json()[0]
    avant = client.get("/api/resume").json()
    client.delete(f"/api/operations/{operation['id']}")
    apres = client.get("/api/resume").json()

    assert avant["solde_reel"] != apres["solde_reel"] or avant["solde_a_confirmer"] != 0
    assert apres["solde_a_confirmer"] == 0
    assert apres["depenses_de_periode"] == 0


def test_une_operation_deja_retiree_est_introuvable(
    client: TestClient, session_bd: Session
) -> None:
    """Une seconde suppression ne doit pas prétendre avoir réussi."""
    principal = session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    creer_recurrence_api(client, compte_id, AUJOURD_HUI - dt.timedelta(days=1))
    materialiser(session_bd, foyer_id=principal.foyer_id)

    operation = client.get("/api/operations?periode_courante=false").json()[0]
    client.delete(f"/api/operations/{operation['id']}")

    assert client.delete(f"/api/operations/{operation['id']}").status_code == 404
    assert client.patch(f"/api/operations/{operation['id']}", json={}).status_code == 404


def test_une_operation_dun_autre_foyer_est_introuvable(
    client: TestClient, session_bd: Session
) -> None:
    from mycounts.domain.montants import Cents
    from mycounts.repository import budget as depot_budget
    from mycounts.repository.base import Principal

    from tests.integration.test_api_auth import creer_compte as creer_utilisateur

    autre_foyer, autre_utilisateur = creer_utilisateur(session_bd, "b@essai.fr", nom_foyer="B")
    autre = Principal(utilisateur_id=autre_utilisateur, foyer_id=autre_foyer)
    compte = depot_budget.creer_compte(session_bd, autre, nom="Perso B")
    session_bd.commit()
    etrangere = depot_budget.creer_operation(
        session_bd, autre, compte_id=compte.id, libelle="Privé",
        montant_centimes=Cents(-100), date_operation=AUJOURD_HUI,
    )
    session_bd.commit()

    session_ouverte(client, session_bd)
    assert client.delete(f"/api/operations/{etrangere.id}").status_code == 404
    assert client.patch(f"/api/operations/{etrangere.id}", json={}).status_code == 404


def test_une_paie_ne_peut_pas_devenir_negative(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    paie = client.post(
        "/api/operations",
        json={
            "compte_id": compte_id,
            "libelle": "Salaire",
            "montant_centimes": 250000,
            "date_operation": AUJOURD_HUI.isoformat(),
            "est_paie": True,
        },
    ).json()

    reponse = client.patch(
        f"/api/operations/{paie['id']}", json={"montant_centimes": -250000}
    )
    assert reponse.status_code == 422
