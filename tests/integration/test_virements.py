"""Virements entre comptes du foyer, contre PostgreSQL.

Le test central est `test_un_virement_ne_touche_ni_aux_depenses_ni_au_total_du_foyer` :
c'est la mesure qui peut rendre la réponse inverse. Trois grandeurs, dont deux qui doivent
varier en sens OPPOSÉS et une qui ne doit pas bouger du tout. Si les dépenses bougeaient,
un simple virement vers l'épargne ferait sauter les plafonds du mois.
"""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from mycounts.domain.agregats import Agregat, calculer
from mycounts.domain.comptes import TypeCompte
from mycounts.repository import budget as depot
from mycounts.repository.base import Principal
from sqlalchemy.orm import Session

from tests.integration.test_api_budget import session_ouverte

AUJOURD_HUI = dt.date.today()
FIN_FENETRE = AUJOURD_HUI + dt.timedelta(days=30)


def creer_compte_api(
    client: TestClient, nom: str, *, ouverture: int = 0, type_compte: str = "courant"
) -> str:
    reponse = client.post(
        "/api/comptes",
        json={
            "nom": nom,
            "prive": True,
            "type_compte": type_compte,
            "solde_ouverture_centimes": ouverture,
        },
    )
    assert reponse.status_code == 201, reponse.text
    return str(reponse.json()["id"])


def solde_du_compte(session: Session, principal: Principal, compte_id: str) -> int:
    import uuid

    return int(
        calculer(
            Agregat.SOLDE_REEL,
            depot.operations_pour_calcul(session, principal, comptes=[uuid.UUID(compte_id)]),
            aujourd_hui=AUJOURD_HUI,
            fin_de_fenetre=FIN_FENETRE,
        )
    )


def test_un_virement_ne_touche_ni_aux_depenses_ni_au_total_du_foyer(
    client: TestClient, session_bd: Session
) -> None:
    principal = session_ouverte(client, session_bd)
    courant = creer_compte_api(client, "Courant", ouverture=100_000)
    epargne = creer_compte_api(client, "Livret A", type_compte="epargne")

    depenses_avant = int(client.get("/api/resume").json()["depenses_de_periode"])
    courant_avant = solde_du_compte(session_bd, principal, courant)
    epargne_avant = solde_du_compte(session_bd, principal, epargne)

    reponse = client.post(
        "/api/virements",
        json={
            "compte_source_id": courant,
            "compte_destination_id": epargne,
            "montant_centimes": 20_000,
            "date_operation": AUJOURD_HUI.isoformat(),
            "libelle": "Mise de côté",
        },
    )
    assert reponse.status_code == 201, reponse.text

    session_bd.expire_all()
    depenses_apres = int(client.get("/api/resume").json()["depenses_de_periode"])
    courant_apres = solde_du_compte(session_bd, principal, courant)
    epargne_apres = solde_du_compte(session_bd, principal, epargne)

    # Les deux qui bougent, en sens contraires et du même montant.
    assert courant_apres - courant_avant == -20_000
    assert epargne_apres - epargne_avant == 20_000

    # Celle qui ne bouge pas : vu du foyer, aucun argent n'a été créé ni détruit.
    assert (courant_apres + epargne_apres) == (courant_avant + epargne_avant)

    # Et celle dont dépend tout le reste : un virement n'est pas une dépense.
    assert depenses_apres == depenses_avant, (
        "un virement compté en dépense ferait sauter les plafonds du mois"
    )


def test_une_depense_du_meme_montant_bouge_bien_les_depenses(
    client: TestClient, session_bd: Session
) -> None:
    """Témoin du test précédent : sans lui, « les dépenses n'ont pas bougé » serait aussi
    bien la preuve que le virement en est exclu que celle d'un calcul cassé.
    """
    session_ouverte(client, session_bd)
    courant = creer_compte_api(client, "Courant", ouverture=100_000)

    avant = int(client.get("/api/resume").json()["depenses_de_periode"])
    reponse = client.post(
        "/api/operations",
        json={
            "compte_id": courant,
            "libelle": "Courses",
            "montant_centimes": -20_000,
            "date_operation": AUJOURD_HUI.isoformat(),
        },
    )
    assert reponse.status_code == 201, reponse.text

    apres = int(client.get("/api/resume").json()["depenses_de_periode"])
    assert apres - avant == -20_000


def test_un_virement_vers_le_meme_compte_est_refuse(
    client: TestClient, session_bd: Session
) -> None:
    session_ouverte(client, session_bd)
    courant = creer_compte_api(client, "Courant")

    reponse = client.post(
        "/api/virements",
        json={
            "compte_source_id": courant,
            "compte_destination_id": courant,
            "montant_centimes": 5_000,
            "date_operation": AUJOURD_HUI.isoformat(),
        },
    )
    assert reponse.status_code == 422, reponse.text


def test_un_montant_nul_ou_negatif_est_refuse(client: TestClient, session_bd: Session) -> None:
    """Le sens du virement se dit par les deux comptes, jamais par le signe du montant.

    Accepter un montant négatif créerait deux lectures possibles de la même demande, et
    l'une d'elles inverserait silencieusement le sens du mouvement.
    """
    session_ouverte(client, session_bd)
    source = creer_compte_api(client, "Courant")
    destination = creer_compte_api(client, "Livret A", type_compte="epargne")

    for montant in (0, -5_000):
        reponse = client.post(
            "/api/virements",
            json={
                "compte_source_id": source,
                "compte_destination_id": destination,
                "montant_centimes": montant,
                "date_operation": AUJOURD_HUI.isoformat(),
            },
        )
        assert reponse.status_code == 422, f"montant {montant} : {reponse.text}"


def test_un_compte_dun_autre_foyer_est_introuvable(
    client: TestClient, session_bd: Session
) -> None:
    """Ni virement possible, ni information sur l'existence du compte.

    La réponse est la même que pour un identifiant inventé : « introuvable ». Distinguer
    les deux dirait à qui essaie qu'un compte existe bien derrière cet identifiant.
    """
    import uuid

    session_ouverte(client, session_bd)
    courant = creer_compte_api(client, "Courant")

    reponse = client.post(
        "/api/virements",
        json={
            "compte_source_id": courant,
            "compte_destination_id": str(uuid.uuid4()),
            "montant_centimes": 5_000,
            "date_operation": AUJOURD_HUI.isoformat(),
        },
    )
    assert reponse.status_code == 404, reponse.text


def test_le_type_dun_compte_est_rendu_par_lapi(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    creer_compte_api(client, "Courant")
    creer_compte_api(client, "Livret A", type_compte="epargne")

    par_nom = {c["nom"]: c["type_compte"] for c in client.get("/api/comptes").json()}
    assert par_nom == {"Courant": TypeCompte.COURANT, "Livret A": TypeCompte.EPARGNE}


def test_lepargne_ne_gonfle_pas_le_solde_de_laccueil(
    client: TestClient, session_bd: Session
) -> None:
    """Mettre 500 € sur un livret ne doit pas enrichir le solde du quotidien.

    C'est la raison d'être du type de compte. Sans lui, l'accueil annoncerait la somme
    des deux, et la décision de dépenser se prendrait sur un chiffre faux.
    """
    session_ouverte(client, session_bd)
    creer_compte_api(client, "Courant", ouverture=100_000)
    avant = client.get("/api/resume").json()

    creer_compte_api(client, "Livret A", ouverture=50_000, type_compte="epargne")
    apres = client.get("/api/resume").json()

    assert apres["solde_reel"] == avant["solde_reel"]
    assert apres["solde_projete"] == avant["solde_projete"]

    # Et le témoin : un compte COURANT du même montant, lui, change bien le solde.
    creer_compte_api(client, "Second courant", ouverture=50_000)
    avec_courant = client.get("/api/resume").json()
    assert avec_courant["solde_reel"] - avant["solde_reel"] == 50_000


def test_lepargne_totalise_ses_comptes_et_ce_qui_y_a_ete_verse(
    client: TestClient, session_bd: Session
) -> None:
    session_ouverte(client, session_bd)
    courant = creer_compte_api(client, "Courant", ouverture=100_000)
    livret = creer_compte_api(client, "Livret A", ouverture=50_000, type_compte="epargne")

    avant = client.get("/api/epargne").json()
    assert avant["total_centimes"] == 50_000
    assert avant["verse_sur_la_periode_centimes"] == 0, (
        "un solde d'ouverture n'est pas un versement : personne ne l'a mis de côté ce mois-ci"
    )

    client.post(
        "/api/virements",
        json={
            "compte_source_id": courant,
            "compte_destination_id": livret,
            "montant_centimes": 20_000,
            "date_operation": AUJOURD_HUI.isoformat(),
        },
    )

    apres = client.get("/api/epargne").json()
    assert apres["total_centimes"] == 70_000
    assert apres["verse_sur_la_periode_centimes"] == 20_000
    assert [c["nom"] for c in apres["comptes"]] == ["Livret A"]


def test_un_virement_sortant_de_lepargne_ne_compte_pas_comme_verse(
    client: TestClient, session_bd: Session
) -> None:
    """« Versé sur la période » mesure un effort, pas un solde.

    Sans le filtre sur le sens, reprendre 200 € sur le livret ferait BAISSER le versé, et
    un aller-retour du même montant le laisserait à zéro alors que de l'argent a bien
    circulé. Pire : un total négatif se lirait comme « j'ai désépargné », ce qui est vrai,
    mais ce n'est pas la question posée par cette ligne.
    """
    session_ouverte(client, session_bd)
    courant = creer_compte_api(client, "Courant", ouverture=100_000)
    livret = creer_compte_api(client, "Livret A", ouverture=50_000, type_compte="epargne")

    for source, destination in ((courant, livret), (livret, courant)):
        client.post(
            "/api/virements",
            json={
                "compte_source_id": source,
                "compte_destination_id": destination,
                "montant_centimes": 20_000,
                "date_operation": AUJOURD_HUI.isoformat(),
            },
        )

    epargne = client.get("/api/epargne").json()
    assert epargne["verse_sur_la_periode_centimes"] == 20_000, "seul l'entrant compte"
    assert epargne["total_centimes"] == 50_000, "l'aller-retour laisse le livret intact"
