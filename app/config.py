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

# CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
