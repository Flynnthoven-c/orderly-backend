"""
Orderly - Configuración general del backend.
Carga variables de entorno y expone constantes de configuración.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Base de datos
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/orderly")

# Si Railway provee la URL con "postgresql://" hay que convertirla a asyncpg
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")

# Autenticación
_jwt_secret_default = "orderly-dev-secret-change-in-production"
JWT_SECRET = os.getenv("JWT_SECRET", _jwt_secret_default)
JWT_EXPIRATION_DAYS = int(os.getenv("JWT_EXPIRATION_DAYS", "30"))

# Advertir si se usa el secret por defecto (bloquear en produccion)
_env = os.getenv("RAILWAY_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))
if JWT_SECRET == _jwt_secret_default and _env != "development":
    raise RuntimeError(
        "JWT_SECRET no está configurado. "
        "Define la variable de entorno JWT_SECRET con un valor seguro antes de desplegar."
    )
# Contraseña del panel admin (solo tú)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@orderly.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
