# FoodStore Backend

Backend del sistema de gestión de FoodStore construido con FastAPI.

## Tecnologías

- **FastAPI**: Framework web moderno y rápido
- **SQLModel**: ORM con soporte para SQLAlchemy
- **PostgreSQL**: Base de datos relacional
- **Python 3.10+**: Lenguaje de programación

## Estructura del Proyecto

```
FS-backend/
├── app/
│   ├── categoria/       # Módulo de categorías
│   │   ├── model.py     # Modelo SQLModel
│   │   ├── schema.py    # Esquemas Pydantic
│   │   ├── service.py   # Lógica de negocio
│   │   ├── router.py    # Endpoints API
│   │   ├── repository.py
│   │   └── unit_of_work.py
│   ├── ingrediente/      # Módulo de ingredientes
│   │   ├── model.py
│   │   ├── schema.py
│   │   ├── service.py
│   │   ├── router.py
│   │   ├── repository.py
│   │   └── unit_of_work.py
│   ├── producto/        # Módulo de productos
│   │   ├── model.py
│   │   ├── schema.py
│   │   ├── service.py
│   │   ├── router.py
│   │   ├── repository.py
│   │   └── unit_of_work.py
│   ├── producto_categoria/    # Relación N:N
│   ├── producto_ingrediente/  # Relación N:N
│   └── core/
│       ├── database.py   # Configuración DB
│       └── repository.py
├── main.py              # Punto de entrada
└── requirements.txt     # Dependencias
```

## Instalación

1. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno:
```bash
# Crear archivo .env
DATABASE_URL=postgresql://user:password@localhost:5432/foodstore
```

4. Ejecutar el servidor:
```bash
python main.py
```

El servidor estará disponible en `http://localhost:8000`

## Documentación API

FastAPI proporciona documentación automática en:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Modelos de Datos

### Producto
- id (PK)
- nombre (string)
- descripcion (string)
- precio_base (float)
- stock_cantidad (int)
- disponible (boolean)
- imagenes_url (string, opcional)
- categorias (relación N:N)
- ingredientes (relación N:N)
- created_at, updated_at, deleted_at

### Categoria
- id (PK)
- nombre (string)
- descripcion (string)
- imagen_url (string, opcional)
- productos (relación N:N)

### Ingrediente
- id (PK)
- nombre (string)
- descripcion (string)
- es_alergeno (boolean)
- productos (relación N:N)

## Patrones de Diseño

- **Repository Pattern**: Abstracción de acceso a datos
- **Unit of Work**: Transacciones atómicas
- **Service Layer**: Lógica de negocio separada
- **Schema Validation**: Validación con Pydantic

## Endpoints Disponibles

### Productos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/productos/` | Listar (paginado) |
| POST | `/productos/` | Crear |
| GET | `/productos/{id}` | Ver por ID |
| PATCH | `/productos/{id}` | Actualizar |
| DELETE | `/productos/{id}` | Eliminar |

### Categorías
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/categorias/` | Listar (paginado) |
| POST | `/categorias/` | Crear |
| GET | `/categorias/{id}` | Ver por ID |
| PATCH | `/categorias/{id}` | Actualizar |
| DELETE | `/categorias/{id}` | Eliminar |

### Ingredientes
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/ingredientes/` | Listar (paginado) |
| POST | `/ingredientes/` | Crear |
| GET | `/ingredientes/{id}` | Ver por ID |
| PATCH | `/ingredientes/{id}` | Actualizar |
| DELETE | `/ingredientes/{id}` | Eliminar |

## Query Parameters

### Productos
- `skip`: Número de registros a omitir
- `limit`: Límite de registros (máx 100)
- `disponible`: Filtrar por disponibilidad (true/false)

### Categorías
- `skip`: Número de registros a omitir
- `limit`: Límite de registros (máx 100)

### Ingredientes
- `skip`: Número de registros a omitir
- `limit`: Límite de registros (máx 100)
- `es_alergeno`: Filtrar por alérgenos (true/false)

## Ejemplos de Uso

```bash
# Listar productos (primera página)
curl http://localhost:8000/productos/

# Listar productos con filtros
curl "http://localhost:8000/productos/?disponible=true&limit=10&skip=0"

# Crear producto
curl -X POST http://localhost:8000/productos/ \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Pizza Margarita", "descripcion": "Pizza clásica", "precio_base": 1500, "stock_cantidad": 10}'

# Listar categorías
curl http://localhost:8000/categorias/

# Listar ingredientes (solo alérgenos)
curl "http://localhost:8000/ingredientes/?es_alergeno=true"
```


