"""Plafonds et enveloppes suivent la VUE, comme tout le reste.

Les colonnes `Plafond.vue` et `Enveloppe.vue` existaient depuis la migration
`06db5cb0ed21` et **aucune requête ne les lisait**. En vue foyer, on voyait donc ses
plafonds personnels et ses enveloppes personnelles, sur des écrans qui annoncent ne
montrer que l'argent commun. Une colonne qu'aucune requête ne lit fait croire au modèle
qu'une fonction existe.

Le test central est `un plafond de foyer est commun, un plafond personnel ne l'est pas` :
les deux vues n'ont pas la même règle de propriété, et ce n'est pas une inconséquence —
l'unicité posée en base la dictait déjà. `uq_plafond_de_foyer_par_categorie` n'admet qu'un
seul plafond foyer par catégorie, tous membres confondus.
"""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from mycounts.domain.securite import hacher_mot_de_passe, normaliser_courriel
from mycounts.repository import auth as depot_auth
from sqlalchemy.orm import Session

from tests.integration.test_api_auth import MOT_DE_PASSE, connecter
from tests.integration.test_api_budget import session_ouverte

FOYER = {"X-Mycounts-Vue": "foyer"}


def creer_categorie(client: TestClient, nom: str) -> str:
    reponse = client.post(
        "/api/categories", json={"nom": nom, "nature": "depense", "teinte": "violet"}
    )
    assert reponse.status_code == 201, reponse.text
    return str(reponse.json()["id"])


def test_un_plafond_ne_traverse_pas_les_vues(client: TestClient, session_bd: Session) -> None:
    """Mesuré dans les DEUX sens : chaque vue voit le sien et seulement le sien.

    N'en vérifier qu'un laisserait passer un code qui n'en montrerait jamais aucun.
    """
    session_ouverte(client, session_bd)
    perso = creer_categorie(client, "Perso")
    commun = creer_categorie(client, "Commun")

    assert client.put(
        "/api/plafonds", json={"categorie_id": perso, "montant_centimes": 10_000}
    ).status_code in (200, 201)
    assert client.put(
        "/api/plafonds",
        json={"categorie_id": commun, "montant_centimes": 20_000},
        headers=FOYER,
    ).status_code in (200, 201)

    en_perso = [p["categorie_id"] for p in client.get("/api/plafonds").json()]
    en_foyer = [p["categorie_id"] for p in client.get("/api/plafonds", headers=FOYER).json()]
    assert en_perso == [perso], en_perso
    assert en_foyer == [commun], en_foyer


def test_un_plafond_de_foyer_est_commun_un_plafond_personnel_ne_lest_pas(
    client: TestClient, session_bd: Session
) -> None:
    """Le test central. Deux règles de propriété, dictées par l'unicité en base.

    Sans la seconde moitié, un code qui rendrait TOUS les plafonds du foyer passerait la
    première : c'est justement la fuite qu'il faut exclure — voir le plafond personnel de
    l'autre membre, c'est voir ses intentions de dépense.
    """
    alice = session_ouverte(client, session_bd)
    perso = creer_categorie(client, "Son carnet")
    commun = creer_categorie(client, "Courses communes")
    client.put("/api/plafonds", json={"categorie_id": perso, "montant_centimes": 10_000})
    client.put(
        "/api/plafonds",
        json={"categorie_id": commun, "montant_centimes": 20_000},
        headers=FOYER,
    )

    depot_auth.creer_utilisateur(
        session_bd,
        foyer_id=alice.foyer_id,
        courriel=normaliser_courriel("bruno@essai.fr"),
        nom_affichage="Bruno",
        empreinte_mot_de_passe=hacher_mot_de_passe(MOT_DE_PASSE),
    )
    session_bd.commit()
    connecter(client, "bruno@essai.fr")

    # Ce que Bruno DOIT voir : la limite commune, posée par Alice.
    partages = [p["categorie_id"] for p in client.get("/api/plafonds", headers=FOYER).json()]
    assert partages == [commun], "un plafond du foyer est une décision commune"

    # Ce qu'il ne doit PAS voir : le plafond personnel d'Alice.
    siens = client.get("/api/plafonds").json()
    assert siens == [], "les intentions de dépense d’un autre membre ne se lisent pas"


def test_une_enveloppe_ne_traverse_pas_les_vues(
    client: TestClient, session_bd: Session
) -> None:
    """Une enveloppe découpe une ÉPARGNE, et les deux épargnes sont étanches.

    Les mélanger donnait un découpage dont la somme pouvait dépasser ce qu'il découpe.
    """
    session_ouverte(client, session_bd)
    assert client.post("/api/enveloppes", json={"nom": "Mon projet"}).status_code == 201
    assert (
        client.post("/api/enveloppes", json={"nom": "Notre projet"}, headers=FOYER).status_code
        == 201
    )

    en_perso = [e["nom"] for e in client.get("/api/enveloppes").json()["enveloppes"]]
    en_foyer = [
        e["nom"] for e in client.get("/api/enveloppes", headers=FOYER).json()["enveloppes"]
    ]
    assert en_perso == ["Mon projet"], en_perso
    assert en_foyer == ["Notre projet"], en_foyer


def test_agir_sur_une_enveloppe_de_lautre_vue_est_refuse(
    client: TestClient, session_bd: Session
) -> None:
    """La liste se resserre, les actions suivent — sinon l'écran promet ce qu'il ne tient pas.

    Contrairement aux COMPTES, dont la permission reste large des deux côtés : un compte
    est un objet du foyer qu'on administre, une enveloppe est un découpage propre à une
    épargne, et il n'y a rien à administrer depuis l'autre monde.
    """
    session_ouverte(client, session_bd)
    creee = client.post("/api/enveloppes", json={"nom": "Mon projet"})
    identifiant = next(e["id"] for e in creee.json()["enveloppes"] if e["nom"] == "Mon projet")

    refus = client.post(
        f"/api/enveloppes/{identifiant}/mouvements",
        json={"type": "allocation", "montant_centimes": 1_000},
        headers=FOYER,
    )
    assert refus.status_code == 404, refus.text


def test_une_operation_dit_qui_la_saisie(client: TestClient, session_bd: Session) -> None:
    """« Voir qui modifie quoi », demandé dès le premier jour du partage.

    La colonne existait sur trois tables et n'était exposée nulle part : le modèle savait
    répondre, l'application ne posait jamais la question. Sur un compte joint, c'est
    pourtant la première qu'on se pose devant une ligne qu'on ne reconnaît pas.
    """
    alice = session_ouverte(client, session_bd)
    joint = client.post(
        "/api/comptes",
        json={"nom": "Le joint", "prive": False, "produit": "compte_courant"},
        headers=FOYER,
    ).json()

    depot_auth.creer_utilisateur(
        session_bd,
        foyer_id=alice.foyer_id,
        courriel=normaliser_courriel("bruno@essai.fr"),
        nom_affichage="Bruno",
        empreinte_mot_de_passe=hacher_mot_de_passe(MOT_DE_PASSE),
    )
    session_bd.commit()
    connecter(client, "bruno@essai.fr")

    ecrite = client.post(
        "/api/operations",
        json={
            "compte_id": joint["id"],
            "libelle": "Courses de Bruno",
            "montant_centimes": -3_000,
            "date_operation": "2026-08-21",
        },
        headers=FOYER,
    )
    assert ecrite.status_code == 201, ecrite.text
    bruno_id = client.get("/api/auth/moi").json()["id"]
    assert ecrite.json()["cree_par_id"] == bruno_id

    # Et Alice, qui relit la même ligne, apprend qui l'a écrite.
    connecter(client, "a@essai.fr")
    lignes = client.get("/api/operations", headers=FOYER).json()
    saisie = next(o for o in lignes if o["libelle"] == "Courses de Bruno")
    assert saisie["cree_par_id"] == bruno_id, "l’auteur doit survivre au changement de lecteur"


def test_une_enveloppe_datee_recoit_un_rythme(client: TestClient, session_bd: Session) -> None:
    """« J'ai un voyage au Japon en novembre 2026, il me faut 2 000 €. »

    La `date_cible` était stockée, saisissable, renvoyée par l'API — et lue par aucun
    calcul. Ce test mesure le chemin COMPLET : l'écran écrit une échéance, le serveur en
    déduit un rythme mensuel, et le rend.
    """
    session_ouverte(client, session_bd)
    creee = client.post(
        "/api/enveloppes",
        json={"nom": "Japon", "cible_centimes": 200_000, "date_cible": "2099-12-31"},
    )
    assert creee.status_code == 201, creee.text

    japon = next(e for e in creee.json()["enveloppes"] if e["nom"] == "Japon")
    assert japon["contribution_theorique_centimes"] is not None
    assert japon["contribution_theorique_centimes"] > 0

    # Une enveloppe SANS échéance n'en reçoit aucun : un objectif sans date est un
    # plancher, qu'aucun rythme ne presse.
    client.post("/api/enveloppes", json={"nom": "Travaux", "cible_centimes": 500_000})
    liste = client.get("/api/enveloppes").json()["enveloppes"]
    travaux = next(e for e in liste if e["nom"] == "Travaux")
    assert travaux["contribution_theorique_centimes"] is None


def test_la_preparation_dit_ce_quon_peut_mettre_de_cote(
    client: TestClient, session_bd: Session
) -> None:
    """« Chaque mois, l'application doit calculer combien je peux théoriquement mettre de
    côté. »

    La propriété mesurée est que ce montant EST le solde projeté du quotidien, et non un
    second calcul qui lui ressemble. Deux définitions de « ce qu'il me reste » finiraient
    par diverger, et l'écart passerait pour une panne de l'une des deux pages.

    Projeté et non réel, c'est le point : le premier tient compte des prélèvements encore
    à venir dans la période. Placer le réel viderait le compte courant juste avant
    l'échéance du loyer.
    """
    session_ouverte(client, session_bd)
    client.post(
        "/api/comptes",
        json={
            "nom": "Courant",
            "prive": True,
            "produit": "compte_courant",
            "solde_ouverture_centimes": 50_000,
        },
    )
    epargne = client.post(
        "/api/comptes", json={"nom": "LEP", "prive": True, "produit": "lep"}
    ).json()
    client.post("/api/enveloppes", json={"nom": "Japon", "cible_centimes": 200_000})

    resume = client.get("/api/resume").json()
    preparation = client.get("/api/enveloppes/preparation").json()
    assert preparation["capacite_epargne_centimes"] == max(0, resume["solde_projete"])
    # Et le virement est proposé vers le seul compte d'épargne existant.
    assert preparation["compte_epargne_suggere_id"] == epargne["id"]


def test_un_mois_deficitaire_ne_propose_pas_de_placer_une_somme_negative(
    client: TestClient, session_bd: Session
) -> None:
    """Zéro dit « rien à placer », ce qui est exact. Un négatif se lirait comme une
    consigne de retirer, que rien ici ne demande."""
    session_ouverte(client, session_bd)
    compte = client.post(
        "/api/comptes", json={"nom": "Courant", "prive": True, "produit": "compte_courant"}
    ).json()
    client.post(
        "/api/operations",
        json={
            "compte_id": compte["id"],
            "libelle": "Découvert",
            "montant_centimes": -40_000,
            "date_operation": dt.date.today().isoformat(),
        },
    )

    preparation = client.get("/api/enveloppes/preparation").json()
    assert client.get("/api/resume").json()["solde_projete"] < 0, "le décor doit être déficitaire"
    assert preparation["capacite_epargne_centimes"] == 0
