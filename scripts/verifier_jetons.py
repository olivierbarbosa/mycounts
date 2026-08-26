"""Garde-fou n°12 — aucun `var(--…)` qui ne désigne un jeton existant.

Le garde-fou n°9 interdit d'écrire une couleur EN DUR. Il ne dit rien de l'erreur
inverse, et plus silencieuse : écrire `var(--fond-verre)` quand le jeton s'appelle
`--couleur-verre-opaque`. Une variable CSS inconnue rend la déclaration invalide, le
navigateur la jette, et il ne reste RIEN — ni erreur, ni avertissement, ni trace dans la
console. Le composant s'affiche, en moins bien, et personne ne sait pourquoi.

C'est arrivé le 27 août 2026 : `SelecteurEspace.module.css` utilisait onze noms
inexistants sur dix-neuf. La barre s'affichait sans fond, sans bordure, sans ombre, et
surtout sans distinction entre l'espace actif et les autres — les deux couleurs de texte
étant également fantômes. Voir ERREURS.md #053.

CE QUI EST DÉTECTÉ dans `frontend/src` :
  - tout `var(--x)` dont `--x` n'est ni généré par `design/tokens.ts`, ni déclaré dans
    une feuille du projet, ni posé en ligne depuis un composant React.

CE QUI COMPTE COMME DÉCLARÉ :
  - les jetons produits par `feuilleDeTokens()` — les groupes préfixés (`--couleur-…`,
    `--verre-…`, `--rayon-…`…) et les quelques noms écrits littéralement ;
  - tout `--x:` écrit dans un `.css` du projet ;
  - tout `'--x':` posé dans un objet `style` d'un `.tsx` — c'est ainsi que `--rang`,
    `--actif` ou `--teinte-marque` arrivent dans le CSS, et les refuser ferait rougir ce
    contrôle devant du code correct.

CE QUI N'EST PAS DÉTECTÉ — limites assumées :
  - un jeton qui EXISTE mais dont la valeur ne convient pas : ce contrôle vérifie
    l'existence, jamais la pertinence ;
  - un jeton déclaré dans un fichier et utilisé dans un autre sans que la cascade les
    relie : le nom est connu, la portée ne l'est pas ;
  - `var(--x, repli)` avec repli : signalé quand même, parce qu'un nom inventé reste une
    faute, mais le repli fait que le rendu, lui, n'est pas cassé ;
  - les variables construites dynamiquement (`var(--teinte-${n})`), qu'aucune lecture
    statique ne peut résoudre.

Si `tokens.ts` devient illisible pour ce script, il ÉCHOUE au lieu de passer : un
contrôle qui ne trouve plus sa référence ne doit jamais conclure « rien à signaler ».
"""

from __future__ import annotations

import re
import sys
from typing import Final

from scripts.commun import RACINE, afficher_chemin

SOURCE: Final = RACINE / "frontend" / "src"
TOKENS: Final = SOURCE / "design" / "tokens.ts"

# `export const nomDuGroupe = {` … `}` — le bloc d'un groupe de jetons.
_GROUPE: Final = re.compile(
    r"^export const (\w+)(?::[^=]+)? = \{(.*?)^\}", re.DOTALL | re.MULTILINE
)
# Une clé d'objet, en camelCase, éventuellement entre guillemets.
_CLE: Final = re.compile(r"^\s*['\"]?([A-Za-z][A-Za-z0-9]*)['\"]?\s*:", re.MULTILINE)
# `enVariables('prefixe', nomDuGroupe)` — la liaison entre un préfixe et un groupe.
_EMISSION: Final = re.compile(r"enVariables\(\s*['\"](\w+)['\"]\s*,\s*(\w+)\s*\)")
# Un nom écrit littéralement dans la feuille (`--cible-tactile: …`).
_LITTERAL: Final = re.compile(r"(--[a-z0-9-]+)\s*:")

_USAGE: Final = re.compile(r"var\(\s*(--[a-z0-9-]+)")
_DECLARATION_CSS: Final = re.compile(r"(--[a-z0-9-]+)\s*:")
# Tolère la clé calculée `['--x' as string]:`, qu'un composant écrit pour contourner le
# typage de `CSSProperties`. Exiger le deux-points sur la même ligne garde le motif serré.
_DECLARATION_TSX: Final = re.compile(r"['\"](--[a-z0-9-]+)['\"][^:\n]*:")

_BLOC_COMMENTAIRE: Final = re.compile(r"/\*.*?\*/", re.DOTALL)


def en_kebab(nom: str) -> str:
    """Même conversion que `enKebab` dans tokens.ts — `reserveBulle` → `reserve-bulle`."""
    return re.sub(r"[A-Z]", lambda majuscule: f"-{majuscule.group().lower()}", nom)


def jetons_generes(source_tokens: str) -> set[str]:
    """Les noms que `feuilleDeTokens()` écrira réellement.

    Reconstruits depuis les MÊMES deux informations que la fonction TypeScript : les clés
    de chaque groupe, et les appels qui associent un préfixe à un groupe. Recopier une
    liste de noms ici en ferait un second auteur, qui se périmerait au premier jeton
    ajouté — exactement la faute que ce garde-fou cherche à empêcher.
    """
    groupes = {nom: set(_CLE.findall(corps)) for nom, corps in _GROUPE.findall(source_tokens)}
    emissions = _EMISSION.findall(source_tokens)
    if not groupes or not emissions:
        raise ValueError(
            "tokens.ts n'a pas pu être lu : ni groupe ni appel à enVariables() trouvé."
        )

    noms = {
        f"--{prefixe}-{en_kebab(cle)}"
        for prefixe, groupe in emissions
        for cle in groupes.get(groupe, ())
    }
    # Les noms posés à la main dans le gabarit, hors des groupes.
    debut = source_tokens.find("feuilleDeTokens")
    noms |= set(_LITTERAL.findall(source_tokens[debut:]))
    return noms


def retirer_commentaires(texte: str) -> str:
    """Un `var(--…)` cité dans un commentaire n'est pas un usage."""
    return _BLOC_COMMENTAIRE.sub(lambda m: "\n" * m.group().count("\n"), texte)


def main() -> int:
    if not TOKENS.is_file():
        print(f"tokens.ts introuvable : {TOKENS}", file=sys.stderr)
        return 1

    try:
        connus = jetons_generes(TOKENS.read_text(encoding="utf-8"))
    except ValueError as erreur:
        print(f"Garde-fou n°12 inutilisable : {erreur}", file=sys.stderr)
        return 1

    fichiers = [
        f for f in sorted(SOURCE.rglob("*")) if f.is_file() and f.suffix in {".css", ".tsx"}
    ]

    # Deuxième passe nécessaire : une variable peut être déclarée dans un fichier et lue
    # dans un autre — `--rang` est posée par Bulle.tsx et lue par Bulle.module.css.
    for fichier in fichiers:
        contenu = fichier.read_text(encoding="utf-8")
        motif = _DECLARATION_CSS if fichier.suffix == ".css" else _DECLARATION_TSX
        connus |= set(motif.findall(contenu))

    trouvailles: list[str] = []
    for fichier in fichiers:
        contenu = retirer_commentaires(fichier.read_text(encoding="utf-8"))
        for numero, ligne in enumerate(contenu.splitlines(), 1):
            for jeton in _USAGE.findall(ligne):
                if jeton not in connus:
                    trouvailles.append(f"{afficher_chemin(fichier)}:{numero} {jeton}")

    if trouvailles:
        print("JETON CSS INEXISTANT — la déclaration sera jetée en silence :", file=sys.stderr)
        for trouvaille in trouvailles:
            print(f"  {trouvaille}", file=sys.stderr)
        print(
            f"\nLes noms disponibles sont générés par {afficher_chemin(TOKENS)} :"
            " ils sont TOUS préfixés par leur groupe (--couleur-…, --verre-…, --rayon-…).",
            file=sys.stderr,
        )
        return 1

    print(f"Garde-fou n°12 : {len(connus)} jetons connus, aucun var(--…) inexistant.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
