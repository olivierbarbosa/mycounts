"""Persistance des preuves d'identité, appareils fiables et courriels sortants."""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Mapping

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from mycounts.models.auth import (
    AppareilConfiance,
    CourrielSortant,
    JetonIdentite,
    Utilisateur,
)


def creer_jeton(
    session: Session,
    *,
    utilisateur_id: uuid.UUID,
    usage: str,
    empreinte: str,
    expire_le: dt.datetime,
) -> JetonIdentite:
    """Remplace les liens encore ouverts du même usage pour éviter deux portes actives."""
    session.execute(
        delete(JetonIdentite).where(
            JetonIdentite.utilisateur_id == utilisateur_id,
            JetonIdentite.usage == usage,
            JetonIdentite.utilise_le.is_(None),
        )
    )
    jeton = JetonIdentite(
        utilisateur_id=utilisateur_id,
        usage=usage,
        empreinte=empreinte,
        expire_le=expire_le,
    )
    session.add(jeton)
    session.flush()
    return jeton


def consommer_jeton(
    session: Session, *, empreinte: str, usage: str, a_l_instant: dt.datetime
) -> tuple[JetonIdentite, Utilisateur] | None:
    """Verrouille puis consomme; deux requêtes concurrentes ne gagnent jamais ensemble."""
    ligne = session.execute(
        select(JetonIdentite, Utilisateur)
        .join(Utilisateur, Utilisateur.id == JetonIdentite.utilisateur_id)
        .where(
            JetonIdentite.empreinte == empreinte,
            JetonIdentite.usage == usage,
            JetonIdentite.utilise_le.is_(None),
            JetonIdentite.expire_le > a_l_instant,
            Utilisateur.actif.is_(True),
        )
        .with_for_update()
    ).one_or_none()
    if ligne is None:
        return None
    jeton, utilisateur = ligne
    jeton.utilise_le = a_l_instant
    session.flush()
    return jeton, utilisateur


def marquer_courriel_verifie(
    session: Session, utilisateur: Utilisateur, *, a_l_instant: dt.datetime
) -> None:
    utilisateur.courriel_verifie_le = a_l_instant
    session.flush()


def creer_appareil(
    session: Session,
    *,
    utilisateur_id: uuid.UUID,
    empreinte_secret: str,
    nom: str,
    expire_le: dt.datetime,
) -> AppareilConfiance:
    appareil = AppareilConfiance(
        utilisateur_id=utilisateur_id,
        empreinte_secret=empreinte_secret,
        nom=nom[:120] or "Appareil",
        expire_le=expire_le,
    )
    session.add(appareil)
    session.flush()
    return appareil


def appareil_actif(
    session: Session,
    *,
    utilisateur_id: uuid.UUID,
    empreinte_secret: str,
    a_l_instant: dt.datetime,
) -> AppareilConfiance | None:
    appareil = session.execute(
        select(AppareilConfiance).where(
            AppareilConfiance.utilisateur_id == utilisateur_id,
            AppareilConfiance.empreinte_secret == empreinte_secret,
            AppareilConfiance.expire_le > a_l_instant,
        )
    ).scalar_one_or_none()
    if appareil is not None:
        appareil.vu_le = a_l_instant
        session.flush()
    return appareil


def tourner_secret_appareil(
    session: Session,
    appareil: AppareilConfiance,
    *,
    empreinte_secret: str,
    expire_le: dt.datetime,
) -> None:
    appareil.empreinte_secret = empreinte_secret
    appareil.expire_le = expire_le
    session.flush()


def appareils_de(session: Session, utilisateur_id: uuid.UUID) -> list[AppareilConfiance]:
    return list(
        session.execute(
            select(AppareilConfiance)
            .where(AppareilConfiance.utilisateur_id == utilisateur_id)
            .order_by(AppareilConfiance.vu_le.desc())
        ).scalars()
    )


def revoquer_appareil(
    session: Session, *, utilisateur_id: uuid.UUID, appareil_id: uuid.UUID
) -> bool:
    appareil = session.execute(
        select(AppareilConfiance).where(
            AppareilConfiance.id == appareil_id,
            AppareilConfiance.utilisateur_id == utilisateur_id,
        )
    ).scalar_one_or_none()
    if appareil is None:
        return False
    session.delete(appareil)
    session.flush()
    return True


def revoquer_tous_les_appareils(session: Session, utilisateur_id: uuid.UUID) -> None:
    session.execute(
        delete(AppareilConfiance).where(AppareilConfiance.utilisateur_id == utilisateur_id)
    )
    session.flush()


def mettre_en_file(
    session: Session,
    *,
    utilisateur_id: uuid.UUID,
    cle_idempotence: str,
    destinataire: str,
    modele: str,
    donnees: Mapping[str, str],
) -> CourrielSortant:
    existant = session.execute(
        select(CourrielSortant).where(CourrielSortant.cle_idempotence == cle_idempotence)
    ).scalar_one_or_none()
    if existant is not None:
        return existant
    courriel = CourrielSortant(
        utilisateur_id=utilisateur_id,
        cle_idempotence=cle_idempotence,
        destinataire=destinataire,
        modele=modele,
        donnees=dict(donnees),
    )
    session.add(courriel)
    session.flush()
    return courriel


def prochain_courriel(
    session: Session, *, a_l_instant: dt.datetime
) -> CourrielSortant | None:
    return session.execute(
        select(CourrielSortant)
        .where(
            CourrielSortant.envoye_le.is_(None),
            CourrielSortant.prochaine_tentative_le <= a_l_instant,
            CourrielSortant.tentatives < 8,
        )
        .order_by(CourrielSortant.cree_le)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).scalar_one_or_none()


def marquer_envoye(
    session: Session, courriel: CourrielSortant, *, a_l_instant: dt.datetime
) -> None:
    courriel.envoye_le = a_l_instant
    courriel.derniere_erreur = None
    # Le lien contient le jeton en clair par nécessité de transport. Il disparaît de la
    # base dès l'envoi; seule son empreinte à usage unique reste dans `jeton_identite`.
    courriel.donnees = {}
    session.flush()


def reporter_courriel(
    session: Session,
    courriel: CourrielSortant,
    *,
    a_l_instant: dt.datetime,
    erreur: str,
) -> None:
    courriel.tentatives += 1
    # 1, 2, 4… minutes, borné à une heure. La ligne reste inspectable après huit essais.
    minutes = min(60, 2 ** max(0, courriel.tentatives - 1))
    courriel.prochaine_tentative_le = a_l_instant + dt.timedelta(minutes=minutes)
    courriel.derniere_erreur = erreur[:240]
    session.flush()
