"""Compléter le périmètre des écritures SQL et préserver les cascades.

Revision ID: e846d42fb19c
Revises: e31a9b6427d0
"""

from __future__ import annotations

from alembic import op

revision = "e846d42fb19c"
down_revision = "e31a9b6427d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # La FK composite doit conserver la cascade déjà portée par la FK simple : supprimer
    # un compte emporte ses opérations, sans que la contrainte d'isolation ne la bloque.
    op.drop_constraint("fk_operation_compte_espace", "operation", type_="foreignkey")
    op.create_foreign_key(
        "fk_operation_compte_espace",
        "operation",
        "compte",
        ["compte_id", "espace_id"],
        ["id", "espace_id"],
        ondelete="CASCADE",
    )

    # Les triggers ne choisissent jamais un espace arbitraire : ils le recopient depuis
    # le parent déjà désigné. Ils couvrent les scripts de maintenance et imports SQL qui
    # ne passent pas encore par les constructeurs V1, tout en laissant les FK composites
    # refuser une valeur explicite contradictoire.
    op.execute(
        """
        CREATE FUNCTION mycounts_espace_depuis_foyer() RETURNS trigger AS $$
        BEGIN
          IF NEW.espace_id IS NULL THEN NEW.espace_id := NEW.foyer_id; END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE FUNCTION mycounts_espace_depuis_compte() RETURNS trigger AS $$
        BEGIN
          IF NEW.espace_id IS NULL THEN
            SELECT espace_id INTO NEW.espace_id FROM compte WHERE id = NEW.compte_id;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE FUNCTION mycounts_espace_depuis_categorie() RETURNS trigger AS $$
        BEGIN
          IF NEW.espace_id IS NULL THEN
            SELECT espace_id INTO NEW.espace_id FROM categorie WHERE id = NEW.categorie_id;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE FUNCTION mycounts_espace_depuis_enveloppe() RETURNS trigger AS $$
        BEGIN
          IF NEW.espace_id IS NULL THEN
            SELECT espace_id INTO NEW.espace_id FROM enveloppe WHERE id = NEW.enveloppe_id;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_compte_espace BEFORE INSERT ON compte
          FOR EACH ROW EXECUTE FUNCTION mycounts_espace_depuis_foyer();
        CREATE TRIGGER trg_categorie_espace BEFORE INSERT ON categorie
          FOR EACH ROW EXECUTE FUNCTION mycounts_espace_depuis_foyer();
        CREATE TRIGGER trg_correspondance_import_espace BEFORE INSERT ON correspondance_import
          FOR EACH ROW EXECUTE FUNCTION mycounts_espace_depuis_foyer();
        CREATE TRIGGER trg_enveloppe_espace BEFORE INSERT ON enveloppe
          FOR EACH ROW EXECUTE FUNCTION mycounts_espace_depuis_foyer();
        CREATE TRIGGER trg_recurrence_espace BEFORE INSERT ON recurrence
          FOR EACH ROW EXECUTE FUNCTION mycounts_espace_depuis_compte();
        CREATE TRIGGER trg_operation_espace BEFORE INSERT ON operation
          FOR EACH ROW EXECUTE FUNCTION mycounts_espace_depuis_compte();
        CREATE TRIGGER trg_plafond_espace BEFORE INSERT ON plafond
          FOR EACH ROW EXECUTE FUNCTION mycounts_espace_depuis_categorie();
        CREATE TRIGGER trg_mouvement_enveloppe_espace BEFORE INSERT ON mouvement_enveloppe
          FOR EACH ROW EXECUTE FUNCTION mycounts_espace_depuis_enveloppe();
        """
    )


def downgrade() -> None:
    for table in (
        "compte",
        "categorie",
        "correspondance_import",
        "enveloppe",
        "recurrence",
        "operation",
        "plafond",
        "mouvement_enveloppe",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_espace ON {table}")
    for fonction in (
        "mycounts_espace_depuis_enveloppe",
        "mycounts_espace_depuis_categorie",
        "mycounts_espace_depuis_compte",
        "mycounts_espace_depuis_foyer",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {fonction}()")
    op.drop_constraint("fk_operation_compte_espace", "operation", type_="foreignkey")
    op.create_foreign_key(
        "fk_operation_compte_espace",
        "operation",
        "compte",
        ["compte_id", "espace_id"],
        ["id", "espace_id"],
    )
