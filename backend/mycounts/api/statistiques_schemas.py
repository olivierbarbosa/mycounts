"""Schémas des statistiques."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel

from mycounts.domain.statistiques import Motif


class PostePublic(BaseModel):
    categorie: str | None
    """`None` pour « sans catégorie ». Jamais masqué à l'écran : c'est souvent la plus
    grosse ligne, et la cacher donnerait une répartition fausse."""

    montant_centimes: int
    part: int
    montant_precedent_centimes: int | None
    variation: int | None
    """`None` quand le poste n'existait pas : « nouveau » et « +∞ % » ne disent pas la
    même chose."""


class ConstatPublic(BaseModel):
    """Un fait chiffré, jamais un jugement. Voir `domain/statistiques.py`."""

    motif: Motif
    sujet: str
    montant_centimes: int
    detail: int


class StatistiquesPubliques(BaseModel):
    debut: dt.date
    fin: dt.date
    total_centimes: int
    total_precedent_centimes: int
    nombre_de_depenses: int
    cout_annuel_des_abonnements_centimes: int
    postes: list[PostePublic]
    constats: list[ConstatPublic]
