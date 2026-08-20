"""Catégorisation assistée des libellés importés — SEUL point de sortie vers un tiers.

**Ce fichier est le seul de tout le projet autorisé à parler à un service externe.** Le
garde-fou nº 3 le vérifie : si l'URL d'OpenRouter apparaît ailleurs, il échoue. La raison
n'est pas cosmétique — un projet qui envoie des données bancaires doit pouvoir répondre
« ce fichier, et lui seul » à la question « qu'est-ce qui sort ».

## Ce qui sort, exactement

Des **libellés de commerçants**, et rien d'autre :

    ["INTERMARCHE", "TOTAL", "SCM LA PROVIDENCE"]

Ne sortent JAMAIS : les montants, les dates, les soldes, les numéros de compte, les
identifiants de foyer ou d'utilisateur, les références bancaires. La fonction ci-dessous
prend une liste de `str` et rien de plus — ce n'est pas une politesse d'écriture, c'est ce
qui rend la promesse vérifiable par lecture du seul prototype.

Olivier a accepté ce départ de données en connaissance de cause le 20 août 2026, après
qu'on lui a montré ce que contiendraient les libellés — y compris ceux qui trahissent un
rendez-vous médical.

## Ce que ce module ne fait pas

- **Il ne décide rien.** Il PROPOSE une catégorie, l'écran de revue la montre décochable
  comme le reste. Rien ne s'écrit sans revue, y compris ce qui vient d'un modèle.
- **Il n'est jamais bloquant.** Clé absente, service en panne, réponse illisible : la
  fonction rend un dictionnaire vide et l'import continue exactement comme avant. Une
  catégorisation est un confort ; en faire une dépendance de l'import rendrait celui-ci
  tributaire d'un tiers pour une tâche qu'il sait faire sans lui.
- **Il n'est appelé que pour ce qui reste.** Les correspondances apprises et le tableau par
  défaut passent d'abord : moins d'appels, moins de coût, et moins de libellés qui sortent.
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Final

import httpx

URL: Final[str] = "https://openrouter.ai/api/v1/chat/completions"

"""Modèle par défaut : francophone, économique, et suffisant pour classer un libellé.

`mistral-nemo` coûte 0,019 $ par million de tokens en entrée — environ quatre centièmes de
millime pour deux cents libellés. Le choix se change par `MYCOUNTS_MODELE_IA` sans toucher
au code : un modèle est une dépendance externe comme une autre, et la figer dans les
sources obligerait à un déploiement pour en essayer un autre.
"""
MODELE_PAR_DEFAUT: Final[str] = "mistralai/mistral-nemo"

"""Délai au-delà duquel on renonce, en secondes.

Court volontairement. Ce module sert un écran que l'utilisateur regarde : mieux vaut une
revue sans suggestions dans la seconde qu'une revue parfaite dans dix.
"""
DELAI: Final[float] = 8.0

"""Nombre maximal de libellés envoyés en une fois.

Au-delà, la réponse devient longue et le modèle commence à en oublier. Deux cents libellés
d'un relevé mensuel tiennent largement — et un fichier plus gros sera simplement moins
complètement suggéré, ce qui est sans conséquence puisque rien n'est bloquant.
"""
LOT_MAXIMAL: Final[int] = 120

CONSIGNE: Final[str] = (
    "Tu classes des libellés de relevé bancaire français dans des catégories de budget. "
    "Réponds UNIQUEMENT par un objet JSON dont chaque clé est un libellé reçu et chaque "
    "valeur le nom EXACT d'une catégorie de la liste fournie, ou null si aucune ne "
    "convient. N'invente aucune catégorie. N'ajoute aucun commentaire."
)


def _cle() -> str | None:
    """La clé, lue dans l'environnement — jamais dans le dépôt.

    `None` quand elle est absente : le module se tait alors, et l'import fonctionne sans
    lui. C'est le comportement voulu en développement, en test, et sur toute installation
    dont le propriétaire ne veut pas que ses libellés sortent.
    """
    cle = os.environ.get("MYCOUNTS_CLE_OPENROUTER", "").strip()
    return cle or None


def proposer_des_categories(
    libelles: Sequence[str], categories: Sequence[str]
) -> dict[str, str]:
    """Propose une catégorie pour chaque libellé. Rend `{}` en cas de difficulté.

    Les deux arguments sont des listes de CHAÎNES, et c'est la garantie centrale de ce
    module : il ne peut pas envoyer un montant, une date ou un numéro de compte, parce
    qu'il n'en reçoit pas.

    Le résultat est filtré contre `categories` avant d'être rendu : un modèle qui
    inventerait une catégorie absente de la liste verrait sa réponse écartée, plutôt que
    de faire remonter un nom qui ne correspond à rien dans le foyer.
    """
    cle = _cle()
    if cle is None or not libelles or not categories:
        return {}

    uniques = list(dict.fromkeys(libelle for libelle in libelles if libelle.strip()))[
        :LOT_MAXIMAL
    ]
    if not uniques:
        return {}

    demande = {
        "model": os.environ.get("MYCOUNTS_MODELE_IA", MODELE_PAR_DEFAUT),
        "temperature": 0,
        "messages": [
            {"role": "system", "content": CONSIGNE},
            {
                "role": "user",
                "content": json.dumps(
                    {"categories": list(categories), "libelles": uniques},
                    ensure_ascii=False,
                ),
            },
        ],
    }

    try:
        reponse = httpx.post(
            URL,
            headers={"Authorization": f"Bearer {cle}", "Content-Type": "application/json"},
            json=demande,
            timeout=DELAI,
        )
        reponse.raise_for_status()
        contenu = reponse.json()["choices"][0]["message"]["content"]
    except Exception:
        # Toute difficulté — réseau, quota, format inattendu — se solde par un silence.
        # Laisser remonter l'erreur ferait échouer un import qui n'avait pas besoin de ce
        # service pour aboutir.
        return {}

    return _lire_la_reponse(contenu, uniques, categories)


def _lire_la_reponse(
    contenu: str, libelles: Sequence[str], categories: Sequence[str]
) -> dict[str, str]:
    """Extrait le mappage de la réponse, en n'en gardant que ce qui est vérifiable.

    Un modèle encadre volontiers son JSON de texte ou de balises de code. On cherche donc
    le premier objet plutôt que d'exiger une réponse parfaitement propre — et on rend `{}`
    si l'on n'en trouve pas, plutôt que de deviner.
    """
    debut, fin = contenu.find("{"), contenu.rfind("}")
    if debut == -1 or fin <= debut:
        return {}
    try:
        brut = json.loads(contenu[debut : fin + 1])
    except json.JSONDecodeError:
        return {}
    if not isinstance(brut, dict):
        return {}

    connus = set(libelles)
    permises = set(categories)
    return {
        libelle: categorie
        for libelle, categorie in brut.items()
        if isinstance(libelle, str)
        and isinstance(categorie, str)
        and libelle in connus
        and categorie in permises
    }
