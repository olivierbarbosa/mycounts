"""Second facteur : secret TOTP et codes de secours.

`totp_actif` est distinct du secret, et ce n'est pas une redondance : le secret est écrit
dès qu'on montre le QR, l'activation seulement quand un PREMIER code a été vérifié. Sans
cette distinction, une application mal configurée verrouillerait le compte — le serveur
croirait l'enrôlement fait, et aucun code ne marcherait plus.

Revision ID: d5a90e3c71b8
Revises: c3f81a5d47e9
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d5a90e3c71b8"
down_revision = "c3f81a5d47e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("utilisateur", sa.Column("secret_totp", sa.String(length=64), nullable=True))
    op.add_column(
        "utilisateur",
        sa.Column(
            "totp_actif", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.create_table(
        "code_de_secours",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "utilisateur_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("utilisateur.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("empreinte", sa.String(length=255), nullable=False),
        sa.Column(
            "cree_le", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("utilise_le", sa.DateTime(timezone=True), nullable=True),
    )
    # Les codes se cherchent toujours par personne, et jamais autrement : sans cet index,
    # chaque tentative de connexion par code balaierait la table entière.
    op.create_index(
        "ix_code_de_secours_utilisateur", "code_de_secours", ["utilisateur_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_code_de_secours_utilisateur", table_name="code_de_secours")
    op.drop_table("code_de_secours")
    op.drop_column("utilisateur", "totp_actif")
    op.drop_column("utilisateur", "secret_totp")
