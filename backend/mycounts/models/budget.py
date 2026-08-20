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
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mycounts.domain.agregats import EtatOperation
from mycounts.domain.comptes import TypeCompte
from mycounts.domain.enveloppes import TypeMouvement as TypeMouvementEnveloppe
from mycounts.domain.recurrence import UniteRecurrence
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
    # Courant ou épargne. Le défaut est `courant` : un compte créé sans qu'on se pose la
    # question est un compte du quotidien, et se tromper dans ce sens ne cache rien à
    # personne — l'inverse retirerait de l'argent du solde affiché sans le dire.
    type_compte: Mapped[TypeCompte] = mapped_column(
        String(16), default=TypeCompte.COURANT, server_default=TypeCompte.COURANT.value
    )
    # Produit tel qu'il existe chez les banques : Livret A, PEL, compte-titres… Il NOMME,
    # il ne calcule pas — c'est `type_compte` que les agrégats lisent. Les deux sont
    # séparés parce qu'un produit peut changer de nom sans que rien ne bouge dans les
    # totaux, et parce qu'un produit absent du catalogue doit rester possible.
    produit: Mapped[str] = mapped_column(
        String(32), default="compte_courant", server_default="compte_courant"
    )
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


class Recurrence(Base):
    """Prélèvement ou revenu qui revient à intervalle régulier.

    `ancre` est la date de la première échéance. Toutes les suivantes s'en déduisent —
    jamais de l'échéance précédente, sinon une récurrence au 31 resterait bloquée au 28
    après son premier février (voir `domain/recurrence.py`).
    """

    __tablename__ = "recurrence"
    __table_args__ = (
        CheckConstraint("montant_centimes <> 0", name="ck_recurrence_montant_non_nul"),
        CheckConstraint("intervalle >= 1", name="ck_recurrence_intervalle"),
        CheckConstraint("fin is null or fin >= ancre", name="ck_recurrence_fin_apres_ancre"),
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

    ancre: Mapped[dt.date] = mapped_column(Date)
    unite: Mapped[UniteRecurrence] = mapped_column(String(16))
    intervalle: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    fin: Mapped[dt.date | None] = mapped_column(Date, default=None)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    cree_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    compte: Mapped[Compte] = relationship()
    categorie: Mapped[Categorie | None] = relationship()


class Plafond(Base):
    """Limite de dépense sur une catégorie, pour une période budgétaire.

    Le plafond est **personnel** : c'est la paie de son propriétaire qui découpe les
    périodes sur lesquelles il se mesure. Les plafonds partagés viendront avec les
    comptes joints, quand la question de la période commune sera tranchée.

    Le montant est stocké **positif** : un plafond est une limite, pas une dépense. La
    consommation, elle, se calcule et n'est jamais stockée.
    """

    __tablename__ = "plafond"
    __table_args__ = (
        CheckConstraint("montant_centimes > 0", name="ck_plafond_montant_positif"),
        UniqueConstraint(
            "utilisateur_id", "categorie_id", name="uq_plafond_par_categorie_et_personne"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE")
    )
    categorie_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categorie.id", ondelete="CASCADE")
    )
    montant_centimes: Mapped[int] = mapped_column(BigInteger)
    cree_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    categorie: Mapped[Categorie] = relationship()


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
        CheckConstraint(
            # Un virement n'est ni une paie ni une ouverture de période : les trois
            # marqueurs répondent à des questions différentes, mais une saisie fautive
            # les combinerait sans que rien ne proteste — et le virement ouvrirait alors
            # une période budgétaire, ou compterait comme un revenu.
            "not (virement_id is not null and (est_paie or est_ouverture))",
            name="ck_operation_virement_ni_paie_ni_ouverture",
        ),
        CheckConstraint(
            # Un ajustement n'est rien d'autre qu'un ajustement : ni paie, ni ouverture,
            # ni moitié de virement. Les combiner ferait ouvrir une période budgétaire ou
            # compter un revenu là où il n'y a qu'une correction.
            "not (est_ajustement and (est_paie or est_ouverture or virement_id is not null))",
            name="ck_operation_ajustement_seul"
        ),
        Index("ix_operation_compte_date", "compte_id", "date_operation"),
        Index("ix_operation_paie", "compte_id", "date_operation", postgresql_where="est_paie"),
        # Clé d'idempotence de la matérialisation, explicite et documentée : le job peut
        # être rejoué autant de fois qu'on veut sans jamais créer de doublon. Partielle,
        # car les opérations saisies à la main n'ont pas de récurrence.
        Index(
            "uq_operation_par_echeance",
            "recurrence_id",
            "date_operation",
            unique=True,
            postgresql_where="recurrence_id is not null",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    compte_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("compte.id", ondelete="CASCADE"))
    categorie_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categorie.id", ondelete="RESTRICT"), default=None
    )
    cree_par_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="RESTRICT")
    )
    recurrence_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("recurrence.id", ondelete="SET NULL"), default=None
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

    # Écartée volontairement : un prélèvement rejeté par la banque, une échéance qui n'est
    # finalement pas passée. La ligne RESTE en base — c'est ce qui empêche le job de
    # matérialisation de la recréer au passage suivant, la clé d'idempotence
    # `uq_operation_par_echeance` la voyant toujours.
    annulee: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Les deux moitiés d'un virement portent le MÊME identifiant. Ce n'est pas une clé
    # étrangère : il n'existe pas de table « virement », parce qu'un virement n'a aucune
    # donnée propre au-delà de ses deux opérations. Lui donner une table créerait une
    # seconde source pour le montant et la date, qui pourrait diverger des lignes.
    virement_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), default=None, index=True
    )

    # Écart enregistré pour mettre le solde d'accord avec celui de la banque. Compte dans
    # les soldes, jamais dans les dépenses : réparer une erreur de saisie de 20 € n'est
    # pas avoir dépensé 20 €.
    est_ajustement: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    compte: Mapped[Compte] = relationship()
    categorie: Mapped[Categorie | None] = relationship()


class Enveloppe(Base):
    """Part réservée de l'épargne, rattachée à une catégorie de dépense.

    Aucune colonne de solde : il se recalcule depuis `MouvementEnveloppe`, exactement
    comme le solde d'un compte se recalcule depuis ses opérations. Stocker un solde en
    ferait une seconde source de vérité, qui dériverait au premier mouvement oublié.
    """

    __tablename__ = "enveloppe"
    __table_args__ = (
        UniqueConstraint("foyer_id", "nom", name="uq_enveloppe_nom_par_foyer"),
        CheckConstraint(
            "cible_centimes is null or cible_centimes > 0",
            name="ck_enveloppe_cible_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    foyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("foyer.id", ondelete="RESTRICT"))
    cree_par_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="RESTRICT")
    )
    nom: Mapped[str] = mapped_column(String(80))

    # À quoi l'argent est promis. Facultatif : une réserve générale n'a pas de catégorie.
    categorie_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categorie.id", ondelete="RESTRICT"), default=None
    )

    # Sur quel compte cet argent DEVRAIT se trouver. Simple préférence de couverture :
    # elle ne provoque aucun mouvement bancaire, elle sert à comparer ce qui est promis à
    # ce qui est réellement en banque.
    compte_prefere_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("compte.id", ondelete="RESTRICT"), default=None
    )

    # `None` et non zéro : une enveloppe sans cible n'est pas une enveloppe pleine, et la
    # préparation mensuelle ne doit rien lui recommander plutôt que de recommander zéro.
    cible_centimes: Mapped[int | None] = mapped_column(BigInteger, default=None)
    date_cible: Mapped[dt.date | None] = mapped_column(Date, default=None)

    archive: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    cree_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    categorie: Mapped[Categorie | None] = relationship()
    mouvements: Mapped[list[MouvementEnveloppe]] = relationship(
        back_populates="enveloppe", cascade="all, delete-orphan"
    )


class MouvementEnveloppe(Base):
    """Une ligne du journal d'une enveloppe.

    Le montant est TOUJOURS positif : c'est le type qui dit le sens. Un montant signé
    rendrait possible une allocation négative — une reprise déguisée, invisible dans un
    journal filtré par type.
    """

    __tablename__ = "mouvement_enveloppe"
    __table_args__ = (
        CheckConstraint("montant_centimes > 0", name="ck_mouvement_enveloppe_positif"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    enveloppe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("enveloppe.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[TypeMouvementEnveloppe] = mapped_column(String(24))
    montant_centimes: Mapped[int] = mapped_column(BigInteger)
    date_mouvement: Mapped[dt.date] = mapped_column(Date)
    libelle: Mapped[str] = mapped_column(String(140), default="")

    # L'opération qui a puisé dans l'enveloppe, s'il y en a une. Facultatif : une
    # allocation ne vient d'aucune opération, c'est tout son propos.
    operation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("operation.id", ondelete="SET NULL"), default=None
    )

    cree_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    enveloppe: Mapped[Enveloppe] = relationship(back_populates="mouvements")
