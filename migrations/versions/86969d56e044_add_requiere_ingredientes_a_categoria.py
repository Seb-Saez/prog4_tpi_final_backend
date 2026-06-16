"""add_requiere_ingredientes_a_categoria

Revision ID: 86969d56e044
Revises: 8ff5ea5987af
Create Date: 2026-06-16 18:07:43.980996

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '86969d56e044'
down_revision: Union[str, None] = '8ff5ea5987af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agrega el flag requiere_ingredientes con default=True para filas existentes.
    op.add_column(
        'categoria',
        sa.Column(
            'requiere_ingredientes',
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column('categoria', 'requiere_ingredientes')
