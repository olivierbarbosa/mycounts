"""Destruction définitive d'un COMPTE, et ce qu'elle emporte avec elle.

Depuis le 21 août 2026 il n'existe plus de « supprimer le foyer » : arrêter de partager et
disparaître sont deux intentions distinctes, et les confondre faisait perdre son compte à
qui voulait seulement la première (ERREURS.md #044). La dissolution du partage a son
propre fichier ; ici on efface une personne.

Le test central reste `la suppression ne laisse AUCUNE ligne` : il remplit les douze tables,
supprime, puis parcourt `Base.metadata` pour exiger que chacune soit vide. C'est la seule
forme qui résiste au temps — une liste de tables écrite à la main dans le test répéterait
celle du repository, et les deux se tromperaient ensemble le jour où une treizième
apparaîtra.

Portée de cette garantie, mesurée et non supposée : elle attrape les tables dont la clé
vers le foyer est en RESTRICT, où l'oubli fait buter la suppression. Elle n'attrape PAS
une table en CASCADE oubliée dans le repository — PostgreSQL la nettoie seul, et le test
reste vert à juste titre.

Ce que ce fichier NE couvre pas : la restitution des données. Il n'y en a pas. Aucune
sauvegarde n'est prise avant l'appel, rien n'est récupérable après.
"""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi.testclient import TestClient
from mycounts.domain.import_releve import GenreCorrespondance
from mycounts.domain.securite import hacher_mot_de_passe, normaliser_courriel
from mycounts.models.auth import Foyer
from mycounts.models.base import Base
from mycounts.repository import auth as depot_auth
from mycounts.repository import budget as depot_budget
from mycounts.repository.base import Principal
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tests.integration.test_api_auth import MOT_DE_PASSE, connecter
from tests.integration.test_api_budget import session_ouverte

# Le nom que pose `creer_compte` par défaut. Il ne sert plus de confirmation — c'est
# l'ADRESSE qu'on retape pour supprimer son compte — mais reste utile pour retrouver le
# foyer en base.
NOM_FOYER = "Foyer"

# L'adresse de `session_ouverte`, et donc celle qu'il faudra retaper.
COURRIEL = "a@essai.fr"


def remplir_les_douze_tables(
    client: TestClient, session_bd: Session, principal: Principal
) -> None:
    """Pose au moins une ligne dans chaque table rattachée au foyer.

    Sans ce remplissage, le test passerait sur une base déjà vide et ne prouverait rien :
    « aucune ligne ne subsiste » est vrai d'office quand il n'y en avait aucune.
    """
    compte = client.post(
        "/api/comptes",
        json={
            "nom": "Courant",
            "prive": True,
            "produit": "compte_courant",
            "solde_ouverture_centimes": 100_000,
        },
    ).json()
    reponse_categorie = client.post(
        "/api/categories", json={"nom": "Courses", "nature": "depense", "teinte": "violet"}
    )
    assert reponse_categorie.status_code == 201, reponse_categorie.text
    categorie = reponse_categorie.json()

    client.post(
        "/api/operations",
        json={
            "compte_id": compte["id"],
            "libelle": "Un achat",
            "montant_centimes": -2_500,
            "date_operation": dt.date.today().isoformat(),
            "categorie_id": categorie["id"],
        },
    )
    client.post(
        "/api/recurrences",
        json={
            "compte_id": compte["id"],
            "libelle": "Abonnement",
            "montant_centimes": -1_000,
            "ancre": dt.date.today().isoformat(),
            "unite": "mois",
            "categorie_id": categorie["id"],
        },
    )
    client.put(
        "/api/plafonds", json={"categorie_id": categorie["id"], "montant_centimes": 30_000}
    )
    # La création d'une enveloppe renvoie la RÉPARTITION entière, pas l'enveloppe : son
    # identifiant se retrouve dans la liste.
    repartition = client.post(
        "/api/enveloppes", json={"nom": "Vacances", "cible_centimes": 50_000}
    )
    assert repartition.status_code == 201, repartition.text
    enveloppe_id = next(
        e["id"] for e in repartition.json()["enveloppes"] if e["nom"] == "Vacances"
    )
    mouvement = client.post(
        f"/api/enveloppes/{enveloppe_id}/mouvements",
        json={"type": "allocation", "montant_centimes": 5_000},
    )
    assert mouvement.status_code == 201, mouvement.text
    assert client.post("/api/auth/invitations").status_code == 201

    # La correspondance d'import n'a pas de route dédiée : elle se retient au fil d'un
    # import. On passe par le repository, qui en est l'auteur.
    depot_budget.retenir_la_correspondance(
        session_bd,
        principal,
        genre=GenreCorrespondance.LIBELLE,
        valeur="INTERMARCHE",
        categorie_id=uuid.UUID(categorie["id"]),
    )
    session_bd.commit()


def test_la_suppression_ne_laisse_AUCUNE_ligne(client: TestClient, session_bd: Session) -> None:
    principal = session_ouverte(client, session_bd)
    remplir_les_douze_tables(client, session_bd, principal)

    # Toutes pleines AVANT : c'est ce qui rend le « toutes vides après » informatif.
    avant = {
        table.name: session_bd.execute(select(func.count()).select_from(table)).scalar_one()
        for table in Base.metadata.sorted_tables
    }
    vides_avant = [nom for nom, n in avant.items() if n == 0]
    assert not vides_avant, f"le remplissage a manqué ces tables : {vides_avant}"

    # Dernier membre : son départ emporte le foyer. Personne ne resterait pour le vider.
    reponse = client.request("DELETE", "/api/auth/moi", json={"courriel": COURRIEL})
    assert reponse.status_code == 204, reponse.text

    session_bd.expire_all()
    apres = {
        table.name: session_bd.execute(select(func.count()).select_from(table)).scalar_one()
        for table in Base.metadata.sorted_tables
    }
    restantes = {nom: n for nom, n in apres.items() if n != 0}
    assert not restantes, f"des lignes ont survécu à la suppression : {restantes}"


def test_une_adresse_mal_retapee_ne_supprime_rien(
    client: TestClient, session_bd: Session
) -> None:
    """La barrière de l'adresse, prise dans le sens où elle doit tenir.

    Sans ce test, la comparaison pourrait être inversée, ou simplement absente, et le test
    précédent passerait tout aussi bien : il ne se trompe jamais d'adresse.
    """
    principal = session_ouverte(client, session_bd)
    remplir_les_douze_tables(client, session_bd, principal)

    refus = client.request("DELETE", "/api/auth/moi", json={"courriel": "b@essai.fr"})
    assert refus.status_code == 400, refus.text
    assert "ne correspond pas" in refus.json()["detail"]

    # Et rien n'a bougé : un refus qui aurait déjà effacé la moitié des tables serait pire
    # qu'une suppression franche.
    session_bd.expire_all()
    assert client.get("/api/comptes").json() != []


def test_un_membre_invite_part_sans_emporter_le_foyer(
    client: TestClient, session_bd: Session
) -> None:
    """Le sens de ce test s'est INVERSÉ le 21 août 2026.

    Il exigeait auparavant qu'un invité ne puisse pas détruire le foyer — vrai, mais la
    seule action offerte détruisait TOUT, si bien qu'un invité qui voulait simplement
    partir ne le pouvait pas. Il peut désormais supprimer son compte, et le foyer, ses
    comptes joints et ses autres membres lui survivent.
    """
    session_ouverte(client, session_bd)
    foyer_id = session_bd.execute(select(Foyer.id).where(Foyer.nom == NOM_FOYER)).scalar_one()

    # Un compte joint ouvert par le propriétaire : il doit rester après le départ.
    assert (
        client.post(
            "/api/comptes",
            json={"nom": "Le joint", "prive": False, "produit": "compte_courant"},
            headers={"X-Mycounts-Vue": "foyer"},
        ).status_code
        == 201
    )

    invite_courriel = "invite@essai.fr"
    depot_auth.creer_utilisateur(
        session_bd,
        foyer_id=foyer_id,
        courriel=normaliser_courriel(invite_courriel),
        nom_affichage="Invité",
        empreinte_mot_de_passe=hacher_mot_de_passe(MOT_DE_PASSE),
    )
    session_bd.commit()

    connecter(client, invite_courriel)
    depart = client.request("DELETE", "/api/auth/moi", json={"courriel": invite_courriel})
    assert depart.status_code == 204, depart.text

    # Le foyer est toujours là, et le propriétaire retrouve tout.
    session_bd.expire_all()
    assert session_bd.get(Foyer, foyer_id) is not None
    connecter(client, COURRIEL)
    joints = client.get("/api/comptes", headers={"X-Mycounts-Vue": "foyer"}).json()
    assert [c["nom"] for c in joints] == ["Le joint"]


def test_le_proprietaire_ne_part_pas_en_laissant_des_membres(
    client: TestClient, session_bd: Session
) -> None:
    """Refus franc plutôt qu'un foyer dont on ne sort plus.

    `Compte.proprietaire_id` pointerait vers un utilisateur effacé sur les comptes joints
    qu'il a ouverts, et plus personne ne pourrait les supprimer — la garde de
    `DELETE /api/comptes/{id}` réserve ce droit à celui qui les a ouverts, et il n'existe
    plus. Transférer la propriété est un lot à part ; laisser partir sans transfert
    fabriquerait un état sans issue.

    C'est aussi le témoin qui empêche le verrou d'être inversé : sans lui, un code qui
    refuserait TOUJOURS le départ passerait le test précédent... non, il le ferait rougir.
    Celui-ci tient l'autre bord — un code qui n'interdirait JAMAIS rien.
    """
    session_ouverte(client, session_bd)
    foyer_id = session_bd.execute(select(Foyer.id).where(Foyer.nom == NOM_FOYER)).scalar_one()

    depot_auth.creer_utilisateur(
        session_bd,
        foyer_id=foyer_id,
        courriel=normaliser_courriel("invite@essai.fr"),
        nom_affichage="Invité",
        empreinte_mot_de_passe=hacher_mot_de_passe(MOT_DE_PASSE),
    )
    session_bd.commit()

    refus = client.request("DELETE", "/api/auth/moi", json={"courriel": COURRIEL})
    assert refus.status_code == 409, refus.text
    assert "Retirez-les" in refus.json()["detail"]

    session_bd.expire_all()
    assert session_bd.get(Foyer, foyer_id) is not None
    assert client.get("/api/auth/moi").status_code == 200


def test_un_seul_proprietaire_par_foyer(client: TestClient, session_bd: Session) -> None:
    """La base refuse un second propriétaire.

    Garantie par index partiel et non par le code : deux membres capables de tout effacer,
    c'est le genre d'état qui ne se remarque qu'au moment où l'un des deux s'en sert.
    """
    import sqlalchemy.exc

    session_ouverte(client, session_bd)
    foyer_id = session_bd.execute(
        select(Foyer.id).where(Foyer.nom == NOM_FOYER)
    ).scalar_one()

    try:
        # L'index mord au FLUSH, que `creer_utilisateur` fait lui-même : entourer le seul
        # `commit()` laisserait l'erreur s'échapper et le test rougirait pour la bonne
        # raison mais au mauvais endroit.
        depot_auth.creer_utilisateur(
            session_bd,
            foyer_id=foyer_id,
            courriel=normaliser_courriel("second@essai.fr"),
            nom_affichage="Second",
            empreinte_mot_de_passe=hacher_mot_de_passe(MOT_DE_PASSE),
            est_proprietaire=True,
        )
        session_bd.commit()
    except sqlalchemy.exc.IntegrityError:
        session_bd.rollback()
    else:
        raise AssertionError("la base a accepté deux propriétaires pour le même foyer")


def test_la_session_est_fermee_par_la_suppression(
    client: TestClient, session_bd: Session
) -> None:
    """Le cookie ne doit pas survivre au compte qu'il désigne.

    Le laisser en place mènerait l'écran suivant vers une erreur au lieu de l'accueil, avec
    un jeton pointant sur un utilisateur effacé.
    """
    session_ouverte(client, session_bd)
    assert (
        client.request("DELETE", "/api/auth/moi", json={"courriel": COURRIEL}).status_code
        == 204
    )

    assert client.get("/api/auth/moi").status_code == 401
