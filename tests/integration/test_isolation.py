"""Isolation entre foyers.

Deux contrôles complémentaires, dont aucun ne suffit seul :
  1. structurel — toute route non publique exige une session ;
  2. de données — une requête du repository ne renvoie jamais un autre foyer.

Le garde-fou statique `scripts/verifier_scope_repository.py` prouve qu'aucune requête
n'est écrite hors du repository ; il ne prouve pas que celles du repository appliquent
correctement leur périmètre. C'est ce fichier qui s'en charge.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from mycounts.api.app import app
from mycounts.repository import auth as depot
from mycounts.repository.base import Principal
from sqlalchemy.orm import Session

from tests.integration.test_api_auth import creer_compte

# Routes délibérément accessibles sans session. Toute NOUVELLE route est privée par
# défaut : l'ajouter ici est un geste explicite, qui se voit en revue.
ROUTES_PUBLIQUES = {
    ("/health", "GET"),
    ("/auth/connexion", "POST"),
    ("/auth/rejoindre", "POST"),
}


def routes_privees() -> list[tuple[str, str]]:
    """Toutes les routes exposées, moins les publiques déclarées.

    L'énumération part du schéma OpenAPI et non de `app.routes` : FastAPI n'aplatit pas
    `include_router`, et une exploration des attributs internes casserait à la première
    montée de version. Le schéma, lui, est le contrat public — et c'est exactement la
    liste de ce qui est réellement joignable.
    """
    schema: dict[str, Any] = app.openapi()
    return [
        (chemin, methode.upper())
        for chemin, operations in schema["paths"].items()
        for methode in operations
        if (chemin, methode.upper()) not in ROUTES_PUBLIQUES
    ]


def test_il_existe_bien_des_routes_privees() -> None:
    """Témoin de l'énumération elle-même.

    Ce test a déjà servi : une première version ne lisait que `app.routes` et ratait
    toutes les routes du routeur /auth. Le test d'isolation passait alors sur une liste
    vide, c'est-à-dire sans rien vérifier. Voir ERREURS.md #005.
    """
    trouvees = routes_privees()
    assert trouvees, "aucune route privée trouvée : l'énumération est cassée"
    # Les routes d'authentification connues doivent y figurer : une énumération qui ne
    # descendrait plus dans les routeurs inclus redeviendrait silencieusement vide.
    for attendue in [("/auth/moi", "GET"), ("/auth/invitations", "POST"),
                     ("/auth/deconnexion", "POST")]:
        assert attendue in trouvees, f"{attendue} absente de l'énumération"


def test_toute_route_privee_exige_une_session(client: TestClient) -> None:
    """Itère sur les routes RÉELLEMENT enregistrées.

    Une route ajoutée sans authentification fait échouer ce test sans que personne ait à
    penser à l'ajouter ici.
    """
    for chemin, methode in routes_privees():
        reponse = client.request(methode, chemin)
        assert reponse.status_code == 401, f"{methode} {chemin} accessible sans session"


def test_les_membres_d_un_foyer_ne_voient_pas_l_autre(session_bd: Session) -> None:
    foyer_a, utilisateur_a = creer_compte(session_bd, "a@essai.fr", nom_foyer="A", nom="Alice")
    foyer_b, utilisateur_b = creer_compte(session_bd, "b@essai.fr", nom_foyer="B", nom="Bruno")

    vus_par_a = depot.membres_du_foyer(
        session_bd, Principal(utilisateur_id=utilisateur_a, foyer_id=foyer_a)
    )
    vus_par_b = depot.membres_du_foyer(
        session_bd, Principal(utilisateur_id=utilisateur_b, foyer_id=foyer_b)
    )

    assert [u.courriel for u in vus_par_a] == ["a@essai.fr"]
    assert [u.courriel for u in vus_par_b] == ["b@essai.fr"]


def test_le_temoin_de_l_isolation(session_bd: Session) -> None:
    """Contrôle inverse : les deux comptes existent bien dans la même base.

    Sans lui, une requête qui ne renverrait JAMAIS rien passerait le test précédent.
    """
    foyer_a, utilisateur_a = creer_compte(session_bd, "a@essai.fr", nom_foyer="A")
    creer_compte(session_bd, "b@essai.fr", nom_foyer="B")

    assert depot.utilisateur_par_courriel(session_bd, "b@essai.fr") is not None
    assert len(depot.membres_du_foyer(
        session_bd, Principal(utilisateur_id=utilisateur_a, foyer_id=foyer_a)
    )) == 1
