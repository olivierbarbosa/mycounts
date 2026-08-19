"""Garde-fou n°2 — aucun secret commité.

CE QUI EST DÉTECTÉ
  - les préfixes de jetons reconnaissables (clés de fournisseurs, jetons GitHub/Slack,
    identifiants AWS) ;
  - les blocs de clé privée ;
  - une affectation de mot de passe / secret à une chaîne littérale non vide dans le code ;
  - une URL de connexion portant des identifiants vers un hôte **non local** ;
  - un fichier `.env` réellement **suivi par git** (le cas le plus fréquent en pratique).

CE QUI N'EST PAS DÉTECTÉ — limites assumées :
  - un secret sans préfixe reconnaissable (une chaîne aléatoire de 32 caractères est
    indiscernable d'un identifiant de test) ;
  - l'historique git : seul l'arbre de travail est analysé. Un secret déjà commité puis
    retiré reste dans l'historique et doit être révoqué, pas seulement supprimé ;
  - les secrets dans des fichiers binaires.

Un outil dédié (gitleaks) couvre plus large et pourra compléter ce contrôle en CI. Il
n'est pas listé ici tant qu'il n'a pas été réellement exécuté sur ce dépôt : annoncer une
protection non vérifiée est pire que ne rien annoncer.
"""

from __future__ import annotations

import re
import subprocess
import sys
from typing import Final

from scripts.commun import RACINE, afficher_chemin, fichiers_du_depot, texte_de

MOTIFS: Final = (
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"), "clé secrète de fournisseur (sk-…)"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"), "jeton GitHub"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "jeton Slack"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "identifiant AWS"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"), "clé privée"),
    (
        re.compile(
            r"""(?i)\b(?:password|passwd|secret|api_?key|token)\s*[:=]\s*["'][^"'\s]{8,}["']"""
        ),
        "secret affecté en dur",
    ),
)

# Une URL de connexion porte souvent le mot de passe de la base. Les hôtes locaux sont
# tolérés : `.env.example` doit pouvoir montrer une URL de développement utilisable.
_URL_AVEC_IDENTIFIANTS: Final = re.compile(r"://[^:/@\s]+:[^@/\s]+@(?P<hote>[^:/\s]+)")
HOTES_LOCAUX: Final = frozenset({"localhost", "127.0.0.1", "::1", "db", "postgres"})

# Chaînes manifestement inertes. Cette liste ne désarme QUE la détection d'un secret
# affecté en dur — jamais celle des jetons ni des URL : un jeton `ghp_…` reste un jeton
# même sur une ligne qui contient le mot « exemple ». Ce périmètre trop large était un
# angle mort, révélé par le témoin de test.
INERTES: Final = re.compile(
    r"""(?i)(exemple|example|placeholder|changeme|xxx+|\.\.\.|votre[_-]|<[^>]+>|\$\{)"""
)


def libelles_de_ligne(ligne: str) -> list[str]:
    """Libellés des secrets détectés sur une ligne. Fonction pure, donc testable."""
    inerte = INERTES.search(ligne) is not None
    libelles = [
        libelle
        for motif, libelle in MOTIFS
        if motif.search(ligne) and not (inerte and libelle == "secret affecté en dur")
    ]
    correspondance = _URL_AVEC_IDENTIFIANTS.search(ligne)
    if correspondance and correspondance["hote"] not in HOTES_LOCAUX:
        libelles.append("URL de connexion avec identifiants vers un hôte distant")
    return libelles


def fichiers_env_suivis() -> list[str]:
    """Fichiers .env réellement suivis par git — le cas le plus fréquent."""
    try:
        sortie = subprocess.run(
            ["git", "ls-files", "-z"], cwd=RACINE, capture_output=True, text=True, check=True
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [
        f for f in sortie.split("\0")
        if f and (f == ".env" or f.startswith(".env.")) and f != ".env.example"
    ]


def main() -> int:
    trouvailles: list[str] = []
    moi = __file__

    for suivi in fichiers_env_suivis():
        trouvailles.append(f"{suivi} : fichier d'environnement suivi par git")

    for chemin in fichiers_du_depot():
        if str(chemin) == moi:
            continue
        contenu = texte_de(chemin)
        if contenu is None:
            continue
        for numero, ligne in enumerate(contenu.splitlines(), 1):
            trouvailles.extend(
                f"{afficher_chemin(chemin)}:{numero} {libelle}"
                for libelle in libelles_de_ligne(ligne)
            )

    if trouvailles:
        print("SECRET POTENTIEL DÉTECTÉ :", file=sys.stderr)
        for trouvaille in trouvailles:
            print(f"  {trouvaille}", file=sys.stderr)
        print(
            "\nUn secret déjà commité doit être RÉVOQUÉ, pas seulement supprimé : il reste "
            "dans l'historique.",
            file=sys.stderr,
        )
        return 1

    print("Garde-fou n°2 : aucun secret détecté.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
