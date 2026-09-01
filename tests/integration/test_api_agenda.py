"""API des récurrences, de l'agenda et de la confirmation."""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from mycounts.domain.calendrier import aujourd_hui
from mycounts.jobs.materialisation import materialiser
from mycounts.repository.base import Principal
from sqlalchemy.orm import Session

from tests.integration.test_api_budget import creer_compte_api, session_ouverte

AUJOURD_HUI = aujourd_hui()


def creer_recurrence_api(client: TestClient, compte_id: str, ancre: dt.date, **kw: object) -> dict:  # type: ignore[type-arg]
    corps = {
        "compte_id": compte_id,
        "libelle": "Abonnement musique",
        "montant_centimes": -1099,
        "ancre": ancre.isoformat(),
        "unite": "mois",
        **kw,
    }
    reponse = client.post("/api/recurrences", json=corps)
    assert reponse.status_code == 201, reponse.text
    return dict(reponse.json())


def test_les_routes_agenda_exigent_une_session(client: TestClient) -> None:
    for methode, chemin in [
        ("GET", "/api/recurrences"),
        ("POST", "/api/recurrences"),
        ("GET", "/api/agenda"),
        ("GET", "/api/agenda/mois-en-cours"),
        ("GET", "/api/operations/a-confirmer"),
    ]:
        assert client.request(methode, chemin).status_code == 401, f"{methode} {chemin}"


def test_creer_une_recurrence_et_voir_ses_echeances(
    client: TestClient, session_bd: Session
) -> None:
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    creer_recurrence_api(client, compte_id, AUJOURD_HUI + dt.timedelta(days=3))

    agenda = client.get("/api/agenda?jours=90").json()
    assert len(agenda) >= 3, "trois mois d'échéances au moins sur 90 jours"
    assert agenda[0]["date_echeance"] == (AUJOURD_HUI + dt.timedelta(days=3)).isoformat()
    assert agenda == sorted(agenda, key=lambda e: e["date_echeance"]), "agenda non trié"


def test_une_charge_future_reduit_le_solde_projete_du_cycle(
    client: TestClient, session_bd: Session
) -> None:
    """Le calendrier doit réserver l'argent avant le prélèvement, pas le jour même."""
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    client.post(
        "/api/operations",
        json={
            "compte_id": compte_id,
            "libelle": "Salaire",
            "montant_centimes": 250000,
            "date_operation": (AUJOURD_HUI - dt.timedelta(days=5)).isoformat(),
            "est_paie": True,
        },
    )
    creer_recurrence_api(
        client,
        compte_id,
        AUJOURD_HUI + dt.timedelta(days=3),
        montant_centimes=-100000,
    )

    resume = client.get("/api/resume").json()

    assert resume["solde_reel"] == 250000
    assert resume["solde_projete"] == 150000
    assert resume["depenses_de_periode"] == 0, "une prévision n'est pas encore dépensée"


def test_lagenda_ne_montre_que_le_futur_non_materialise(
    client: TestClient, session_bd: Session
) -> None:
    """L'agenda ne montre que ce qui reste à venir.

    Une échéance déjà matérialisée est devenue une opération : la laisser dans l'agenda
    la ferait compter deux fois à l'œil du lecteur.
    """
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    creer_recurrence_api(client, compte_id, AUJOURD_HUI - dt.timedelta(days=1))

    agenda = client.get("/api/agenda?jours=90").json()
    assert all(e["date_echeance"] > AUJOURD_HUI.isoformat() for e in agenda)


def test_une_echeance_echue_ne_disparait_pas_des_ecrans(
    client: TestClient, session_bd: Session
) -> None:
    """Le trou que ce rattrapage ferme.

    Entre le jour d'une échéance et le passage du job, elle n'apparaissait ni dans
    l'agenda (qui commence aujourd'hui) ni dans les opérations (pas encore créée) : de
    l'argent invisible sur tous les écrans. La lecture matérialise donc au passage.
    """
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    creer_recurrence_api(client, compte_id, AUJOURD_HUI - dt.timedelta(days=1))

    # Aucun job lancé à la main : la seule lecture de l'agenda doit suffire.
    client.get("/api/agenda?jours=90")

    file = client.get("/api/operations/a-confirmer").json()
    assert len(file) == 1, "l'échéance d'hier doit être remontée quelque part"
    assert file[0]["date_operation"] == (AUJOURD_HUI - dt.timedelta(days=1)).isoformat()


def test_lhorizon_de_lagenda_est_borne(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    creer_recurrence_api(client, compte_id, AUJOURD_HUI, unite="jour")

    court = client.get("/api/agenda?jours=7").json()
    long = client.get("/api/agenda?jours=30").json()
    assert len(court) < len(long), "l'horizon doit réellement restreindre"
    assert client.get("/api/agenda?jours=400").status_code == 422


def test_confirmer_une_echeance_la_retire_de_la_file(
    client: TestClient, session_bd: Session
) -> None:
    principal = session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    creer_recurrence_api(client, compte_id, AUJOURD_HUI - dt.timedelta(days=1))
    materialiser(session_bd, foyer_id=principal.foyer_id)

    file = client.get("/api/operations/a-confirmer").json()
    assert len(file) == 1

    confirmee = client.post(f"/api/operations/{file[0]['id']}/confirmer")
    assert confirmee.status_code == 200
    assert confirmee.json()["etat"] == "confirmee"
    assert client.get("/api/operations/a-confirmer").json() == []


def test_confirmer_ne_change_pas_le_solde_projete(
    client: TestClient, session_bd: Session
) -> None:
    """Le témoin central, vu depuis l'API telle que l'écran l'appelle."""
    principal = session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    creer_recurrence_api(client, compte_id, AUJOURD_HUI - dt.timedelta(days=1))
    materialiser(session_bd, foyer_id=principal.foyer_id)

    avant = client.get("/api/resume").json()
    file = client.get("/api/operations/a-confirmer").json()
    client.post(f"/api/operations/{file[0]['id']}/confirmer")
    apres = client.get("/api/resume").json()

    assert apres["solde_projete"] == avant["solde_projete"], "double comptage"
    assert apres["solde_reel"] < avant["solde_reel"]
    assert apres["solde_a_confirmer"] > avant["solde_a_confirmer"]


def test_confirmer_une_operation_dun_autre_foyer_est_introuvable(
    client: TestClient, session_bd: Session
) -> None:
    from mycounts.domain.montants import Cents
    from mycounts.domain.recurrence import UniteRecurrence
    from mycounts.repository import budget as depot_budget
    from mycounts.repository import recurrences as depot_rec

    from tests.integration.test_api_auth import creer_compte as creer_utilisateur

    autre_foyer, autre_utilisateur = creer_utilisateur(session_bd, "b@essai.fr", nom_foyer="B")
    autre = Principal(utilisateur_id=autre_utilisateur, foyer_id=autre_foyer)
    compte = depot_budget.creer_compte(session_bd, autre, nom="Perso B")
    session_bd.commit()
    depot_rec.creer_recurrence(
        session_bd,
        autre,
        compte_id=compte.id,
        libelle="Abonnement B",
        montant_centimes=Cents(-500),
        ancre=AUJOURD_HUI - dt.timedelta(days=1),
        unite=UniteRecurrence.MOIS,
    )
    session_bd.commit()
    materialiser(session_bd, foyer_id=autre_foyer)
    etrangere = depot_rec.operations_a_confirmer(session_bd, autre)[0]

    session_ouverte(client, session_bd)
    assert client.post(f"/api/operations/{etrangere.id}/confirmer").status_code == 404


def test_arreter_une_recurrence_vide_lagenda_sans_toucher_a_lhistorique(
    client: TestClient, session_bd: Session
) -> None:
    principal = session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    recurrence = creer_recurrence_api(client, compte_id, AUJOURD_HUI - dt.timedelta(days=1))
    materialiser(session_bd, foyer_id=principal.foyer_id)

    operations_avant = len(client.get("/api/operations?periode_courante=false").json())
    assert client.delete(f"/api/recurrences/{recurrence['id']}").status_code == 204

    assert client.get("/api/agenda?jours=90").json() == []
    assert len(client.get("/api/operations?periode_courante=false").json()) == operations_avant, (
        "arrêter une récurrence ne doit pas réécrire le passé"
    )


def test_une_recurrence_a_montant_nul_est_refusee(
    client: TestClient, session_bd: Session
) -> None:
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    reponse = client.post(
        "/api/recurrences",
        json={
            "compte_id": compte_id,
            "libelle": "Rien",
            "montant_centimes": 0,
            "ancre": AUJOURD_HUI.isoformat(),
            "unite": "mois",
        },
    )
    assert reponse.status_code == 422


def test_une_fin_anterieure_a_lancre_est_refusee(
    client: TestClient, session_bd: Session
) -> None:
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    reponse = client.post(
        "/api/recurrences",
        json={
            "compte_id": compte_id,
            "libelle": "Incoherent",
            "montant_centimes": -100,
            "ancre": AUJOURD_HUI.isoformat(),
            "unite": "mois",
            "fin": (AUJOURD_HUI - dt.timedelta(days=1)).isoformat(),
        },
    )
    assert reponse.status_code == 422


# --- Modification d'un prélèvement -----------------------------------------------


def test_modifier_un_prelevement(client: TestClient, session_bd: Session) -> None:
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    recurrence = creer_recurrence_api(client, compte_id, AUJOURD_HUI + dt.timedelta(days=3))

    reponse = client.patch(
        f"/api/recurrences/{recurrence['id']}",
        json={"libelle": "Abonnement vidéo", "montant_centimes": -1599, "intervalle": 3},
    )
    assert reponse.status_code == 200
    assert reponse.json()["libelle"] == "Abonnement vidéo"
    assert reponse.json()["montant_centimes"] == -1599
    assert reponse.json()["intervalle"] == 3


def test_retirer_categorie_et_fin_dun_prelevement(
    client: TestClient, session_bd: Session
) -> None:
    """Un `null` explicite efface ; omettre le champ conserve sa valeur."""
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    categorie = client.post(
        "/api/categories",
        json={"nom": "Abonnements", "nature": "depense", "teinte": "cyan"},
    ).json()
    recurrence = creer_recurrence_api(
        client,
        compte_id,
        AUJOURD_HUI,
        categorie_id=categorie["id"],
        fin=(AUJOURD_HUI + dt.timedelta(days=90)).isoformat(),
    )

    inchangee = client.patch(
        f"/api/recurrences/{recurrence['id']}", json={"libelle": "Toujours là"}
    ).json()
    assert inchangee["categorie_id"] == categorie["id"]
    assert inchangee["fin"] is not None

    retiree = client.patch(
        f"/api/recurrences/{recurrence['id']}",
        json={"categorie_id": None, "fin": None},
    )
    assert retiree.status_code == 200, retiree.text
    assert retiree.json()["categorie_id"] is None
    assert retiree.json()["fin"] is None


def test_modifier_ne_reecrit_pas_lhistorique(client: TestClient, session_bd: Session) -> None:
    """Un abonnement dont le tarif augmente n'a pas coûté davantage les mois précédents.

    Réécrire les opérations déjà matérialisées ferait changer des soldes de mois clos.
    """
    principal = session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    recurrence = creer_recurrence_api(client, compte_id, AUJOURD_HUI - dt.timedelta(days=1))
    materialiser(session_bd, foyer_id=principal.foyer_id)

    passees_avant = client.get("/api/operations?periode_courante=false").json()
    montant_avant = passees_avant[0]["montant_centimes"]

    client.patch(f"/api/recurrences/{recurrence['id']}", json={"montant_centimes": -9999})

    passees_apres = client.get("/api/operations?periode_courante=false").json()
    assert passees_apres[0]["montant_centimes"] == montant_avant, (
        "le prélèvement déjà passé ne doit pas changer de montant"
    )


def test_la_modification_change_les_echeances_futures(
    client: TestClient, session_bd: Session
) -> None:
    """Volet inverse : sans lui, une modification qui ne changerait RIEN passerait le
    test précédent."""
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    recurrence = creer_recurrence_api(client, compte_id, AUJOURD_HUI + dt.timedelta(days=3))

    avant = client.get("/api/agenda?jours=90").json()
    client.patch(f"/api/recurrences/{recurrence['id']}", json={"montant_centimes": -9999})
    apres = client.get("/api/agenda?jours=90").json()

    assert all(e["montant_centimes"] == -1099 for e in avant)
    assert all(e["montant_centimes"] == -9999 for e in apres)


def test_modifier_un_prelevement_dun_autre_foyer_est_introuvable(
    client: TestClient, session_bd: Session
) -> None:
    from mycounts.domain.montants import Cents
    from mycounts.domain.recurrence import UniteRecurrence
    from mycounts.repository import budget as depot_budget
    from mycounts.repository import recurrences as depot_rec

    from tests.integration.test_api_auth import creer_compte as creer_utilisateur

    autre_foyer, autre_utilisateur = creer_utilisateur(session_bd, "b@essai.fr", nom_foyer="B")
    autre = Principal(utilisateur_id=autre_utilisateur, foyer_id=autre_foyer)
    compte = depot_budget.creer_compte(session_bd, autre, nom="Perso B")
    session_bd.commit()
    etrangere = depot_rec.creer_recurrence(
        session_bd,
        autre,
        compte_id=compte.id,
        libelle="Abonnement B",
        montant_centimes=Cents(-500),
        ancre=AUJOURD_HUI,
        unite=UniteRecurrence.MOIS,
    )
    session_bd.commit()

    session_ouverte(client, session_bd)
    reponse = client.patch(
        f"/api/recurrences/{etrangere.id}", json={"montant_centimes": -100}
    )
    assert reponse.status_code == 404


def test_un_montant_nul_en_modification_est_refuse(
    client: TestClient, session_bd: Session
) -> None:
    session_ouverte(client, session_bd)
    compte_id = creer_compte_api(client)
    recurrence = creer_recurrence_api(client, compte_id, AUJOURD_HUI)
    reponse = client.patch(
        f"/api/recurrences/{recurrence['id']}", json={"montant_centimes": 0}
    )
    assert reponse.status_code == 422


def test_les_bornes_du_mois_sont_le_mois_civil_pas_la_periode_de_paie(
    client: TestClient, session_bd: Session
) -> None:
    """Le premier au dernier jour du mois, bornes incluses.

    Le témoin porte sur ce qui distingue les deux notions : une période budgétaire va de
    paie à paie, donc elle ne commence presque jamais un 1er et ne finit presque jamais un
    dernier jour du mois. Un test qui vérifierait seulement « debut <= fin » passerait avec
    l'une comme avec l'autre et ne prouverait rien.
    """
    session_ouverte(client, session_bd)
    reponse = client.get("/api/agenda/mois-en-cours")
    assert reponse.status_code == 200, reponse.text
    debut = dt.date.fromisoformat(reponse.json()["debut"])
    fin = dt.date.fromisoformat(reponse.json()["fin"])

    assert debut.day == 1
    assert (debut.year, debut.month) == (fin.year, fin.month)
    # Dernier jour du mois : le lendemain bascule sur le mois suivant.
    assert (fin + dt.timedelta(days=1)).month != fin.month
    # Et le mois est bien celui d'aujourd'hui, pas un voisin.
    assert (debut.year, debut.month) == (AUJOURD_HUI.year, AUJOURD_HUI.month)
