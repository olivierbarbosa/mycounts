"""Isolation et cycle de vie des espaces financiers."""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from fastapi.testclient import TestClient
from mycounts.domain.agregats import EtatOperation
from mycounts.domain.espaces import RoleEspace, TypeEspace
from mycounts.domain.montants import Cents
from mycounts.domain.securite import hacher_mot_de_passe
from mycounts.models.budget import Operation
from mycounts.repository import auth as depot_auth
from mycounts.repository import budget as depot_budget
from mycounts.repository import espaces as depot
from mycounts.repository.base import Principal
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

MOT_DE_PASSE = "correct cheval batterie agrafe"


def _identite(session: Session, courriel: str, nom: str) -> tuple[Principal, Principal]:
    foyer = depot_auth.creer_foyer(session, f"Ancien {nom}")
    utilisateur = depot_auth.creer_utilisateur(
        session,
        foyer_id=foyer.id,
        courriel=courriel,
        nom_affichage=nom,
        empreinte_mot_de_passe=hacher_mot_de_passe(MOT_DE_PASSE),
        est_proprietaire=True,
    )
    espace, _ = depot.creer_espace_personnel(session, utilisateur)
    depot_budget.creer_categories_initiales(session, espace.id)
    session.commit()
    return (
        Principal(
            utilisateur_id=utilisateur.id,
            espace_id=espace.id,
            foyer_id=espace.id,
            role=RoleEspace.PROPRIETAIRE,
            type_espace=TypeEspace.PERSONNEL,
        ),
        Principal(
            utilisateur_id=utilisateur.id,
            espace_id=foyer.id,
            foyer_id=foyer.id,
            role=RoleEspace.PROPRIETAIRE,
            type_espace=TypeEspace.FOYER,
        ),
    )


def _connecter(client: TestClient, courriel: str) -> None:
    reponse = client.post(
        "/api/auth/connexion",
        json={"courriel": courriel, "mot_de_passe": MOT_DE_PASSE},
    )
    assert reponse.status_code == 200, reponse.text


def test_un_uuid_non_autorise_ne_lit_pas_lespace_personnel(
    client: TestClient, session_bd: Session
) -> None:
    alice, _ = _identite(session_bd, "alice@essai.fr", "Alice")
    bob, _ = _identite(session_bd, "bob@essai.fr", "Bob")
    depot_budget.creer_compte(session_bd, alice, nom="Personnel Alice")
    depot_budget.creer_compte(session_bd, bob, nom="Secret Bob")
    session_bd.commit()
    _connecter(client, "alice@essai.fr")

    reponse = client.get("/api/comptes", headers={"X-Mycounts-Espace": str(bob.espace_id)})
    inconnue = client.get(
        "/api/comptes", headers={"X-Mycounts-Espace": str(uuid.uuid4())}
    )

    assert reponse.status_code == 404
    assert reponse.json()["detail"] == "Espace indisponible."
    assert inconnue.status_code == 404
    assert inconnue.json() == reponse.json()


def test_un_uuid_non_autorise_necrit_pas_dans_lespace_personnel(
    client: TestClient, session_bd: Session
) -> None:
    alice, _ = _identite(session_bd, "alice@essai.fr", "Alice")
    bob, _ = _identite(session_bd, "bob@essai.fr", "Bob")
    depot_budget.creer_compte(session_bd, alice, nom="Personnel Alice")
    session_bd.commit()
    _connecter(client, "alice@essai.fr")

    reponse = client.post(
        "/api/comptes",
        headers={"X-Mycounts-Espace": str(bob.espace_id)},
        json={"nom": "Ne doit jamais exister", "prive": True},
    )

    assert reponse.status_code == 404
    assert [compte.nom for compte in depot_budget.comptes_visibles(session_bd, alice)] == [
        "Personnel Alice"
    ]


def test_un_identifiant_espace_malforme_est_refuse_sans_repli(
    client: TestClient, session_bd: Session
) -> None:
    alice, _ = _identite(session_bd, "alice@essai.fr", "Alice")
    depot_budget.creer_compte(session_bd, alice, nom="Personnel Alice")
    session_bd.commit()
    _connecter(client, "alice@essai.fr")

    reponse = client.get("/api/comptes", headers={"X-Mycounts-Espace": "pas-un-uuid"})

    assert reponse.status_code == 404


def test_lancienne_invitation_ne_peut_pas_partager_lespace_personnel(
    client: TestClient, session_bd: Session
) -> None:
    alice, _ = _identite(session_bd, "alice@essai.fr", "Alice")
    _connecter(client, "alice@essai.fr")

    reponse = client.post(
        "/api/auth/invitations",
        headers={"X-Mycounts-Espace": str(alice.espace_id)},
    )

    assert reponse.status_code == 410


def test_un_compte_peut_rejoindre_plusieurs_foyers_et_les_donnees_restent_isolees(
    client: TestClient, session_bd: Session
) -> None:
    alice, _ = _identite(session_bd, "alice@essai.fr", "Alice")
    bob, _ = _identite(session_bd, "bob@essai.fr", "Bob")
    _connecter(client, "alice@essai.fr")

    cree = client.post(
        "/api/espaces",
        headers={"X-Mycounts-Espace": str(alice.espace_id)},
        json={"nom": "Maison"},
    )
    assert cree.status_code == 201, cree.text
    foyer_id = cree.json()["id"]
    invitation = client.post(
        "/api/espaces/invitations",
        headers={"X-Mycounts-Espace": foyer_id},
        json={"courriel": "bob@essai.fr", "role": "membre"},
    )
    assert invitation.status_code == 201, invitation.text
    client.post("/api/auth/deconnexion")
    _connecter(client, "bob@essai.fr")

    acceptee = client.post(
        "/api/espaces/invitations/accepter",
        headers={"X-Mycounts-Espace": str(bob.espace_id)},
        json={"jeton": invitation.json()["jeton"]},
    )
    assert acceptee.status_code == 200, acceptee.text
    liste = client.get("/api/espaces").json()
    assert foyer_id in {espace["id"] for espace in liste}

    # Le compte du foyer est visible seulement avec son UUID explicite.
    bob_foyer = depot.principal_pour(
        session_bd,
        utilisateur_id=bob.utilisateur_id,
        espace_id=acceptee.json()["id"],
    )
    assert bob_foyer is not None
    depot_budget.creer_compte(session_bd, bob_foyer, nom="Joint Maison", prive=False)
    session_bd.commit()
    assert [
        c["nom"] for c in client.get("/api/comptes", headers={"X-Mycounts-Espace": foyer_id}).json()
    ] == ["Joint Maison"]
    assert (
        client.get("/api/comptes", headers={"X-Mycounts-Espace": str(bob.espace_id)}).json() == []
    )


def test_transfert_puis_depart_ne_touche_pas_les_espaces_personnels(
    client: TestClient, session_bd: Session
) -> None:
    alice, _ = _identite(session_bd, "alice@essai.fr", "Alice")
    bob, _ = _identite(session_bd, "bob@essai.fr", "Bob")
    espace, _ = depot.creer_foyer(session_bd, alice, nom="Famille")
    invitation = depot.creer_invitation(
        session_bd,
        Principal(
            utilisateur_id=alice.utilisateur_id,
            espace_id=espace.id,
            role=RoleEspace.PROPRIETAIRE,
            type_espace=TypeEspace.FOYER,
        ),
        courriel="bob@essai.fr",
        role=RoleEspace.MEMBRE,
        empreinte_jeton="a" * 64,
        expire_le=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
    )
    depot.accepter_invitation(
        session_bd,
        invitation,
        utilisateur_id=bob.utilisateur_id,
        a_l_instant=dt.datetime.now(dt.UTC),
    )
    session_bd.commit()
    _connecter(client, "alice@essai.fr")

    transfert = client.post(
        "/api/espaces/propriete",
        headers={"X-Mycounts-Espace": str(espace.id)},
        json={"utilisateur_id": str(bob.utilisateur_id)},
    )
    assert transfert.status_code == 204, transfert.text
    depart = client.delete(
        "/api/espaces/membres/moi",
        headers={"X-Mycounts-Espace": str(espace.id)},
    )
    assert depart.status_code == 204, depart.text
    assert depot.espace_personnel_de(session_bd, alice.utilisateur_id) is not None
    assert (
        depot.appartenance_active(
            session_bd, utilisateur_id=alice.utilisateur_id, espace_id=espace.id
        )
        is None
    )
    assert depot.nombre_proprietaires(session_bd, espace.id) == 1

    # L'UUID révoqué est bien refusé, mais la liste sans périmètre reste joignable : le
    # frontend peut oublier son localStorage périmé et revenir au personnel.
    assert client.get(
        "/api/espaces", headers={"X-Mycounts-Espace": str(espace.id)}
    ).status_code == 404
    liste = client.get("/api/espaces")
    assert liste.status_code == 200
    assert str(alice.espace_id) in {item["id"] for item in liste.json()}
    assert str(espace.id) not in {item["id"] for item in liste.json()}


def test_la_base_refuse_un_lien_financier_inter_espace(session_bd: Session) -> None:
    alice, _ = _identite(session_bd, "alice@essai.fr", "Alice")
    bob, _ = _identite(session_bd, "bob@essai.fr", "Bob")
    compte_bob = depot_budget.creer_compte(session_bd, bob, nom="Bob")
    session_bd.commit()

    session_bd.add(
        Operation(
            espace_id=alice.espace_id,
            compte_id=compte_bob.id,
            cree_par_id=alice.utilisateur_id,
            libelle="Lien interdit",
            montant_centimes=Cents(-100),
            date_operation=dt.date(2026, 8, 24),
            etat=EtatOperation.CONFIRMEE,
        )
    )
    with pytest.raises(IntegrityError):
        session_bd.flush()
    session_bd.rollback()


def test_supprimer_le_foyer_historique_preserve_identite_et_espace_personnel(
    client: TestClient, session_bd: Session
) -> None:
    personnel, foyer = _identite(session_bd, "alice@essai.fr", "Alice")
    depot_budget.creer_categories_initiales(session_bd, foyer.espace_id)
    depot_budget.creer_compte(session_bd, foyer, nom="Compte commun", prive=False)
    session_bd.commit()
    _connecter(client, "alice@essai.fr")

    reponse = client.request(
        "DELETE",
        f"/api/espaces/{foyer.espace_id}",
        headers={"X-Mycounts-Espace": str(foyer.espace_id)},
        json={"nom": "Ancien Alice"},
    )

    assert reponse.status_code == 204, reponse.text
    assert depot_auth.utilisateur_par_id(session_bd, personnel.utilisateur_id) is not None
    assert depot.espace_personnel_de(session_bd, personnel.utilisateur_id) is not None
    assert (
        depot.appartenance_active(
            session_bd,
            utilisateur_id=personnel.utilisateur_id,
            espace_id=foyer.espace_id,
        )
        is None
    )
