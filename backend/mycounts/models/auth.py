"""Tables d'authentification et d'appartenance au foyer.

`foyer_id` est présent dès maintenant, alors que l'interface n'expose aucun partage :
ajouter le périmètre après coup obligerait à toucher chaque requête de lecture du projet.
C'est le seul endroit où anticiper coûte moins cher que corriger.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mycounts.models.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Foyer(Base):
    __tablename__ = "foyer"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    nom: Mapped[str] = mapped_column(String(120))
    cree_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    membres: Mapped[list[Utilisateur]] = relationship(back_populates="foyer")


class Utilisateur(Base):
    __tablename__ = "utilisateur"
    __table_args__ = (UniqueConstraint("courriel", name="uq_utilisateur_courriel"),)

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    foyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("foyer.id", ondelete="RESTRICT"))
    # Toujours stocké en minuscules normalisées : sans ça, « A@b.fr » et « a@b.fr »
    # créeraient deux comptes que l'unicité SQL ne verrait pas comme un doublon.
    courriel: Mapped[str] = mapped_column(String(254))
    nom_affichage: Mapped[str] = mapped_column(String(80))
    empreinte_mot_de_passe: Mapped[str] = mapped_column(String(255))
    actif: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    cree_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    foyer: Mapped[Foyer] = relationship(back_populates="membres")


class Invitation(Base):
    """Code d'invitation à usage unique.

    Seule l'empreinte du code est stockée : une fuite de la base ne permet pas de
    rejoindre un foyer. Le code en clair n'existe qu'une fois, au moment de sa création.
    """

    __tablename__ = "invitation"
    __table_args__ = (UniqueConstraint("empreinte_code", name="uq_invitation_empreinte"),)

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    foyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("foyer.id", ondelete="CASCADE"))
    empreinte_code: Mapped[str] = mapped_column(String(64))
    creee_par_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE")
    )
    cree_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expire_le: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    utilisee_le: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class SessionWeb(Base):
    """Session authentifiée, désignée par un jeton opaque.

    Le jeton fait 256 bits d'entropie : son empreinte SHA-256 suffit. Argon2 n'apporterait
    rien ici — il protège contre l'attaque par dictionnaire d'un secret CHOISI par un
    humain, ce qu'un jeton aléatoire n'est pas.
    """

    __tablename__ = "session_web"
    __table_args__ = (UniqueConstraint("empreinte_jeton", name="uq_session_empreinte"),)

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE")
    )
    empreinte_jeton: Mapped[str] = mapped_column(String(64))
    cree_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expire_le: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
