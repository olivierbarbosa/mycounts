"""Espaces personnels et foyers multiples, sans perte de données.

Revision ID: e31a9b6427d0
Revises: c74b81e2a603
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e31a9b6427d0"
down_revision = "c74b81e2a603"
branch_labels = None
depends_on = None


TABLES_FINANCIERES = (
    "compte",
    "categorie",
    "recurrence",
    "plafond",
    "operation",
    "correspondance_import",
    "enveloppe",
    "mouvement_enveloppe",
)


def upgrade() -> None:
    op.create_table(
        "espace",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("nom", sa.String(length=120), nullable=False),
        sa.Column("proprietaire_personnel_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actif", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "cree_le", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "(type = 'personnel' and proprietaire_personnel_id is not null) or "
            "(type = 'foyer' and proprietaire_personnel_id is null)",
            name="ck_espace_proprietaire_selon_type",
        ),
        sa.ForeignKeyConstraint(
            ["proprietaire_personnel_id"], ["utilisateur.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "proprietaire_personnel_id", name="uq_espace_personnel_par_utilisateur"
        ),
    )
    op.create_table(
        "appartenance",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("utilisateur_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("espace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("actif", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "rejoint_le", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "role in ('proprietaire', 'administrateur', 'membre')",
            name="ck_appartenance_role",
        ),
        sa.ForeignKeyConstraint(["espace_id"], ["espace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["utilisateur_id"], ["utilisateur.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "utilisateur_id", "espace_id", name="uq_appartenance_utilisateur_espace"
        ),
    )
    op.create_index("ix_appartenance_espace_id", "appartenance", ["espace_id"])
    op.create_index("ix_appartenance_utilisateur_id", "appartenance", ["utilisateur_id"])
    op.create_index(
        "uq_appartenance_proprietaire_actif_par_espace",
        "appartenance",
        ["espace_id"],
        unique=True,
        postgresql_where=sa.text("actif and role = 'proprietaire'"),
    )

    op.create_table(
        "invitation_espace",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("espace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("courriel_destinataire", sa.String(length=254), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="membre", nullable=False),
        sa.Column("empreinte_jeton", sa.String(length=64), nullable=False),
        sa.Column("creee_par_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "cree_le", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expire_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("utilisee_le", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "role in ('administrateur', 'membre')", name="ck_invitation_espace_role"
        ),
        sa.ForeignKeyConstraint(["creee_par_id"], ["utilisateur.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["espace_id"], ["espace.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("empreinte_jeton", name="uq_invitation_espace_empreinte"),
    )
    op.create_index(
        "ix_invitation_espace_courriel_destinataire",
        "invitation_espace",
        ["courriel_destinataire"],
    )
    op.create_index("ix_invitation_espace_espace_id", "invitation_espace", ["espace_id"])

    for table in TABLES_FINANCIERES:
        op.add_column(table, sa.Column("espace_id", postgresql.UUID(as_uuid=True)))

    # Les foyers historiques deviennent des espaces FOYER avec le même UUID. Cela
    # conserve la capacité de relier les anciennes FK durant toute la migration.
    op.execute(
        """
        INSERT INTO espace (id, type, nom, actif, cree_le)
        SELECT id, 'foyer', nom, true, cree_le FROM foyer
        """
    )

    # La table temporaire rend le remappage reproductible dans toute cette transaction.
    op.execute(
        """
        CREATE TEMPORARY TABLE migration_espace_personnel (
            utilisateur_id uuid PRIMARY KEY,
            espace_id uuid UNIQUE NOT NULL
        ) ON COMMIT DROP;
        INSERT INTO migration_espace_personnel
        SELECT id, gen_random_uuid() FROM utilisateur;

        INSERT INTO foyer (id, nom, cree_le)
        SELECT m.espace_id, u.nom_affichage, u.cree_le
        FROM migration_espace_personnel m
        JOIN utilisateur u ON u.id = m.utilisateur_id;

        INSERT INTO espace (
            id, type, nom, proprietaire_personnel_id, actif, cree_le
        )
        SELECT m.espace_id, 'personnel', u.nom_affichage, u.id, true, u.cree_le
        FROM migration_espace_personnel m
        JOIN utilisateur u ON u.id = m.utilisateur_id;
        """
    )

    # Chaque identité possède son espace personnel et conserve son appartenance au
    # foyer historique. L'ancien propriétaire reste l'unique propriétaire du foyer.
    op.execute(
        """
        INSERT INTO appartenance (id, utilisateur_id, espace_id, role, actif, rejoint_le)
        SELECT gen_random_uuid(), u.id, m.espace_id, 'proprietaire', true, u.cree_le
        FROM utilisateur u
        JOIN migration_espace_personnel m ON m.utilisateur_id = u.id;

        INSERT INTO appartenance (id, utilisateur_id, espace_id, role, actif, rejoint_le)
        SELECT gen_random_uuid(), u.id, u.foyer_id,
               CASE WHEN u.est_proprietaire THEN 'proprietaire' ELSE 'membre' END,
               u.actif, u.cree_le
        FROM utilisateur u;
        """
    )

    # Comptes privés vers l'espace personnel ; comptes joints vers le foyer.
    op.execute(
        """
        UPDATE compte c
        SET espace_id = CASE WHEN c.prive THEN m.espace_id ELSE c.foyer_id END,
            foyer_id = CASE WHEN c.prive THEN m.espace_id ELSE c.foyer_id END
        FROM migration_espace_personnel m
        WHERE m.utilisateur_id = c.proprietaire_id;
        """
    )

    # Une catégorie historique reste la copie commune ; chaque utilisateur reçoit une
    # copie personnelle et une table de correspondance permet de remapper tous les liens.
    op.execute(
        """
        UPDATE categorie SET espace_id = foyer_id;
        CREATE TEMPORARY TABLE migration_categorie_personnelle (
            ancienne_id uuid NOT NULL,
            utilisateur_id uuid NOT NULL,
            nouvelle_id uuid UNIQUE NOT NULL,
            PRIMARY KEY (ancienne_id, utilisateur_id)
        ) ON COMMIT DROP;
        INSERT INTO migration_categorie_personnelle
        SELECT c.id, u.id, gen_random_uuid()
        FROM categorie c
        JOIN utilisateur u ON u.foyer_id = c.foyer_id;

        INSERT INTO categorie (
            id, foyer_id, espace_id, nom, nature, teinte, archivee, cree_le
        )
        SELECT mc.nouvelle_id, me.espace_id, me.espace_id,
               c.nom, c.nature, c.teinte, c.archivee, c.cree_le
        FROM migration_categorie_personnelle mc
        JOIN migration_espace_personnel me ON me.utilisateur_id = mc.utilisateur_id
        JOIN categorie c ON c.id = mc.ancienne_id;
        """
    )

    op.execute(
        """
        UPDATE operation o SET espace_id = c.espace_id
        FROM compte c WHERE c.id = o.compte_id;
        UPDATE operation o SET categorie_id = mc.nouvelle_id
        FROM compte c, migration_categorie_personnelle mc
        WHERE c.id = o.compte_id
          AND c.prive
          AND mc.ancienne_id = o.categorie_id
          AND mc.utilisateur_id = c.proprietaire_id;

        UPDATE recurrence r SET espace_id = c.espace_id
        FROM compte c WHERE c.id = r.compte_id;
        UPDATE recurrence r SET categorie_id = mc.nouvelle_id
        FROM compte c, migration_categorie_personnelle mc
        WHERE c.id = r.compte_id
          AND c.prive
          AND mc.ancienne_id = r.categorie_id
          AND mc.utilisateur_id = c.proprietaire_id;
        """
    )

    op.execute(
        """
        UPDATE plafond p
        SET espace_id = CASE WHEN p.vue = 'personnelle' THEN me.espace_id ELSE u.foyer_id END
        FROM utilisateur u
        JOIN migration_espace_personnel me ON me.utilisateur_id = u.id
        WHERE u.id = p.utilisateur_id;
        UPDATE plafond p SET categorie_id = mc.nouvelle_id
        FROM migration_categorie_personnelle mc
        WHERE p.vue = 'personnelle'
          AND mc.ancienne_id = p.categorie_id
          AND mc.utilisateur_id = p.utilisateur_id;

        UPDATE enveloppe e
        SET espace_id = CASE WHEN e.vue = 'personnelle' THEN me.espace_id ELSE u.foyer_id END,
            foyer_id = CASE WHEN e.vue = 'personnelle' THEN me.espace_id ELSE u.foyer_id END
        FROM utilisateur u
        JOIN migration_espace_personnel me ON me.utilisateur_id = u.id
        WHERE u.id = e.cree_par_id;
        UPDATE enveloppe e SET categorie_id = mc.nouvelle_id
        FROM migration_categorie_personnelle mc
        WHERE e.vue = 'personnelle'
          AND mc.ancienne_id = e.categorie_id
          AND mc.utilisateur_id = e.cree_par_id;
        UPDATE enveloppe e SET compte_prefere_id = NULL
        FROM compte c
        WHERE c.id = e.compte_prefere_id AND c.espace_id <> e.espace_id;

        UPDATE mouvement_enveloppe m SET espace_id = e.espace_id
        FROM enveloppe e WHERE e.id = m.enveloppe_id;
        UPDATE mouvement_enveloppe m SET operation_id = NULL
        FROM operation o
        WHERE o.id = m.operation_id AND o.espace_id <> m.espace_id;
        """
    )

    # Les correspondances communes restent au foyer et sont copiées dans chaque espace
    # personnel avec leur catégorie remappée.
    op.execute(
        """
        UPDATE correspondance_import SET espace_id = foyer_id;
        INSERT INTO correspondance_import (
            id, foyer_id, espace_id, genre, valeur, categorie_id, cree_le
        )
        SELECT gen_random_uuid(), me.espace_id, me.espace_id,
               ci.genre, ci.valeur, mc.nouvelle_id, ci.cree_le
        FROM correspondance_import ci
        JOIN utilisateur u ON u.foyer_id = ci.foyer_id
        JOIN migration_espace_personnel me ON me.utilisateur_id = u.id
        JOIN migration_categorie_personnelle mc
          ON mc.ancienne_id = ci.categorie_id AND mc.utilisateur_id = u.id;
        """
    )

    for table in TABLES_FINANCIERES:
        op.alter_column(table, "espace_id", nullable=False)
        op.create_foreign_key(
            f"fk_{table}_espace_id",
            table,
            "espace",
            ["espace_id"],
            ["id"],
            ondelete="CASCADE"
            if table not in {"compte", "correspondance_import", "enveloppe"}
            else "RESTRICT",
        )
        op.create_index(f"ix_{table}_espace_id", table, ["espace_id"])

    op.create_unique_constraint("uq_compte_nom_par_espace", "compte", ["espace_id", "nom"])
    op.create_unique_constraint("uq_categorie_nom_par_espace", "categorie", ["espace_id", "nom"])
    op.create_unique_constraint("uq_enveloppe_nom_par_espace", "enveloppe", ["espace_id", "nom"])
    op.create_unique_constraint(
        "uq_correspondance_import_par_espace",
        "correspondance_import",
        ["espace_id", "genre", "valeur"],
    )

    # Les FK composites font de l'isolation un invariant SQL : même une écriture qui
    # contournerait les repositories ne peut lier une opération à une catégorie ou un
    # compte d'un autre espace.
    for table in ("compte", "categorie", "recurrence", "operation", "enveloppe"):
        op.create_unique_constraint(f"uq_{table}_id_espace", table, ["id", "espace_id"])
    op.create_foreign_key(
        "fk_recurrence_compte_espace",
        "recurrence",
        "compte",
        ["compte_id", "espace_id"],
        ["id", "espace_id"],
    )
    op.create_foreign_key(
        "fk_recurrence_categorie_espace",
        "recurrence",
        "categorie",
        ["categorie_id", "espace_id"],
        ["id", "espace_id"],
    )
    op.create_foreign_key(
        "fk_operation_compte_espace",
        "operation",
        "compte",
        ["compte_id", "espace_id"],
        ["id", "espace_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_operation_categorie_espace",
        "operation",
        "categorie",
        ["categorie_id", "espace_id"],
        ["id", "espace_id"],
    )
    op.create_foreign_key(
        "fk_operation_recurrence_espace",
        "operation",
        "recurrence",
        ["recurrence_id", "espace_id"],
        ["id", "espace_id"],
    )
    op.create_foreign_key(
        "fk_plafond_categorie_espace",
        "plafond",
        "categorie",
        ["categorie_id", "espace_id"],
        ["id", "espace_id"],
    )
    op.create_foreign_key(
        "fk_correspondance_categorie_espace",
        "correspondance_import",
        "categorie",
        ["categorie_id", "espace_id"],
        ["id", "espace_id"],
    )
    op.create_foreign_key(
        "fk_enveloppe_categorie_espace",
        "enveloppe",
        "categorie",
        ["categorie_id", "espace_id"],
        ["id", "espace_id"],
    )
    op.create_foreign_key(
        "fk_enveloppe_compte_espace",
        "enveloppe",
        "compte",
        ["compte_prefere_id", "espace_id"],
        ["id", "espace_id"],
    )
    op.create_foreign_key(
        "fk_mouvement_enveloppe_espace",
        "mouvement_enveloppe",
        "enveloppe",
        ["enveloppe_id", "espace_id"],
        ["id", "espace_id"],
    )
    op.create_foreign_key(
        "fk_mouvement_operation_espace",
        "mouvement_enveloppe",
        "operation",
        ["operation_id", "espace_id"],
        ["id", "espace_id"],
    )


def downgrade() -> None:
    raise RuntimeError(
        "Le retour au modèle mono-foyer serait destructif après création de plusieurs "
        "foyers. Restaurer la sauvegarde pré-migration pour revenir en arrière."
    )
