"""Comptes, catégories et opérations.

Deux choix de modélisation qui ne se rediscutent pas :

- **`operation` ne porte pas de `foyer_id`.** Il serait une copie de `compte.foyer_id`,
  donc une seconde source de vérité qui dériverait le jour où une opération change de
  compte. Le périmètre passe par une jointure sur `compte` — plus verbeux dans le
  repository, mais impossible à désynchroniser.
- **La couleur d'une catégorie est une TEINTE NOMMÉE, pas un code hexadécimal.** Stocker
  « #7C3AED » en base contournerait le garde-fou n°9 (aucune couleur hors des tokens) :
  la palette se retrouverait à moitié dans le code, à moitié dans les données, et le
  changement de thème clair/sombre deviendrait impossible.
"""

from __future__ import annotations

import datetime as dt
import uuid
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mycounts.domain.agregats import EtatOperation
from mycounts.models.auth import Foyer, Utilisateur
from mycounts.models.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class NatureCategorie(StrEnum):
    DEPENSE = "depense"
    REVENU = "revenu"


class TeinteCategorie(StrEnum):
    """Teintes disponibles, résolues en couleur par `frontend/src/design/tokens.ts`."""

    VIOLET = "violet"
    CYAN = "cyan"
    VERT = "vert"
    AMBRE = "ambre"
    ROSE = "rose"
    ARDOISE = "ardoise"


class Compte(Base):
    """Compte bancaire.

    Au lot 2, tout compte est privé : `proprietaire_id` est obligatoire. Les comptes
    joints arrivent au lot 5 et rendront cette colonne facultative — d'où le `prive`
    explicite dès maintenant plutôt qu'une déduction sur la nullité du propriétaire.
    """

    __tablename__ = "compte"
    __table_args__ = (
        CheckConstraint("devise = 'EUR'", name="ck_compte_devise_eur"),
        UniqueConstraint("foyer_id", "nom", name="uq_compte_nom_par_foyer"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    foyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("foyer.id", ondelete="RESTRICT"))
    proprietaire_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="RESTRICT")
    )
    nom: Mapped[str] = mapped_column(String(80))
    prive: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # Figée par contrainte : le multi-devises imposerait de stocker le taux AVEC chaque
    # opération, sans quoi recalculer un historique réécrirait le passé.
    devise: Mapped[str] = mapped_column(String(3), default="EUR", server_default="EUR")
    archive: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    cree_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    foyer: Mapped[Foyer] = relationship()
    proprietaire: Mapped[Utilisateur] = relationship()


class Categorie(Base):
    """Catégorie de dépense ou de revenu.

    Archivée plutôt que supprimée : les opérations passées doivent garder la catégorie
    sous laquelle elles ont été classées, sinon les totaux d'un mois clos changeraient
    rétroactivement.
    """

    __tablename__ = "categorie"
    __table_args__ = (
        UniqueConstraint("foyer_id", "nom", name="uq_categorie_nom_par_foyer"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    foyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("foyer.id", ondelete="CASCADE"))
    nom: Mapped[str] = mapped_column(String(60))
    nature: Mapped[NatureCategorie] = mapped_column(String(16))
    teinte: Mapped[TeinteCategorie] = mapped_column(String(16))
    archivee: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    cree_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Operation(Base):
    """Mouvement d'argent, réel ou prévu.

    Signe du montant : négatif = sortie, positif = entrée. Un montant nul est refusé par
    contrainte — il ne décrit rien et fausserait les comptages sans changer les totaux.
    """

    __tablename__ = "operation"
    __table_args__ = (
        CheckConstraint("montant_centimes <> 0", name="ck_operation_montant_non_nul"),
        CheckConstraint(
            "not est_paie or montant_centimes > 0", name="ck_operation_paie_positive"
        ),
        CheckConstraint(
            "not (est_paie and est_ouverture)", name="ck_operation_paie_ou_ouverture"
        ),
        Index("ix_operation_compte_date", "compte_id", "date_operation"),
        Index("ix_operation_paie", "compte_id", "date_operation", postgresql_where="est_paie"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    compte_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("compte.id", ondelete="CASCADE"))
    categorie_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categorie.id", ondelete="RESTRICT"), default=None
    )
    cree_par_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="RESTRICT")
    )

    libelle: Mapped[str] = mapped_column(String(140))
    montant_centimes: Mapped[int] = mapped_column(BigInteger)

    # Les trois dates. `date_operation` porte tous les calculs ; `date_valeur` reste
    # facultative tant qu'il n'y a pas d'import ; `cree_le` est technique, en UTC.
    date_operation: Mapped[dt.date] = mapped_column(Date)
    date_valeur: Mapped[dt.date | None] = mapped_column(Date, default=None)
    cree_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    etat: Mapped[EtatOperation] = mapped_column(String(16), default=EtatOperation.CONFIRMEE)

    # Marqueur explicite d'ouverture de période budgétaire. Le déduire d'une catégorie
    # nommée « Salaire » rendrait la règle invisible et cassable en renommant.
    est_paie: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Solde de départ saisi à la création du compte. C'est une OPÉRATION et non une
    # colonne `solde_initial` : un solde reste une somme d'opérations, sans quoi on
    # créerait la seconde source de vérité que tout le projet évite. Le marqueur sert à
    # l'exclure des dépenses — un découvert de départ n'est pas une dépense du mois.
    est_ouverture: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    compte: Mapped[Compte] = relationship()
    categorie: Mapped[Categorie | None] = relationship()
