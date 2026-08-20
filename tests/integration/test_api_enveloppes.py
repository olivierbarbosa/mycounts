"""Enveloppes, contre PostgreSQL.

Le test central est `réserver ne déplace aucun argent` : c'est la règle qui commande tout
le module. Une allocation qui créerait une opération ferait apparaître de l'argent qui
n'existe pas — le compte dit où l'argent EST, l'enveloppe à quoi il est PROMIS.
"""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.integration.test_api_budget import session_ouverte

AUJOURD_HUI = dt.date.today()


def creer_compte(client: TestClient, nom: str, produit: str, ouverture: int = 0) -> str:
    reponse = client.post(
        "/api/comptes",
        json={
            "nom": nom,
            "prive": True,
            "produit": produit,
            "solde_ouverture_centimes": ouverture,
        },
    )
    assert reponse.status_code == 201, reponse.text
    return str(reponse.json()["id"])


def creer_enveloppe(client: TestClient, nom: str, **kw: object) -> dict:  # type: ignore[type-arg]
    reponse = client.post("/api/enveloppes", json={"nom": nom, **kw})
    assert reponse.status_code == 201, reponse.text
    return dict(reponse.json())


def enveloppe_nommee(repartition: dict, nom: str) -> dict:  # type: ignore[type-arg]
    return next(e for e in repartition["enveloppes"] if e["nom"] == nom)


def test_reserver_ne_deplace_aucun_argent(client: TestClient, session_bd: Session) -> None:
    """La règle qui commande tout le module.

    Trois grandeurs : l'épargne totale ne doit PAS bouger, le réservé doit monter, et le
    nombre d'opérations en base doit rester identique. Sans la troisième, une allocation
    qui écrirait discrètement une opération passerait — c'est exactement ce que le
    document de référence interdit.
    """
    session_ouverte(client, session_bd)
    creer_compte(client, "Courant", "compte_courant", ouverture=100_000)
    creer_compte(client, "Livret A", "livret_a", ouverture=300_000)

    avant = client.get("/api/enveloppes").json()
    operations_avant = len(client.get("/api/operations?periode_courante=false").json())
    assert avant["epargne_totale_centimes"] == 300_000
    assert avant["non_affecte_centimes"] == 300_000

    apres = creer_enveloppe(client, "Impôts", allocation_initiale_centimes=90_000)

    assert apres["epargne_totale_centimes"] == 300_000, "l'argent en banque n'a pas bougé"
    assert apres["reserve_centimes"] == 90_000
    assert apres["non_affecte_centimes"] == 210_000
    assert (
        len(client.get("/api/operations?periode_courante=false").json()) == operations_avant
    ), "une allocation ne doit créer AUCUNE opération bancaire"


def test_le_solde_vient_du_journal_pas_dune_valeur_ecrite(
    client: TestClient, session_bd: Session
) -> None:
    session_ouverte(client, session_bd)
    creer_compte(client, "Livret A", "livret_a", ouverture=300_000)
    etat = creer_enveloppe(client, "Vacances", allocation_initiale_centimes=50_000)
    enveloppe_id = enveloppe_nommee(etat, "Vacances")["id"]

    for type_, montant in (("depense", 12_000), ("remboursement", 2_000)):
        reponse = client.post(
            f"/api/enveloppes/{enveloppe_id}/mouvements",
            json={"type": type_, "montant_centimes": montant},
        )
        assert reponse.status_code == 201, reponse.text

    etat = client.get("/api/enveloppes").json()
    assert enveloppe_nommee(etat, "Vacances")["solde_centimes"] == 40_000

    journal = client.get(f"/api/enveloppes/{enveloppe_id}/journal").json()
    assert [m["type"] for m in journal] == ["allocation", "depense", "remboursement"]
    assert all(m["montant_centimes"] > 0 for m in journal), "les montants sont tous positifs"


def test_une_enveloppe_negative_ne_rogne_pas_les_autres(
    client: TestClient, session_bd: Session
) -> None:
    """Le témoin du calcul de réservé : deux enveloppes, dont une dans le rouge.

    Une somme naïve donnerait 85 000 et ferait croire à 15 000 € de plus disponibles.
    """
    session_ouverte(client, session_bd)
    creer_compte(client, "Livret A", "livret_a", ouverture=300_000)
    creer_enveloppe(client, "Impôts", allocation_initiale_centimes=90_000)
    vacances = creer_enveloppe(client, "Vacances")
    vide = enveloppe_nommee(vacances, "Vacances")["id"]

    client.post(
        f"/api/enveloppes/{vide}/mouvements",
        json={"type": "depense", "montant_centimes": 5_000},
    )

    etat = client.get("/api/enveloppes").json()
    assert enveloppe_nommee(etat, "Vacances")["solde_centimes"] == -5_000
    assert etat["reserve_centimes"] == 90_000, "le négatif ne diminue pas le réservé"
    assert etat["non_affecte_centimes"] == 210_000


def test_le_non_affecte_passe_en_negatif_quand_lepargne_ne_couvre_plus(
    client: TestClient, session_bd: Session
) -> None:
    """Les promesses ne sont plus couvertes : il faut que ça se voie."""
    session_ouverte(client, session_bd)
    creer_compte(client, "Livret A", "livret_a", ouverture=50_000)
    etat = creer_enveloppe(client, "Impôts", allocation_initiale_centimes=90_000)

    assert etat["non_affecte_centimes"] == -40_000
    assert etat["decouvert"] is True


def test_la_place_restante_est_nulle_sans_cible(client: TestClient, session_bd: Session) -> None:
    """`null` et non zéro : sans cible, la préparation mensuelle ne recommandera rien."""
    session_ouverte(client, session_bd)
    creer_compte(client, "Livret A", "livret_a", ouverture=300_000)
    creer_enveloppe(client, "Divers", allocation_initiale_centimes=10_000)
    creer_enveloppe(client, "Ski", allocation_initiale_centimes=10_000, cible_centimes=30_000)

    etat = client.get("/api/enveloppes").json()
    assert enveloppe_nommee(etat, "Divers")["place_centimes"] is None
    assert enveloppe_nommee(etat, "Ski")["place_centimes"] == 20_000


def test_un_montant_negatif_est_refuse(client: TestClient, session_bd: Session) -> None:
    """Le sens vient du type : accepter un montant signé rendrait possible une allocation
    négative, c'est-à-dire une reprise déguisée, invisible dans un journal filtré."""
    session_ouverte(client, session_bd)
    creer_compte(client, "Livret A", "livret_a", ouverture=100_000)
    etat = creer_enveloppe(client, "Vacances")
    enveloppe_id = enveloppe_nommee(etat, "Vacances")["id"]

    for montant in (0, -5_000):
        reponse = client.post(
            f"/api/enveloppes/{enveloppe_id}/mouvements",
            json={"type": "allocation", "montant_centimes": montant},
        )
        assert reponse.status_code == 422, f"montant {montant} : {reponse.text}"


def test_supprimer_une_enveloppe_rend_son_argent_disponible(
    client: TestClient, session_bd: Session
) -> None:
    """Aucun argent ne disparaît : une enveloppe ne détient rien, elle nomme une part."""
    session_ouverte(client, session_bd)
    creer_compte(client, "Livret A", "livret_a", ouverture=300_000)
    etat = creer_enveloppe(client, "Impôts", allocation_initiale_centimes=90_000)
    enveloppe_id = enveloppe_nommee(etat, "Impôts")["id"]

    assert client.delete(f"/api/enveloppes/{enveloppe_id}").status_code == 204

    apres = client.get("/api/enveloppes").json()
    assert apres["enveloppes"] == []
    assert apres["epargne_totale_centimes"] == 300_000, "l'argent est toujours en banque"
    assert apres["non_affecte_centimes"] == 300_000


def test_les_enveloppes_ne_comptent_que_lepargne_pas_le_courant(
    client: TestClient, session_bd: Session
) -> None:
    """Rapportées au compte courant, elles feraient croire qu'on peut réserver ce qui sert
    à vivre le mois.

    Le témoin : un second compte COURANT bien garni ne doit rien changer.
    """
    session_ouverte(client, session_bd)
    creer_compte(client, "Livret A", "livret_a", ouverture=200_000)
    avant = client.get("/api/enveloppes").json()["epargne_totale_centimes"]

    creer_compte(client, "Courant", "compte_courant", ouverture=500_000)
    apres = client.get("/api/enveloppes").json()["epargne_totale_centimes"]

    assert avant == 200_000
    assert apres == 200_000, "le compte courant n'entre pas dans ce qui est découpé"


def test_une_categorie_dun_autre_foyer_est_refusee(
    client: TestClient, session_bd: Session
) -> None:
    import uuid

    session_ouverte(client, session_bd)
    reponse = client.post(
        "/api/enveloppes", json={"nom": "Bizarre", "categorie_id": str(uuid.uuid4())}
    )
    assert reponse.status_code == 404, reponse.text


def test_les_reglages_par_defaut_sont_les_moins_destructeurs(
    client: TestClient, session_bd: Session
) -> None:
    """Une enveloppe créée sans rien régler reporte son solde.

    Le report est le seul mode qui ne fasse disparaître aucun argent réservé chez quelqu'un
    qui n'a rien demandé. Un défaut à `liberation` viderait les enveloppes de tout le monde
    à la première préparation, et personne n'aurait rien signé pour ça.
    """
    session_ouverte(client, session_bd)
    creer_compte(client, "Livret", "livret_a", 500_000)
    creer_enveloppe(client, "Neuve")

    enveloppe = enveloppe_nommee(client.get("/api/enveloppes").json(), "Neuve")
    assert enveloppe["rollover"] == "report"
    assert enveloppe["usage"] == "fonctionnement"
    assert enveloppe["priorite"] == 0
    assert enveloppe["contribution_mensuelle_centimes"] is None


def test_les_reglages_survivent_a_un_aller_retour(
    client: TestClient, session_bd: Session
) -> None:
    """Écrits, relus, et RELUS AILLEURS : la modification renvoie la répartition entière,
    donc une valeur pourrait n'être juste que dans sa réponse immédiate."""
    session_ouverte(client, session_bd)
    creer_compte(client, "Livret", "livret_a", 500_000)
    creee = creer_enveloppe(client, "Vacances", cible_centimes=150_000)
    identifiant = enveloppe_nommee(creee, "Vacances")["id"]

    reponse = client.patch(
        f"/api/enveloppes/{identifiant}",
        json={
            "usage": "reserve",
            "rollover": "liberation",
            "priorite": 3,
            "contribution_mensuelle_centimes": 10_000,
        },
    )
    assert reponse.status_code == 200, reponse.text

    relue = enveloppe_nommee(client.get("/api/enveloppes").json(), "Vacances")
    assert relue["usage"] == "reserve"
    assert relue["rollover"] == "liberation"
    assert relue["priorite"] == 3
    assert relue["contribution_mensuelle_centimes"] == 10_000


def test_un_rollover_inconnu_est_refuse(client: TestClient, session_bd: Session) -> None:
    """La colonne est du texte en base : sans validation, n'importe quelle chaîne y
    entrerait et ne se révélerait qu'au moment de préparer le mois."""
    session_ouverte(client, session_bd)
    creer_compte(client, "Livret", "livret_a", 500_000)
    creee = creer_enveloppe(client, "Essence")
    identifiant = enveloppe_nommee(creee, "Essence")["id"]

    reponse = client.patch(f"/api/enveloppes/{identifiant}", json={"rollover": "peut_etre"})
    assert reponse.status_code == 422, reponse.text


def test_une_contribution_negative_est_refusee(
    client: TestClient, session_bd: Session
) -> None:
    """Une contribution est une somme qu'on PRÉVOIT de mettre. Négative, elle
    recommanderait de retirer de l'argent à chaque période sans que rien ne le dise."""
    session_ouverte(client, session_bd)
    creer_compte(client, "Livret", "livret_a", 500_000)
    creee = creer_enveloppe(client, "Impots")
    identifiant = enveloppe_nommee(creee, "Impots")["id"]

    reponse = client.patch(
        f"/api/enveloppes/{identifiant}", json={"contribution_mensuelle_centimes": -5_000}
    )
    assert reponse.status_code == 422, reponse.text


def test_les_reglages_se_posent_des_la_creation(
    client: TestClient, session_bd: Session
) -> None:
    """Sans quoi il faudrait créer puis modifier : deux requêtes pour un seul geste."""
    session_ouverte(client, session_bd)
    creer_compte(client, "Livret", "livret_a", 500_000)
    creee = creer_enveloppe(
        client, "Ski", usage="reserve", rollover="demander", priorite=2
    )

    enveloppe = enveloppe_nommee(creee, "Ski")
    assert enveloppe["usage"] == "reserve"
    assert enveloppe["rollover"] == "demander"
    assert enveloppe["priorite"] == 2
