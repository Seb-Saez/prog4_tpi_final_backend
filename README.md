# FoodStore — Backend

API REST + WebSocket del sistema de gestión de pedidos de comida, construida con
**FastAPI**, **SQLModel** y **PostgreSQL**. Aplica arquitectura por capas
(`router → service → unit_of_work → repository → model`) con módulos por feature.

## Stack

| Capa | Tecnología |
|------|-----------|
| Framework | FastAPI (REST + WebSocket + OpenAPI) |
| ORM / Schemas | SQLModel + Pydantic v2 |
| Base de datos | PostgreSQL 15+ |
| Migraciones | Alembic |
| Auth | JWT (PyJWT) + bcrypt + RBAC (4 roles) |
| Pagos | MercadoPago (Checkout PRO + webhook IPN) |
| Imágenes | Cloudinary |
| Tests | pytest + TestClient (SQLite in-memory) |

## Estructura

```
backend/
├── alembic.ini              # Configuración de Alembic
├── migrations/              # Migraciones de base de datos
│   ├── env.py
│   └── versions/            # initial schema v7 + sucesivas
├── main.py                  # Punto de entrada (app FastAPI + routers + lifespan)
├── requirements.txt
└── app/
    ├── core/                # Infra transversal
    │   ├── config.py        # Settings desde variables de entorno
    │   ├── database.py      # Engine + get_session
    │   ├── unit_of_work.py  # UoW base (commit/rollback automático)
    │   ├── repository.py    # BaseRepository[T] genérico
    │   ├── security.py      # Hashing + JWT
    │   ├── rate_limit.py    # Rate limiting (login/register: 5 / 15 min)
    │   ├── websocket.py     # ConnectionManager + broadcast post-commit
    │   └── seed.py          # Seed idempotente (roles, estados, etc.)
    └── modules/             # Un paquete por feature
        ├── usuarios/  rol/  direccion/      # Identidad y acceso
        ├── categoria/ producto/ ingrediente/ unidad_medida/
        ├── pedido/    detalle_pedido/ historial_pedido/ estado_pedido/
        ├── pago/      forma_pago/           # MercadoPago
        ├── cloudinary/                      # Uploads
        ├── estadisticas/                    # KPIs del dashboard
        └── ws/                              # Endpoints WebSocket
```

Cada feature con lógica sigue: `model.py`, `schema.py`, `repository.py`,
`unit_of_work.py`, `service.py`, `router.py`.

## Requisitos

- Python 3.12+
- PostgreSQL 15+ (o Docker)

## Instalación y arranque (máquina limpia)

```bash
cd backend

# 1) Entorno virtual
python3 -m venv .venv
source .venv/bin/activate        # Linux/Mac
# .venv\Scripts\activate         # Windows

# 2) Dependencias
pip install -r requirements.txt

# 3) Variables de entorno (ver tabla abajo) — exportarlas o usar un archivo .env
export SECRET_KEY="cambiame-por-una-clave-de-al-menos-32-caracteres"
export ADMIN_INITIAL_PASSWORD="Admin1234!"
# ...resto de POSTGRES_*, MP_*, CLOUDINARY_* según necesidad

# 4) Crear el esquema con Alembic
alembic upgrade head

# 5) Levantar el servidor
uvicorn main:app --reload
```

El servidor queda en `http://localhost:8000`. La documentación interactiva:

- Swagger UI → `http://localhost:8000/docs`
- ReDoc → `http://localhost:8000/redoc`

> Con Docker: `docker compose up` desde la raíz del repo levanta PostgreSQL +
> backend + los dos frontends.

## Variables de entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `POSTGRES_USER` | Usuario de PostgreSQL | `postgres` |
| `POSTGRES_PASSWORD` | Password de PostgreSQL | `password` |
| `POSTGRES_DB` | Nombre de la base | `foodstore` |
| `POSTGRES_HOST` | Host de PostgreSQL | `localhost` |
| `POSTGRES_PORT` | Puerto de PostgreSQL | `5432` |
| `SECRET_KEY` | Clave para firmar JWT (**mín. 32 chars, obligatoria**) | — |
| `ALGORITHM` | Algoritmo JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiración del access token | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Expiración del refresh token | `7` |
| `COOKIE_SECURE` | Cookies solo por HTTPS | `False` |
| `COOKIE_SAMESITE` | SameSite de la cookie (`lax`/`strict`/`none`) | `lax` |
| `ADMIN_INITIAL_USERNAME` | Usuario admin seedeado | `admin` |
| `ADMIN_INITIAL_EMAIL` | Email admin seedeado | `admin@foodstore.local` |
| `ADMIN_INITIAL_PASSWORD` | Password admin (**obligatoria, mín. 8**) | — |
| `MP_ACCESS_TOKEN` | Access Token de MercadoPago (backend) | — |
| `MP_NOTIFICATION_URL` | URL pública para el webhook IPN (ej. ngrok) | — |
| `MP_FRONTEND_URL` | URL del frontend para las `back_urls` | `http://localhost:5173` |
| `CLOUDINARY_CLOUD_NAME` | Cloud name de Cloudinary | `""` |
| `CLOUDINARY_API_KEY` | API Key de Cloudinary (no exponer) | `""` |
| `CLOUDINARY_API_SECRET` | API Secret de Cloudinary (secreto) | `""` |

> `DATABASE_URL` se construye automáticamente a partir de las variables
> `POSTGRES_*` (campo computado en `config.py`).

## Migraciones (Alembic)

El esquema se gestiona con Alembic. La migración inicial (`initial schema v7`)
ya está versionada en `migrations/versions/`.

```bash
# Aplicar todas las migraciones pendientes
alembic upgrade head

# Generar una nueva migración tras cambiar un modelo
alembic revision --autogenerate -m "descripcion del cambio"

# Volver atrás una revisión
alembic downgrade -1
```

Alembic toma la URL de conexión de las variables `POSTGRES_*` vía
`app.core.config.settings` (ver `migrations/env.py`).

## Seed de datos

El seed es **idempotente** y se ejecuta automáticamente en el `lifespan` al
arrancar la app (`app/core/seed.py`). Carga:

- Roles: `ADMIN`, `PEDIDOS`, `STOCK`, `CLIENT`
- Estados de pedido (con `es_terminal` / `permite_cancelar`)
- Formas de pago: `EFECTIVO`, `TRANSFERENCIA`, `MERCADOPAGO`
- Unidades de medida: `kg`, `g`, `L`, `ml`, `ud`, `porciones`
- Usuario admin inicial (según variables `ADMIN_INITIAL_*`)
- Catálogo de demo: categorías, productos e ingredientes

## Tests

Suite de integración con `pytest` + `TestClient` sobre SQLite in-memory.

```bash
# SECRET_KEY y ADMIN_INITIAL_PASSWORD son obligatorias también para los tests
SECRET_KEY="test-secret-key-of-at-least-32-characters" \
ADMIN_INITIAL_PASSWORD="Admin1234!" \
pytest -q
```

Cubre: auth (login/register/logout/rate-limit), pedidos (FSM, cancelación con
motivo — RN-05, historial), pagos, uploads (Cloudinary), estadísticas
(excluyendo `CANCELADO`) y WebSocket.

> El test de `/estadisticas/ventas-por-periodo` se omite (`skip`) en SQLite
> porque usa `func.to_char`, específico de PostgreSQL.

## Endpoints principales

Prefijo común: `/api/v1`. Errores en formato JSON. WebSocket bajo `/ws`.

### Auth
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/auth/register` | Registro (rate limited 5/15min) |
| POST | `/auth/token` | Login (rate limited 5/15min) |
| POST | `/auth/refresh` | Renovar access token |
| POST | `/auth/logout` | Cerrar sesión + revocar refresh |
| GET | `/auth/me` | Usuario actual |

### Productos / Catálogo
| Método | Ruta | Rol |
|--------|------|-----|
| GET | `/productos` · `/productos/{id}` | Público |
| POST · PUT · DELETE | `/productos` · `/productos/{id}` | ADMIN |
| PATCH | `/productos/{id}/disponibilidad` | ADMIN, STOCK |
| PATCH | `/productos/{id}/imagenes` | ADMIN |
| GET · POST | `/productos/{id}/ingredientes` | Público / ADMIN |

### Pedidos
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/pedidos` | Crear desde el carrito (CLIENT) |
| GET | `/pedidos/mios` | Pedidos propios |
| GET | `/pedidos` | Todos (ADMIN/PEDIDOS) |
| GET | `/pedidos/{id}` | Detalle (dueño/ADMIN/PEDIDOS) |
| GET | `/pedidos/{id}/historial` | Historial append-only, ASC |
| PATCH | `/pedidos/{id}/avanzar` | Avanza el estado (ADMIN/PEDIDOS) |
| DELETE | `/pedidos/{id}` | Cancela el pedido — **motivo obligatorio (RN-05)** |

### Pagos (MercadoPago)
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/pagos/preferencia/{pedido_id}` | Crea preferencia (idempotency key UUID por backend) |
| GET | `/pagos/{pedido_id}` | Pago asociado a un pedido |
| POST | `/pagos/webhook` | Webhook IPN (público, notifica por WS) |

### Uploads (Cloudinary)
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/upload` | Sube imagen (valida MIME + 5 MB máx.) |
| DELETE | `/uploads/imagen/{public_id}` | Elimina por `public_id` |

### Estadísticas (rol ADMIN)
`/estadisticas/resumen` · `/ventas-por-periodo` · `/productos-mas-vendidos` ·
`/pedidos-por-estado` · `/ventas-por-categoria`

### WebSocket
| Ruta | Descripción |
|------|-------------|
| `/ws/pedidos` | Feed de cambios de estado de pedidos |
| `/cocina/ws` | Feed para staff (ADMIN/PEDIDOS) |

## Patrones aplicados

Repository · Unit of Work · Service Layer · Snapshot (precios/nombres inmutables
en el pedido) · Soft Delete (`deleted_at`) · Audit Trail append-only
(`HistorialEstadoPedido`) · State Machine (FSM de pedidos) · Idempotent Payments
· Connection Pool (WebSocket) · Webhook.
