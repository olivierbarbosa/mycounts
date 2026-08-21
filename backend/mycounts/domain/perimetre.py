"""Sur quel argent on travaille.

Deux mondes ÉTANCHES, décidé par Olivier le 21 août 2026 : on répond à « combien j'ai » ou
à « combien on a », jamais aux deux mélangés. Un solde qui additionnerait le compte joint
et le livret personnel ferait croire à une aisance qui n'appartient à personne.

**Ce type vit dans le domaine et non dans le repository.** Il a d'abord été écrit à côté du
`Principal`, ce qui obligeait les MODÈLES à importer le repository — une couche basse
dépendant d'une couche haute. Le domaine, lui, ne dépend de rien et tout le monde peut en
dépendre : c'est exactement le rôle qu'une notion partagée doit tenir.
"""

from __future__ import annotations

from enum import StrEnum


class Vue(StrEnum):
    """Le périmètre regardé.

    La vue n'est pas un filtre d'affichage : elle fait partie du PÉRIMÈTRE, au même titre
    que le foyer. C'est pourquoi elle voyage dans le `Principal` et non dans un paramètre
    de route — une fonction qui l'oublierait rendrait des comptes qui ne sont pas les
    siens, et le seul moyen d'empêcher cet oubli est qu'elle ne puisse pas être omise.
    """

    PERSONNELLE = "personnelle"
    """Les comptes privés de la personne connectée, ses budgets, ses enveloppes."""

    FOYER = "foyer"
    """Les comptes joints du foyer, et ce que tous ses membres partagent."""
