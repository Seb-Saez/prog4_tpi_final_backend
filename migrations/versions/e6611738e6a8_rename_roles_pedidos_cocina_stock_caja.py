"""rename_roles_pedidos_cocina_stock_caja

Revision ID: e6611738e6a8
Revises: 86969d56e044
Create Date: 2026-06-16 18:08:09.234932

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'e6611738e6a8'
down_revision: Union[str, None] = '86969d56e044'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Renombrar roles: PEDIDOS → COCINA, STOCK → CAJA.
    # Se usa UPDATE idempotente — si las filas ya no existen con los códigos
    # antiguos, la sentencia no afecta ninguna fila y no falla.
    op.execute("UPDATE rol SET codigo = 'COCINA', descripcion = 'Gestionar y avanzar estados de pedidos en preparación' WHERE codigo = 'PEDIDOS'")
    op.execute("UPDATE rol SET codigo = 'CAJA', descripcion = 'Confirmar pedidos, actualizar stock e ingredientes' WHERE codigo = 'STOCK'")


def downgrade() -> None:
    op.execute("UPDATE rol SET codigo = 'PEDIDOS', descripcion = 'Avanzar estados de pedidos' WHERE codigo = 'COCINA'")
    op.execute("UPDATE rol SET codigo = 'STOCK', descripcion = 'Actualizar stock, gestionar productos, confirmar pedidos' WHERE codigo = 'CAJA'")
