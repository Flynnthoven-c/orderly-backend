# Orderly Backend

API para gestión de pedidos de comida rápida con chatbot WhatsApp.

## Stack

- **FastAPI** + Uvicorn
- **SQLAlchemy** async + PostgreSQL
- **Alembic** para migraciones
- **OpenAI** GPT-4o-mini para chatbot
- **Twilio** WhatsApp API

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
# Crear la base de datos
createdb orderly

# Ejecutar migraciones
alembic upgrade head

# Insertar datos de ejemplo
python -m app.seeds
```

### 4. Iniciar el servidor

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Webhook de Twilio con ngrok

Para recibir mensajes de WhatsApp en desarrollo local:

```bash
ngrok http 8000
```

Copiar la URL de ngrok y configurar en Twilio:
`https://tu-url.ngrok.io/webhook/whatsapp`

## Deploy en Railway

1. Crear proyecto en Railway y agregar plugin de PostgreSQL
2. Conectar el repositorio de GitHub
3. Configurar variables de entorno en Railway:
   - `OPENAI_API_KEY`
   - `TWILIO_ACCOUNT_SID`
   - `TWILIO_AUTH_TOKEN`
   - `TWILIO_WHATSAPP_FROM` (ej: `whatsapp:+1234567890`)
   - `OWNER_WHATSAPP_NUMBER` (ej: `whatsapp:+521234567890`)
   - `ALLOWED_ORIGINS` (dominio de Vercel)
   - `CURRENCY` (ej: `MXN`)
   - `BUSINESS_ID` (ej: `1`)
   - `DATABASE_URL` (Railway lo provee automáticamente)
4. Railway usa el `Procfile` para iniciar: ejecuta migraciones y luego el servidor

## Configurar número dedicado de WhatsApp en Twilio

1. Comprar un número en Twilio con capacidad WhatsApp
2. Crear cuenta en Meta Business Manager para el negocio
3. Verificar el negocio en Meta (1-3 días hábiles)
4. Configurar perfil de WhatsApp Business con nombre, foto y descripción
5. En Twilio Console > Messaging > WhatsApp Senders, apuntar el webhook a:
   `https://tu-backend.railway.app/webhook/whatsapp`

## Estructura del proyecto

```
backend/
├── alembic/              # Migraciones de base de datos
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── models/           # Modelos SQLAlchemy
│   │   ├── business.py
│   │   ├── customer.py
│   │   ├── loyalty.py
│   │   ├── order.py
│   │   └── product.py
│   ├── config.py         # Variables de entorno
│   ├── database.py       # Configuración de DB
│   ├── main.py           # Punto de entrada FastAPI
│   └── seeds.py          # Datos de ejemplo
├── .env.example
├── alembic.ini
├── Procfile
├── railway.toml
├── README.md
└── requirements.txt
```
