"""Crée le foyer et le premier compte. Aucune inscription publique n'existe.

Le mot de passe n'est jamais passé en argument de ligne de commande : il finirait dans
l'historique du shell et dans la liste des processus. Il est demandé en saisie masquée,
ou lu dans la variable d'environnement MYCOUNTS_MOT_DE_PASSE_INITIAL pour un usage
automatisé.

    python -m scripts.creer_premier_compte "Foyer Barbosa" olivier@exemple.fr "Olivier"
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from mycounts.domain.securite import (
    MotDePasseTropCourt,
    hacher_mot_de_passe,
    normaliser_courriel,
)
from mycounts.repository import auth as depot
from mycounts.repository.base import fabrique_de_sessions


def lire_mot_de_passe() -> str:
    depuis_environnement = os.environ.get("MYCOUNTS_MOT_DE_PASSE_INITIAL")
    if depuis_environnement:
        return depuis_environnement
    premier = getpass.getpass("Mot de passe : ")
    if premier != getpass.getpass("Confirmation : "):
        print("Les deux saisies diffèrent.", file=sys.stderr)
        raise SystemExit(1)
    return premier


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(description="Crée le foyer et son premier compte.")
    analyseur.add_argument("nom_foyer")
    analyseur.add_argument("courriel")
    analyseur.add_argument("nom_affichage")
    arguments = analyseur.parse_args(argv)

    courriel = normaliser_courriel(arguments.courriel)
    session = fabrique_de_sessions()()
    try:
        if depot.utilisateur_par_courriel(session, courriel) is not None:
            print(f"Un compte existe déjà pour {courriel}.", file=sys.stderr)
            return 1

        try:
            empreinte = hacher_mot_de_passe(lire_mot_de_passe())
        except MotDePasseTropCourt as erreur:
            print(str(erreur), file=sys.stderr)
            return 1

        foyer = depot.creer_foyer(session, arguments.nom_foyer)
        utilisateur = depot.creer_utilisateur(
            session,
            foyer_id=foyer.id,
            courriel=courriel,
            nom_affichage=arguments.nom_affichage,
            empreinte_mot_de_passe=empreinte,
        )
        session.commit()
    finally:
        session.close()

    print(f"Foyer « {foyer.nom} » créé, compte {utilisateur.courriel} actif.")
    print("Les autres membres rejoignent via POST /auth/invitations puis /auth/rejoindre.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
