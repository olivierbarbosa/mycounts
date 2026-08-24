"""Identité publique, MFA obligatoire, appareils fiables et outbox email.

Revision ID: e18c7d41a2b0
Revises: e846d42fb19c
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e18c7d41a2b0"
down_revision: str | None = "e846d42fb19c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Les identités déjà présentes ont été créées par l'administrateur et sont donc
    # réputées vérifiées. Les nouvelles n'ont aucun défaut et passent par le lien email.
    op.add_column(
        "utilisateur",
        sa.Column("courriel_verifie_le", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(sa.text("UPDATE utilisateur SET courriel_verifie_le = now()"))

    # Les sessions existantes restent valables pendant la migration. Toute session créée
    # ensuite choisit explicitement son niveau selon le MFA réellement fourni.
    op.add_column(
        "session_web",
        sa.Column(
            "second_facteur_satisfait",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.alter_column("session_web", "second_facteur_satisfait", server_default=sa.false())

    op.create_table(
        "jeton_identite",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("utilisateur_id", sa.UUID(), nullable=False),
        sa.Column("usage", sa.String(length=40), nullable=False),
        sa.Column("empreinte", sa.String(length=64), nullable=False),
        sa.Column("cree_le", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expire_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("utilise_le", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "usage in ('verification_courriel', 'reinitialisation_mot_de_passe')",
            name="ck_jeton_identite_usage",
        ),
        sa.ForeignKeyConstraint(["utilisateur_id"], ["utilisateur.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("empreinte", name="uq_jeton_identite_empreinte"),
    )
    op.create_index("ix_jeton_identite_expiration", "jeton_identite", ["expire_le"])

    op.create_table(
        "appareil_confiance",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("utilisateur_id", sa.UUID(), nullable=False),
        sa.Column("empreinte_secret", sa.String(length=64), nullable=False),
        sa.Column("nom", sa.String(length=120), nullable=False),
        sa.Column("cree_le", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("vu_le", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expire_le", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["utilisateur_id"], ["utilisateur.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("empreinte_secret", name="uq_appareil_confiance_empreinte"),
    )
    op.create_index("ix_appareil_confiance_expiration", "appareil_confiance", ["expire_le"])

    op.create_table(
        "courriel_sortant",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("utilisateur_id", sa.UUID(), nullable=False),
        sa.Column("cle_idempotence", sa.String(length=120), nullable=False),
        sa.Column("destinataire", sa.String(length=254), nullable=False),
        sa.Column("modele", sa.String(length=48), nullable=False),
        sa.Column("donnees", sa.JSON(), nullable=False),
        sa.Column("tentatives", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cree_le", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "prochaine_tentative_le",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("envoye_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("derniere_erreur", sa.String(length=240), nullable=True),
        sa.CheckConstraint("tentatives >= 0", name="ck_courriel_sortant_tentatives"),
        sa.ForeignKeyConstraint(["utilisateur_id"], ["utilisateur.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cle_idempotence", name="uq_courriel_sortant_idempotence"),
    )
    op.create_index(
        "ix_courriel_sortant_a_envoyer",
        "courriel_sortant",
        ["envoye_le", "prochaine_tentative_le"],
    )


def downgrade() -> None:
    op.drop_index("ix_courriel_sortant_a_envoyer", table_name="courriel_sortant")
    op.drop_table("courriel_sortant")
    op.drop_index("ix_appareil_confiance_expiration", table_name="appareil_confiance")
    op.drop_table("appareil_confiance")
    op.drop_index("ix_jeton_identite_expiration", table_name="jeton_identite")
    op.drop_table("jeton_identite")
    op.drop_column("session_web", "second_facteur_satisfait")
    op.drop_column("utilisateur", "courriel_verifie_le")
