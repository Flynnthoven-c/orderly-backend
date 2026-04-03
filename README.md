# Orderly Backend

API para gestión de pedidos de comida rápida con chatbot WhatsApp.
Plataforma multi-tenant: cada negocio tiene su propio menú, clientes y reglas de lealtad.

**Producción:** https://orderly-api-production-1722.up.railway.app

## Stack

- **FastAPI** + Uvicorn
- **SQLAlchemy** async + PostgreSQL
- **Alembic** para migraciones
- **OpenAI** GPT-4o-mini para chatbot WhatsApp
- **Twilio** WhatsApp API
- **JWT** para autenticación (30 días de sesión)

## Desarrollo local

### 1. Instalar dependencias

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales
```

### 3. Base de datos

Necesitas PostgreSQL corriendo localmente:

```bash
createdb orderly
alembic upgrade head
python -m app.seeds   # 1 negocio demo, 5 productos, 2 reglas de lealtad
```

Credenciales del seed:
- **Negocio demo:** `demo@burgerpalace.com` / `demo123`
- **Admin:** configurable en .env (`ADMIN_EMAIL` / `ADMIN_PASSWORD`)

### 4. Iniciar el servidor

```bash
uvicorn app.main:app --reload --port 8000
```

Docs interactiva en: http://localhost:8000/docs

### 5. Webhook de Twilio con ngrok

Para recibir mensajes de WhatsApp en desarrollo local:

```bash
ngrok http 8000
```

Copiar la URL de ngrok y configurar en Twilio Console:
`https://tu-url.ngrok.io/webhook/whatsapp`

## Deploy en Railway

### Pasos

1. Crear proyecto en Railway con plugin de PostgreSQL
2. Crear un servicio y hacer deploy con `railway up` o conectar el repo de GitHub
3. Generar un dominio público: `railway domain`
4. Configurar variables de entorno:

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DATABASE_URL` | PostgreSQL (Railway la provee, usar la interna) | `postgresql://...` |
| `JWT_SECRET` | Secreto para firmar tokens JWT | `tu-secreto-seguro` |
| `ADMIN_EMAIL` | Email del administrador de la plataforma | `admin@orderly.com` |
| `ADMIN_PASSWORD` | Contraseña del admin | `tu-password-seguro` |
| `OPENAI_API_KEY` | API key de OpenAI | `sk-...` |
| `TWILIO_ACCOUNT_SID` | Account SID de Twilio | `ACxxxx` |
| `TWILIO_AUTH_TOKEN` | Auth Token de Twilio | `xxxx` |
| `ALLOWED_ORIGINS` | Dominio(s) del frontend (separados por coma) | `https://orderly.vercel.app` |

5. Railway usa el start command del `railway.toml`: ejecuta migraciones y luego el servidor
6. Después del primer deploy, ejecutar seeds: `railway run python -m app.seeds`

### Notas de deploy

- Los datos de cada negocio (nombre, WhatsApp, moneda, etc.) se configuran desde el panel admin
- El bot identifica automáticamente el negocio por el número de WhatsApp al que le escriben
- No se necesitan variables de entorno por negocio individual

## API Endpoints

### Autenticación
- `POST /auth/login` — Login unificado (admin y negocio), retorna JWT de 30 días
- `GET /auth/me` — Datos del negocio autenticado

### Admin (requiere JWT admin)
- `GET /admin/businesses` — Lista negocios con stats
- `POST /admin/businesses` — Crear negocio
- `PUT /admin/businesses/:id` — Editar negocio
- `GET /admin/stats` — Stats globales de la plataforma

### Productos
- `GET /products?business_id=X` — Lista
- `POST /products` — Crear
- `PUT /products/:id` — Editar
- `DELETE /products/:id` — Desactivar

### Pedidos
- `GET /orders?business_id=X` — Lista con filtros (estado, canal, fecha)
- `GET /orders/:id` — Detalle
- `POST /orders` — Crear pedido presencial
- `PUT /orders/:id/status` — Cambiar estado

### Clientes
- `GET /customers?business_id=X&search=...` — Lista con búsqueda
- `GET /customers/:id` — Perfil completo con historial y lealtad
- `POST /customers` — Registrar cliente
- `POST /customers/:id/purchase` — Registrar compra presencial

### Lealtad
- `GET /loyalty/rules?business_id=X` — Reglas
- `POST /loyalty/rules` — Crear regla
- `PUT /loyalty/rules/:id` — Editar regla
- `GET /loyalty/progress/:customer_id` — Progreso del cliente

### Dashboard
- `GET /dashboard/stats?business_id=X` — Ventas, pedidos activos, top producto

### Chatbot
- `POST /webhook/whatsapp` — Webhook de Twilio

## Configurar número dedicado de WhatsApp en Twilio

1. Comprar un número en Twilio con capacidad WhatsApp
2. Crear cuenta en Meta Business Manager para el negocio del cliente
3. Verificar el negocio en Meta (1-3 días hábiles)
4. Configurar perfil de WhatsApp Business con nombre, foto y descripción del negocio
5. En Twilio Console > Messaging > WhatsApp Senders, apuntar el webhook a:
   `https://orderly-api-production-1722.up.railway.app/webhook/whatsapp`
6. En el panel admin de Orderly, registrar el negocio con el número de WhatsApp

Cada negocio tiene su propio número. El bot identifica a cuál negocio pertenece
el mensaje por el número receptor y carga dinámicamente menú, nombre y moneda.

## Estructura del proyecto

```
orderly-backend/
├── alembic/                # Migraciones de base de datos
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── models/             # Modelos SQLAlchemy
│   │   ├── business.py     # Negocio (tenant) con email/password
│   │   ├── customer.py     # Clientes
│   │   ├── loyalty.py      # Reglas y progreso de lealtad
│   │   ├── order.py        # Pedidos e items
│   │   └── product.py      # Productos del menú
│   ├── routers/            # Endpoints de la API
│   │   ├── admin.py        # Panel admin
│   │   ├── auth.py         # Login y sesión
│   │   ├── customers.py    # CRUD clientes + compra presencial
│   │   ├── dashboard.py    # Estadísticas
│   │   ├── loyalty.py      # Reglas de lealtad
│   │   ├── orders.py       # CRUD pedidos
│   │   ├── products.py     # CRUD productos
│   │   └── webhook.py      # Webhook WhatsApp/Twilio
│   ├── schemas/            # Schemas Pydantic
│   ├── services/           # Lógica de negocio
│   │   ├── chatbot.py      # Integración OpenAI con tool calling
│   │   ├── conversation.py # Sesiones de chat en memoria
│   │   ├── orders.py       # Crear pedidos y actualizar lealtad
│   │   └── whatsapp.py     # Envío de mensajes Twilio
│   ├── auth.py             # JWT y hashing de passwords
│   ├── config.py           # Variables de entorno
│   ├── database.py         # Configuración de DB
│   ├── main.py             # Punto de entrada FastAPI
│   └── seeds.py            # Datos de ejemplo
├── .env.example
├── alembic.ini
├── Procfile
├── railway.toml
└── requirements.txt
```
