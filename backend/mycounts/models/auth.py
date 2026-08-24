"""Tables d'authentification et d'appartenance au foyer.

`foyer_id` est présent dès maintenant, alors que l'interface n'expose aucun partage :
ajouter le périmètre après coup obligerait à toucher chaque requête de lecture du projet.
C'est le seul endroit où anticiper coûte moins cher que corriger.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mycounts.domain.espaces import RoleEspace, TypeEspace
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


class Espace(Base):
    """Frontière d'isolation des données financières.

    `proprietaire_personnel_id` n'est renseigné que pour un espace personnel. Son
    unicité garantit qu'une identité ne peut en recevoir qu'un seul, sans confondre ce
    lien structurel avec le rôle d'une appartenance de foyer.
    """

    __tablename__ = "espace"
    __table_args__ = (
        UniqueConstraint(
            "proprietaire_personnel_id", name="uq_espace_personnel_par_utilisateur"
        ),
        CheckConstraint(
            "(type = 'personnel' and proprietaire_personnel_id is not null) or "
            "(type = 'foyer' and proprietaire_personnel_id is null)",
            name="ck_espace_proprietaire_selon_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    type: Mapped[TypeEspace] = mapped_column(String(16))
    nom: Mapped[str] = mapped_column(String(120))
    proprietaire_personnel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE"), default=None
    )
    actif: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    cree_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Appartenance(Base):
    """Droit explicite d'une identité dans un espace."""

    __tablename__ = "appartenance"
    __table_args__ = (
        UniqueConstraint(
            "utilisateur_id", "espace_id", name="uq_appartenance_utilisateur_espace"
        ),
        CheckConstraint(
            "role in ('proprietaire', 'administrateur', 'membre')",
            name="ck_appartenance_role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE"), index=True
    )
    espace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("espace.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[RoleEspace] = mapped_column(String(20))
    actif: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    rejoint_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Utilisateur(Base):
    __tablename__ = "utilisateur"
    __table_args__ = (
        UniqueConstraint("courriel", name="uq_utilisateur_courriel"),
        CheckConstraint(
            "paies_par_cycle between 1 and 12", name="ck_utilisateur_paies_par_cycle"
        ),
        # Un seul propriétaire par foyer, garanti par la base et non par le code appelant :
        # deux membres capables de tout effacer, c'est le genre d'état qui ne se remarque
        # qu'au moment où l'un des deux s'en sert. L'index est partiel — il ne porte que
        # sur les lignes vraies — et vit dans la migration seule, comme celui de `Plafond` :
        # un `WHERE` ne s'exprime pas ici sans un `text()`, que le garde-fou n°7 refuse à
        # bon droit hors du repository.
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    foyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("foyer.id", ondelete="RESTRICT"))
    # Toujours stocké en minuscules normalisées : sans ça, « A@b.fr » et « a@b.fr »
    # créeraient deux comptes que l'unicité SQL ne verrait pas comme un doublon.
    courriel: Mapped[str] = mapped_column(String(254))
    nom_affichage: Mapped[str] = mapped_column(String(80))
    empreinte_mot_de_passe: Mapped[str] = mapped_column(String(255))
    actif: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    courriel_verifie_le: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    # Qui peut détruire le foyer et gérer ses membres. Une colonne explicite plutôt que
    # « le membre le plus ancien » : déduire un pouvoir d'une date de création en fait une
    # règle sans auteur, que le premier tri par `cree_le` écrit ailleurs contredirait.
    est_proprietaire: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    # Secret TOTP, en base32. `None` tant que la personne ne s'est pas enrôlée.
    #
    # En clair en base, et c'est un choix à connaître : le chiffrer exigerait une clé que
    # le serveur doit de toute façon détenir pour vérifier les codes, ce qui déplacerait le
    # secret sans le protéger. Ce qui protège vraiment, c'est que la base ne soit pas
    # lisible — voir le chiffrement des libellés et le chiffrement du disque.
    secret_totp: Mapped[str | None] = mapped_column(String(64), default=None)
    # Passe à vrai quand un PREMIER code a été vérifié, jamais à l'enregistrement du
    # secret. Sans cette distinction, une application mal configurée — mauvaise heure,
    # QR scanné à moitié — verrouillerait le compte : le serveur croirait l'enrôlement
    # fait, et aucun code ne fonctionnerait plus jamais.
    totp_actif: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    # Compteur RFC 6238 du dernier code accepté. Un code TOTP est valable pendant une
    # fenêtre : sans mémoriser sa position, l'intercepter une fois permet de le rejouer
    # autant de fois que voulu pendant cette fenêtre.
    dernier_compteur_totp: Mapped[int | None] = mapped_column(BigInteger, default=None)
    # Nombre de versements de salaire qui composent UN cycle budgétaire. À 2 (quinzaine),
    # seule une paie sur deux ouvre une période : sans ce réglage, une prime ferait
    # repartir tous les plafonds à zéro en plein mois.
    paies_par_cycle: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1"
    )
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


class InvitationEspace(Base):
    """Invitation ciblée vers un foyer, utilisable par une identité existante."""

    __tablename__ = "invitation_espace"
    __table_args__ = (
        UniqueConstraint("empreinte_jeton", name="uq_invitation_espace_empreinte"),
        CheckConstraint(
            "role in ('administrateur', 'membre')", name="ck_invitation_espace_role"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    espace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("espace.id", ondelete="CASCADE"), index=True
    )
    courriel_destinataire: Mapped[str] = mapped_column(String(254), index=True)
    role: Mapped[RoleEspace] = mapped_column(
        String(20), default=RoleEspace.MEMBRE, server_default="membre"
    )
    empreinte_jeton: Mapped[str] = mapped_column(String(64))
    creee_par_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE")
    )
    cree_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expire_le: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    utilisee_le: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class CodeDeSecours(Base):
    """Un code à usage unique, pour entrer sans son téléphone.

    **Haché, comme un mot de passe.** Quarante bits d'aléa ne se cassent pas par
    dictionnaire, mais un vol de dump donnerait sinon dix accès complets à chaque compte.

    **Consommé, jamais supprimé.** `utilise_le` marque l'usage et la ligne reste : savoir
    qu'un code de secours a servi, et quand, est exactement le genre de trace qu'on
    cherche après coup. Une ligne effacée ne raconte rien.
    """

    __tablename__ = "code_de_secours"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE")
    )
    empreinte: Mapped[str] = mapped_column(String(255))
    cree_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    utilise_le: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class Avatar(Base):
    """Image de profil, une par personne au plus.

    **Table à part, et non une colonne sur `utilisateur`.** Une image pèse mille fois ce
    que pèse le reste de la ligne : la laisser là ferait traîner cinquante kilo-octets
    dans chaque lecture de session, à chaque requête, pour un affichage qui n'en a besoin
    qu'une fois. Le coût serait invisible en développement et bien réel sur un téléphone.

    **En base et non sur le disque**, tranché par Olivier le 22 août 2026 : une seule
    chose à sauvegarder, et une seule à chiffrer le jour où la base le sera — ce qu'il a
    demandé, les données étant bancaires. Un fichier posé à côté échapperait à ce
    chiffrement, et resterait orphelin quand le compte part.

    Le contenu est déjà redimensionné et réencodé à l'écriture : ce qui entre ici est ce
    qui sortira, sans traitement à la lecture.
    """

    __tablename__ = "avatar"

    utilisateur_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE"), primary_key=True
    )
    # `LargeBinary` sans longueur : PostgreSQL rend un `bytea`, dont la taille n'est pas
    # déclarée. La borne réelle est posée à l'entrée, dans le domaine, où elle peut
    # produire un message plutôt qu'une erreur de base.
    contenu: Mapped[bytes] = mapped_column(LargeBinary)
    type_mime: Mapped[str] = mapped_column(String(40))
    # Sert l'en-tête `ETag` : sans lui, le navigateur garde l'ancienne image après un
    # changement, et l'on croit que l'envoi a échoué.
    modifie_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


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
    second_facteur_satisfait: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )


class JetonIdentite(Base):
    """Jeton opaque à usage unique pour vérifier ou récupérer une identité."""

    __tablename__ = "jeton_identite"
    __table_args__ = (
        UniqueConstraint("empreinte", name="uq_jeton_identite_empreinte"),
        CheckConstraint(
            "usage in ('verification_courriel', 'reinitialisation_mot_de_passe')",
            name="ck_jeton_identite_usage",
        ),
        Index("ix_jeton_identite_expiration", "expire_le"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE")
    )
    usage: Mapped[str] = mapped_column(String(40))
    empreinte: Mapped[str] = mapped_column(String(64))
    cree_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expire_le: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    utilise_le: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class AppareilConfiance(Base):
    """Appareil autorisé à éviter le TOTP pendant trente jours, révocable seul."""

    __tablename__ = "appareil_confiance"
    __table_args__ = (
        UniqueConstraint("empreinte_secret", name="uq_appareil_confiance_empreinte"),
        Index("ix_appareil_confiance_expiration", "expire_le"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE")
    )
    empreinte_secret: Mapped[str] = mapped_column(String(64))
    nom: Mapped[str] = mapped_column(String(120), default="Appareil")
    cree_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    vu_le: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expire_le: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))


class CourrielSortant(Base):
    """Boîte d'envoi transactionnelle, sans contenu financier ni secret SMTP."""

    __tablename__ = "courriel_sortant"
    __table_args__ = (
        UniqueConstraint("cle_idempotence", name="uq_courriel_sortant_idempotence"),
        Index("ix_courriel_sortant_a_envoyer", "envoye_le", "prochaine_tentative_le"),
        CheckConstraint("tentatives >= 0", name="ck_courriel_sortant_tentatives"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE")
    )
    cle_idempotence: Mapped[str] = mapped_column(String(120))
    destinataire: Mapped[str] = mapped_column(String(254))
    modele: Mapped[str] = mapped_column(String(48))
    donnees: Mapped[dict[str, str]] = mapped_column(JSON)
    tentatives: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cree_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    prochaine_tentative_le: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    envoye_le: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    derniere_erreur: Mapped[str | None] = mapped_column(String(240), default=None)


class TentativeConnexion(Base):
    """Compteur pseudonymisé d'échecs dans une fenêtre fixe.

    Aucun lien vers `Utilisateur` : une adresse inconnue doit produire exactement le même
    seau qu'une adresse connue, sans transformer cette table en liste des comptes.
    """

    __tablename__ = "tentative_connexion"
    __table_args__ = (
        CheckConstraint("echecs > 0", name="ck_tentative_connexion_echecs_positifs"),
        CheckConstraint(
            "portee in ('identifiant', 'couple', 'origine', 'action')",
            name="ck_tentative_connexion_portee",
        ),
        Index("ix_tentative_connexion_fenetre", "fenetre_debut"),
    )

    empreinte: Mapped[str] = mapped_column(String(64), primary_key=True)
    portee: Mapped[str] = mapped_column(String(16), primary_key=True)
    fenetre_debut: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    echecs: Mapped[int] = mapped_column(Integer, default=1)
