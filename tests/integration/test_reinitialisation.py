"""Le script de remise à zéro tient-il ce qu'il annonce ?

Il promettait « un compte » tout en n'en supprimant aucun. L'écart est resté invisible
tant qu'aucun test ne créait de second compte ; les tests d'épargne en créent un par cas,
et la page en affichait quatre — dont deux d'une exécution précédente.

Un script dont l'en-tête décrit un état garanti a besoin d'un test qui le vérifie, sans
quoi cet en-tête n'est qu'une intention.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from mycounts.domain.comptes import TypeCompte
from mycounts.models.budget import Compte
from mycounts.repository import auth as depot_auth
from mycounts.repository import budget as depot
from mycounts.repository import espaces as depot_espaces
from mycounts.repository.base import Principal
from sqlalchemy import select
from sqlalchemy.orm import Session

RACINE = Path(__file__).resolve().parents[2]
COURRIEL = "remise-a-zero@mycounts-demo.fr"


def test_la_remise_a_zero_ne_laisse_quun_seul_compte(session_bd: Session) -> None:
    from tests.integration.test_api_auth import creer_compte as creer_utilisateur

    foyer_id, utilisateur_id = creer_utilisateur(session_bd, COURRIEL)
    principal = Principal(utilisateur_id=utilisateur_id, foyer_id=foyer_id)
    for nom in ("Courant", "Livret A", "Livret jeune"):
        depot.creer_compte(
            session_bd,
            principal,
            nom=nom,
            type_compte=TypeCompte.EPARGNE if nom != "Courant" else TypeCompte.COURANT,
        )
    session_bd.commit()

    avant = session_bd.execute(select(Compte).where(Compte.foyer_id == foyer_id)).scalars().all()
    assert len(avant) == 3, "le témoin lui-même doit partir de plusieurs comptes"

    resultat = subprocess.run(
        [sys.executable, "-m", "scripts.reinitialiser_foyer_essai"],
        cwd=RACINE,
        env={**os.environ, "MYCOUNTS_COURRIEL_TEST": COURRIEL},
        capture_output=True,
        text=True,
    )
    assert resultat.returncode == 0, resultat.stderr

    session_bd.expire_all()
    apres = session_bd.execute(select(Compte).where(Compte.foyer_id == foyer_id)).scalars().all()
    assert len(apres) == 1, f"le script annonce un seul compte, il en reste {len(apres)}"
    assert apres[0].type_compte == TypeCompte.COURANT


def test_la_remise_a_zero_pose_le_compte_dans_lespace_personnel(session_bd: Session) -> None:
    """Le compte de démonstration a un espace personnel ET un foyer, comme tout compte
    créé par `creer_premier_compte`. L'application ouvre le personnel : un compte
    recréé dans le foyer laissait toute la suite sur l'écran d'amorçage."""
    from tests.integration.test_api_auth import creer_compte as creer_utilisateur

    foyer_id, utilisateur_id = creer_utilisateur(session_bd, COURRIEL)
    utilisateur = depot_auth.utilisateur_par_id(session_bd, utilisateur_id)
    assert utilisateur is not None
    personnel, _ = depot_espaces.creer_espace_personnel(session_bd, utilisateur)
    # Un compte dans le foyer, aucun dans le personnel : l'état où l'ancien script laissait
    # la suite, et où il aurait rendu « un compte » sans que ce soit le bon.
    depot.creer_compte(
        session_bd, Principal(utilisateur_id=utilisateur_id, foyer_id=foyer_id), nom="Joint"
    )
    session_bd.commit()

    resultat = subprocess.run(
        [sys.executable, "-m", "scripts.reinitialiser_foyer_essai"],
        cwd=RACINE,
        env={**os.environ, "MYCOUNTS_COURRIEL_TEST": COURRIEL},
        capture_output=True,
        text=True,
    )
    assert resultat.returncode == 0, resultat.stderr

    session_bd.expire_all()
    restants = (
        session_bd.execute(select(Compte).where(Compte.espace_id.in_([foyer_id, personnel.id])))
        .scalars()
        .all()
    )
    assert [c.espace_id for c in restants] == [personnel.id], (
        "un seul compte, et dans l'espace personnel — celui que l'application ouvre"
    )


def test_la_remise_a_zero_refuse_une_adresse_qui_nest_pas_de_demonstration() -> None:
    """Une commande qui vide des tables doit être incapable de viser autre chose.

    Le test porte sur le refus ET sur le code de sortie : un script qui afficherait un
    avertissement puis effacerait quand même passerait un contrôle qui ne lit que la
    sortie standard.
    """
    resultat = subprocess.run(
        [sys.executable, "-m", "scripts.reinitialiser_foyer_essai"],
        cwd=RACINE,
        env={**os.environ, "MYCOUNTS_COURRIEL_TEST": "vrai.utilisateur@exemple.fr"},
        capture_output=True,
        text=True,
    )
    assert resultat.returncode == 1
    assert "Refus" in resultat.stderr
