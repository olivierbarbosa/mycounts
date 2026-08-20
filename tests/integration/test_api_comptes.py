"""Catalogue des produits, modification et suppression d'un compte.

Le test central est `supprimer un compte qui porte des opérations est refusé` : sans ce
refus, les lignes disparaîtraient des soldes et des totaux passés, et un mois déjà clos
changerait de montant après coup.
"""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from mycounts.domain.comptes import CATALOGUE, TypeCompte
from sqlalchemy.orm import Session

from tests.integration.test_api_budget import session_ouverte


def creer(client: TestClient, nom: str, produit: str = "compte_courant") -> dict:  # type: ignore[type-arg]
    reponse = client.post(
        "/api/comptes", json={"nom": nom, "prive": True, "produit": produit}
    )
    assert reponse.status_code == 201, reponse.text
    return dict(reponse.json())


def test_le_catalogue_traduit_chaque_produit_en_comportement(
    client: TestClient, session_bd: Session
) -> None:
    """Un produit qui n'annoncerait pas son comportement laisserait l'écran le deviner."""
    session_ouverte(client, session_bd)
    produits = client.get("/api/comptes/catalogue").json()

    assert len(produits) == len(CATALOGUE)
    assert {p["type_compte"] for p in produits} == {TypeCompte.COURANT, TypeCompte.EPARGNE}
    par_cle = {p["cle"]: p for p in produits}
    assert par_cle["livret_a"]["type_compte"] == TypeCompte.EPARGNE
    assert par_cle["compte_courant"]["type_compte"] == TypeCompte.COURANT


def test_le_comportement_est_deduit_du_produit(client: TestClient, session_bd: Session) -> None:
    """Demander « un Livret A » suffit : le client n'envoie jamais le comportement.

    Le témoin oppose deux produits qui ne doivent PAS donner le même résultat — sans le
    second, un code qui renverrait toujours « épargne » passerait le test.
    """
    session_ouverte(client, session_bd)
    assert creer(client, "Livret", "livret_a")["type_compte"] == TypeCompte.EPARGNE
    assert creer(client, "Courant", "compte_courant")["type_compte"] == TypeCompte.COURANT


def test_un_produit_inconnu_est_refuse(client: TestClient, session_bd: Session) -> None:
    """Plutôt que de retomber sur un produit par défaut : deviner le comportement d'un
    compte reviendrait à déplacer de l'argent d'une colonne à l'autre sans qu'on l'ait
    demandé."""
    session_ouverte(client, session_bd)
    reponse = client.post(
        "/api/comptes", json={"nom": "Bizarre", "prive": True, "produit": "livret_martien"}
    )
    assert reponse.status_code == 422, reponse.text


def test_changer_de_produit_change_le_comportement(
    client: TestClient, session_bd: Session
) -> None:
    """C'est le seul moyen de corriger une création faite trop vite."""
    session_ouverte(client, session_bd)
    compte = creer(client, "Mal nommé", "compte_courant")

    reponse = client.patch(
        f"/api/comptes/{compte['id']}", json={"nom": "Livret A", "produit": "livret_a"}
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["nom"] == "Livret A"
    assert reponse.json()["type_compte"] == TypeCompte.EPARGNE
    assert reponse.json()["produit_libelle"] == "Livret A"


def test_renommer_ne_reinitialise_pas_le_produit(
    client: TestClient, session_bd: Session
) -> None:
    """Les champs absents restent inchangés. Sans cette distinction, renommer un livret le
    remettrait en compte courant et sortirait son argent de la page Épargne."""
    session_ouverte(client, session_bd)
    compte = creer(client, "Livret", "livret_a")

    reponse = client.patch(f"/api/comptes/{compte['id']}", json={"nom": "Livret bleu"})
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["produit"] == "livret_a"
    assert reponse.json()["type_compte"] == TypeCompte.EPARGNE


def test_supprimer_un_compte_vide(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    compte = creer(client, "À jeter")

    assert client.delete(f"/api/comptes/{compte['id']}").status_code == 204
    assert [c["nom"] for c in client.get("/api/comptes").json()] == []


def test_supprimer_un_compte_qui_porte_des_operations_est_refuse(
    client: TestClient, session_bd: Session
) -> None:
    session_ouverte(client, session_bd)
    compte = creer(client, "Utilisé")
    client.post(
        "/api/operations",
        json={
            "compte_id": compte["id"],
            "libelle": "Courses",
            "montant_centimes": -1_000,
            "date_operation": dt.date.today().isoformat(),
        },
    )

    reponse = client.delete(f"/api/comptes/{compte['id']}")
    assert reponse.status_code == 409, reponse.text
    assert "Archivez" in reponse.json()["detail"], "le refus doit dire quoi faire à la place"
    # Et le compte est toujours là : un refus qui supprimerait quand même serait pire.
    assert [c["nom"] for c in client.get("/api/comptes").json()] == ["Utilisé"]


def test_les_soldes_sont_rendus_par_compte(client: TestClient, session_bd: Session) -> None:
    """Le solde RÉEL, pas le projeté : une carte répond à « combien y a-t-il dessus »."""
    session_ouverte(client, session_bd)
    def avec_solde(nom: str, produit: str, ouverture: int) -> dict:  # type: ignore[type-arg]
        return dict(
            client.post(
                "/api/comptes",
                json={
                    "nom": nom,
                    "prive": True,
                    "produit": produit,
                    "solde_ouverture_centimes": ouverture,
                },
            ).json()
        )

    a = avec_solde("A", "compte_courant", 30_000)
    b = avec_solde("B", "livret_a", 12_000)

    rendus = client.get("/api/comptes/soldes").json()
    soldes = {s["compte_id"]: s["solde_centimes"] for s in rendus}
    assert soldes[a["id"]] == 30_000
    assert soldes[b["id"]] == 12_000
