from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlmodel import SQLModel, Session

from app.core.database import engine
from app.core.seed import (
    seed_admin_user,
    seed_categorias,
    seed_estados_pedido,
    seed_formas_pago,
    seed_ingredientes,
    seed_producto_ingredientes,
    seed_productos,
    seed_roles,
    seed_unidades_medida,
)

# Registrar modelos sin router propio en SQLModel.metadata antes de create_all
from app.modules.refresh_token import model as _refresh_token_model  # noqa: F401
from app.modules.rol import model as _rol_model  # noqa: F401
from app.modules.pago import model as _pago_model  # noqa: F401

# Routers de dominio
from app.modules.categoria.router import router_categoria
from app.modules.producto.router import router_producto
from app.modules.ingrediente.router import router_ingrediente
from app.modules.usuarios.router import auth as router_auth, admin as router_admin
from app.modules.rol.router import admin as router_rol_admin
from app.modules.direccion.router import router_direccion
from app.modules.unidad_medida.router import router_unidad_medida
from app.modules.pedido.router import router_pedido
from app.modules.ws.router import router_ws
from app.modules.cloudinary.router import router_cloudinary
from app.modules.pago.router import router_pago
from app.modules.estadisticas.router import router_estadisticas
from app.core.config import settings

# ─── Ciclo de vida ────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: crear tablas y seedear admin inicial
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed_roles(session)
        seed_admin_user(session)
        seed_estados_pedido(session)
        seed_formas_pago(session)
        seed_unidades_medida(session)
        seed_categorias(session)
        seed_productos(session)
        seed_ingredientes(session)
        seed_producto_ingredientes(session)
    yield
    # Shutdown: nada por ahora


app = FastAPI(lifespan=lifespan)


# ─── CORS ─────────────────────────────────────────────────────────────────────
# Con allow_credentials=True NO se puede usar "*": el navegador exige el origin
# exacto. Los subdominios de ngrok rotan en cada reinicio, así que se matchean
# por regex en vez de hardcodearlos.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "http://localhost:5173",
        "http://localhost:5174",
    ],
    allow_origin_regex=r"https://.*\.ngrok(-free)?\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Redirect de MercadoPago (auto_return HTTPS → localhost) ────────────────
@app.get("/pago/resultado")
def redirect_mp(status: str = Query(...), pedido_id: str = Query(...)):
    return RedirectResponse(
        f"{settings.MP_FRONTEND_URL}/pago/resultado?status={status}&pedido_id={pedido_id}"
    )


# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(router_categoria)
app.include_router(router_producto)
app.include_router(router_ingrediente)
app.include_router(router_auth)
app.include_router(router_admin)
app.include_router(router_rol_admin)
app.include_router(router_direccion)
app.include_router(router_unidad_medida)
app.include_router(router_pedido)
app.include_router(router_ws)
app.include_router(router_cloudinary)
app.include_router(router_pago)
app.include_router(router_estadisticas)
