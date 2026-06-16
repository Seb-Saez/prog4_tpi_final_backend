import json
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select
from sqlalchemy import ARRAY, BigInteger, event, TypeDecorator
from sqlalchemy.ext.compiler import compiles


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(type_, compiler, **kw):
    return "TEXT"


# Monkey-patch ARRAY bind_processor for SQLite so lists are serialized to JSON
_orig_bind_processor = ARRAY.bind_processor
_orig_result_processor = ARRAY.result_processor


def _patched_bind_processor(self, dialect):
    if dialect.name == "sqlite":
        def process(value):
            if value is not None:
                return json.dumps(list(value))
            return value
        return process
    return _orig_bind_processor(self, dialect)


def _patched_result_processor(self, dialect, coltype):
    if dialect.name == "sqlite":
        def process(value):
            if value is not None:
                return json.loads(value)
            return value
        return process
    return _orig_result_processor(self, dialect, coltype)


ARRAY.bind_processor = _patched_bind_processor
ARRAY.result_processor = _patched_result_processor


@compiles(BigInteger, "sqlite")
def _compile_bigint_sqlite(type_, compiler, **kw):
    return "INTEGER"


from app.core.config import settings as _settings
from main import app as _app
from app.core import database as _database
from app.core.database import get_session
import main as _main_mod

# Replace all PostgreSQL engine references with SQLite for tests.
# check_same_thread=False is required because TestClient runs lifespan in a separate thread.
_sqlite_engine = create_engine("sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False})
_database.engine = _sqlite_engine
_main_mod.engine = _sqlite_engine
from app.core.seed import seed_roles, seed_admin_user, seed_estados_pedido, seed_formas_pago
from app.core.security import create_access_token
from app.modules.usuarios.model import Usuario
from app.modules.rol.model import Rol, UsuarioRol
from app.modules.rol.enums import RolEnum
from app.modules.estado_pedido.model import EstadoPedido
from app.modules.forma_pago.model import FormaPago
from app.modules.pedido.model import Pedido
from app.modules.detalle_pedido.model import DetallePedido
from app.modules.historial_pedido.model import HistorialEstadoPedido
from app.modules.producto.model import Producto
from app.modules.categoria.model import Categoria
from app.modules.direccion.model import DireccionEntrega
from app.modules.pedido.enums import ModalidadEntrega
from decimal import Decimal


TEST_EMAIL = "test@mail.com"
TEST_PASSWORD = "Test1234!"
TEST_USERNAME = "testuser"
TEST_FULLNAME = "Test User"


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False})
    connection = engine.connect()
    SQLModel.metadata.create_all(connection)

    _session = Session(bind=connection)

    seed_roles(_session)
    seed_estados_pedido(_session)
    seed_formas_pago(_session)
    seed_admin_user(_session)

    def override_get_session():
        yield _session

    _app.dependency_overrides[get_session] = override_get_session

    yield _session

    _app.dependency_overrides.clear()
    _session.close()
    connection.close()


@pytest.fixture
def client(session):
    with TestClient(_app) as c:
        yield c


def _build_token(session, username: str) -> str:
    user = session.exec(select(Usuario).where(Usuario.username == username)).first()
    assert user is not None, f"User '{username}' not found"
    roles = session.exec(
        select(Rol.codigo)
        .join(UsuarioRol, UsuarioRol.rol_id == Rol.id)
        .where(UsuarioRol.usuario_id == user.id)
    ).all()
    payload = {"sub": user.username, "roles": list(roles)}
    return create_access_token(payload, token_version=user.token_version)


@pytest.fixture
def admin_token(session):
    return _build_token(session, _settings.ADMIN_INITIAL_USERNAME)


@pytest.fixture
def client_token(client: TestClient, session):
    resp = client.post("/api/v1/auth/register", json={
        "username": TEST_USERNAME,
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "full_name": TEST_FULLNAME,
    })
    assert resp.status_code == 201, f"register failed: {resp.text}"

    return _build_token(session, TEST_USERNAME)


@pytest.fixture
def admin_headers(client: TestClient, admin_token: str):
    client.cookies.clear()
    client.cookies.set("access_token", admin_token)
    return {}


@pytest.fixture
def client_headers(client: TestClient, client_token: str):
    client.cookies.clear()
    client.cookies.set("access_token", client_token)
    return {}


@pytest.fixture
def forma_pago_id(session) -> int:
    fp = session.exec(select(FormaPago).where(FormaPago.codigo == "EFECTIVO")).first()
    assert fp is not None, "FormaPago EFECTIVO not seeded"
    return fp.id


@pytest.fixture
def user_id(client_headers, client) -> int:
    resp = client.get("/api/v1/auth/me", headers=client_headers)
    assert resp.status_code == 200
    return resp.json()["id"]


@pytest.fixture
def producto_data() -> dict:
    return {
        "nombre": "Hamburguesa Clásica",
        "descripcion": "Carne, queso, lechuga y tomate",
        "precio_base": 100.00,
        "stock_cantidad": 10,
        "disponible": True,
    }
