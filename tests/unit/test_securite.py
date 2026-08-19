"""Tests des primitives de sécurité.

Chaque test cherche le cas où la fonction pourrait rendre la réponse inverse : un mot de
passe faux accepté, un jeton prévisible, une expiration franchie sans être vue.
"""

from __future__ import annotations

import datetime as dt

import pytest
from mycounts.domain.securite import (
    LONGUEUR_MINIMALE_MOT_DE_PASSE,
    MotDePasseTropCourt,
    empreinte_jeton,
    engendrer_jeton,
    est_expire,
    expiration_invitation,
    expiration_session,
    hacher_mot_de_passe,
    jetons_equivalents,
    normaliser_courriel,
    verifier_mot_de_passe,
)

MOT_DE_PASSE = "correct cheval batterie agrafe"


def test_un_mot_de_passe_correct_est_accepte() -> None:
    assert verifier_mot_de_passe(hacher_mot_de_passe(MOT_DE_PASSE), MOT_DE_PASSE)


@pytest.mark.parametrize(
    "tentative",
    [
        "correct cheval batterie agraf",  # un caractère de moins
        "correct cheval batterie agrafe ",  # espace final
        "Correct cheval batterie agrafe",  # casse différente
        "",
        "autre chose entierement",
    ],
)
def test_un_mot_de_passe_faux_est_refuse(tentative: str) -> None:
    """Sans ce volet, une fonction qui renverrait toujours True passerait le test ci-dessus."""
    assert not verifier_mot_de_passe(hacher_mot_de_passe(MOT_DE_PASSE), tentative)


def test_deux_hachages_du_meme_mot_de_passe_different() -> None:
    """Le sel doit être aléatoire : deux empreintes identiques trahiraient son absence."""
    a = hacher_mot_de_passe(MOT_DE_PASSE)
    b = hacher_mot_de_passe(MOT_DE_PASSE)
    assert a != b
    assert verifier_mot_de_passe(a, MOT_DE_PASSE)
    assert verifier_mot_de_passe(b, MOT_DE_PASSE)


def test_l_empreinte_ne_contient_pas_le_mot_de_passe() -> None:
    empreinte = hacher_mot_de_passe(MOT_DE_PASSE)
    assert MOT_DE_PASSE not in empreinte
    assert empreinte.startswith("$argon2id$")


def test_mot_de_passe_trop_court_refuse() -> None:
    with pytest.raises(MotDePasseTropCourt):
        hacher_mot_de_passe("a" * (LONGUEUR_MINIMALE_MOT_DE_PASSE - 1))


def test_mot_de_passe_a_la_longueur_exacte_accepte() -> None:
    """La borne est inclusive : 12 caractères passent, 11 non."""
    assert hacher_mot_de_passe("a" * LONGUEUR_MINIMALE_MOT_DE_PASSE)


@pytest.mark.parametrize("empreinte", ["", "pas une empreinte", "$argon2id$tronque"])
def test_empreinte_corrompue_refuse_sans_lever(empreinte: str) -> None:
    """Une empreinte illisible doit refuser l'accès, pas produire une erreur 500."""
    assert not verifier_mot_de_passe(empreinte, MOT_DE_PASSE)


def test_les_jetons_sont_uniques_et_longs() -> None:
    jetons = {engendrer_jeton() for _ in range(500)}
    assert len(jetons) == 500, "collision : le générateur n'est pas aléatoire"
    assert all(len(j) >= 40 for j in jetons)


def test_l_empreinte_de_jeton_est_deterministe_et_distincte() -> None:
    jeton = engendrer_jeton()
    assert empreinte_jeton(jeton) == empreinte_jeton(jeton)
    assert empreinte_jeton(jeton) != empreinte_jeton(engendrer_jeton())
    assert jeton not in empreinte_jeton(jeton)


def test_comparaison_de_jetons() -> None:
    jeton = engendrer_jeton()
    assert jetons_equivalents(jeton, jeton)
    assert not jetons_equivalents(jeton, jeton[:-1] + ("a" if jeton[-1] != "a" else "b"))


@pytest.mark.parametrize(
    ("saisi", "attendu"),
    [
        ("  Olivier@Exemple.FR ", "olivier@exemple.fr"),
        ("a@b.fr", "a@b.fr"),
        ("A@B.FR", "a@b.fr"),
    ],
)
def test_normalisation_du_courriel(saisi: str, attendu: str) -> None:
    assert normaliser_courriel(saisi) == attendu


def test_expiration_atteinte_est_expiree() -> None:
    """Borne inclusive : à la milliseconde exacte, la session est déjà expirée."""
    instant = dt.datetime(2026, 8, 19, 12, 0, tzinfo=dt.UTC)
    assert est_expire(instant, instant)
    assert est_expire(instant - dt.timedelta(microseconds=1), instant)
    assert not est_expire(instant + dt.timedelta(microseconds=1), instant)


def test_echeance_sans_fuseau_refusee() -> None:
    with pytest.raises(ValueError, match="sans fuseau"):
        est_expire(dt.datetime(2026, 8, 19, 12, 0))  # noqa: DTZ001 — c'est le cas testé


def test_les_durees_vont_dans_le_bon_sens() -> None:
    """Témoin : une expiration doit être dans le futur, et l'invitation plus courte
    que la session. Une inversion de signe passerait inaperçue sans cette comparaison."""
    instant = dt.datetime(2026, 8, 19, 12, 0, tzinfo=dt.UTC)
    assert expiration_session(instant) > instant
    assert expiration_invitation(instant) > instant
    assert expiration_invitation(instant) < expiration_session(instant)
