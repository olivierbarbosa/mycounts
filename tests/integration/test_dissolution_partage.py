"""Arrêt du partage : les comptes joints s'en vont, personne n'est déconnecté.

Le test central est `dissoudre ne touche ni au compte ni aux comptes personnels` : c'est
la plainte exacte d'Olivier le 21 août 2026 — « pourquoi quand je supprime un foyer ça me
déconnecte ». Le foyer est le conteneur racine de tout en base, y compris des comptes
personnels ; c'est un fait de schéma, et l'ancienne action le faisait payer à
l'utilisateur en effaçant son identité avec le partage (ERREURS.md #044).

Ce que ce fichier NE couvre pas : le départ d'un membre, qui vit dans
`test_suppression_foyer.py`. Dissoudre ne retire personne du foyer — les membres restent
membres, avec leurs comptes personnels intacts.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from mycounts.domain.calendrier import aujourd_hui
from mycounts.domain.securite import hacher_mot_de_passe, normaliser_courriel
from mycounts.models.auth import Foyer
from mycounts.repository import auth as depot_auth
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.integration.test_api_auth import MOT_DE_PASSE
from tests.integration.test_api_budget import connecter_avec_mfa, session_ouverte

NOM_FOYER = "Foyer"
COURRIEL = "a@essai.fr"


def creer_joint(client: TestClient, nom: str, ouverture: int = 0) -> dict:  # type: ignore[type-arg]
    reponse = client.post(
        "/api/comptes",
        json={
            "nom": nom,
            "prive": False,
            "produit": "compte_courant",
            "solde_ouverture_centimes": ouverture,
        },
        headers={"X-Mycounts-Vue": "foyer"},
    )
    assert reponse.status_code == 201, reponse.text
    return dict(reponse.json())


def test_dissoudre_ne_touche_ni_au_compte_ni_aux_comptes_personnels(
    client: TestClient, session_bd: Session
) -> None:
    """La mesure qui peut rendre la réponse inverse : deux choses, dont UNE doit changer.

    Les comptes joints disparaissent — c'est ce qui est demandé. Le compte personnel, la
    session et l'utilisateur ne bougent pas — c'est ce que l'ancienne action détruisait au
    passage. Ne vérifier que la première moitié laisserait passer exactement le défaut
    corrigé.
    """
    session_ouverte(client, session_bd)
    foyer_id = session_bd.execute(select(Foyer.id).where(Foyer.nom == NOM_FOYER)).scalar_one()

    perso = client.post(
        "/api/comptes",
        json={"nom": "Mon perso", "prive": True, "produit": "compte_courant"},
    ).json()
    creer_joint(client, "Le joint", ouverture=5_000)

    reponse = client.delete("/api/auth/foyer/partage")
    assert reponse.status_code == 204, reponse.text

    session_bd.expire_all()
    # Ce qui DOIT changer.
    assert client.get("/api/comptes", headers={"X-Mycounts-Vue": "foyer"}).json() == []
    # Ce qui ne doit PAS changer.
    assert [c["id"] for c in client.get("/api/comptes").json()] == [perso["id"]]
    assert client.get("/api/auth/moi").status_code == 200
    assert session_bd.get(Foyer, foyer_id) is not None


def test_la_dissolution_ne_deconnecte_pas(client: TestClient, session_bd: Session) -> None:
    """Dit séparément parce que c'est la plainte, mot pour mot.

    Le test précédent l'attrape déjà par `GET /auth/moi`, mais une assertion noyée parmi
    cinq autres se supprime un jour sans qu'on voie ce qu'on retire.
    """
    session_ouverte(client, session_bd)
    creer_joint(client, "Le joint")

    assert client.delete("/api/auth/foyer/partage").status_code == 204
    apres = client.get("/api/auth/moi")
    assert apres.status_code == 200, "la dissolution a fermé la session"
    assert apres.json()["courriel"] == COURRIEL


def test_un_compte_joint_qui_porte_de_vraies_operations_bloque(
    client: TestClient, session_bd: Session
) -> None:
    """Même règle que pour un compte seul : ce sont les mois clos qu'on protège.

    Le refus NOMME les comptes qui bloquent. « C'est refusé » sans dire par quoi oblige à
    les essayer un par un, sur un écran qui n'en liste aucun.
    """
    session_ouverte(client, session_bd)
    joint = creer_joint(client, "Le joint")
    client.post(
        "/api/operations",
        json={
            "compte_id": joint["id"],
            "libelle": "Une dépense",
            "montant_centimes": -2_500,
            "date_operation": aujourd_hui().isoformat(),
        },
        headers={"X-Mycounts-Vue": "foyer"},
    )

    refus = client.delete("/api/auth/foyer/partage")
    assert refus.status_code == 409, refus.text
    assert "Le joint" in refus.json()["detail"], "le refus doit nommer le compte qui bloque"

    session_bd.expire_all()
    joints = client.get("/api/comptes", headers={"X-Mycounts-Vue": "foyer"}).json()
    assert [c["nom"] for c in joints] == ["Le joint"], "un refus ne doit rien avoir effacé"


def test_un_compte_joint_qui_ne_porte_que_son_amorcage_se_dissout(
    client: TestClient, session_bd: Session
) -> None:
    """L'autre bord, sans lequel un refus SYSTÉMATIQUE passerait le test précédent.

    Un amorçage ne clôt aucun mois : l'emporter ne change aucun total passé. Même
    raisonnement que pour la suppression d'un compte seul (ERREURS.md #042).
    """
    session_ouverte(client, session_bd)
    creer_joint(client, "A peine ouvert", ouverture=8_000)

    assert client.delete("/api/auth/foyer/partage").status_code == 204
    session_bd.expire_all()
    assert client.get("/api/comptes", headers={"X-Mycounts-Vue": "foyer"}).json() == []


def test_un_membre_invite_ne_peut_pas_dissoudre_le_partage(
    client: TestClient, session_bd: Session
) -> None:
    """Un compte joint contient l'argent des DEUX membres.

    La visibilité ne vaut pas permission — la même règle que pour la suppression d'un
    compte joint pris isolément, et pour la même raison.
    """
    session_ouverte(client, session_bd)
    foyer_id = session_bd.execute(select(Foyer.id).where(Foyer.nom == NOM_FOYER)).scalar_one()
    creer_joint(client, "Le joint")

    invite = "invite@essai.fr"
    depot_auth.creer_utilisateur(
        session_bd,
        foyer_id=foyer_id,
        courriel=normaliser_courriel(invite),
        nom_affichage="Invité",
        empreinte_mot_de_passe=hacher_mot_de_passe(MOT_DE_PASSE),
        courriel_verifie=True,
    )
    session_bd.commit()
    connecter_avec_mfa(client, session_bd, invite)

    refus = client.delete("/api/auth/foyer/partage")
    assert refus.status_code == 403, refus.text
    assert "propriétaire" in refus.json()["detail"]

    session_bd.expire_all()
    joints = client.get("/api/comptes", headers={"X-Mycounts-Vue": "foyer"}).json()
    assert [c["nom"] for c in joints] == ["Le joint"]


def test_dissoudre_sans_aucun_compte_joint_le_dit(
    client: TestClient, session_bd: Session
) -> None:
    """« Rien à faire » et « c'est fait » sont deux réponses différentes.

    Répondre 204 sur un foyer sans partage laisserait croire qu'on vient de détruire
    quelque chose — l'écran afficherait un succès pour une action qui n'a rien touché.
    """
    session_ouverte(client, session_bd)

    reponse = client.delete("/api/auth/foyer/partage")
    assert reponse.status_code == 409, reponse.text
    assert "aucun compte joint" in reponse.json()["detail"]
