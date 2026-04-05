"""
Orderly - Autenticación con JWT.
Tokens de 30 días para que el usuario no tenga que loggearse cada rato.
"""

from datetime import datetime, timedelta

import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import JWT_SECRET, JWT_EXPIRATION_DAYS, ADMIN_EMAIL, ADMIN_PASSWORD
from app.database import get_db
from app.models import Business

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(data: dict) -> str:
    """Crea un JWT con expiración de 30 días."""
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS)
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Decodifica y valida un JWT."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sesión expirada, inicia sesión de nuevo")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")


async def get_current_business(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Business:
    """
    Dependencia de FastAPI: extrae el negocio autenticado del JWT.
    Usar en endpoints que requieren autenticación de negocio.
    """
    payload = decode_token(credentials.credentials)

    if payload.get("role") != "business":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    business_id = payload.get("business_id")
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalars().first()

    if not business or not business.active:
        raise HTTPException(status_code=401, detail="Negocio no encontrado o desactivado")

    return business


async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Dependencia de FastAPI: verifica que el JWT es de admin.
    Usar en endpoints del panel de administración.
    """
    payload = decode_token(credentials.credentials)

    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Se requiere acceso de administrador")

    return payload


def authenticate_admin(email: str, password: str) -> str | None:
    """Autentica al admin y retorna un JWT, o None si falla."""
    if email != ADMIN_EMAIL or not ADMIN_PASSWORD:
        return None
    # Verificar si ADMIN_PASSWORD ya es un hash bcrypt
    if ADMIN_PASSWORD.startswith("$2b$") or ADMIN_PASSWORD.startswith("$2a$"):
        if not verify_password(password, ADMIN_PASSWORD):
            return None
    else:
        # Fallback para texto plano (desarrollo) — comparacion segura
        import hmac
        if not hmac.compare_digest(password, ADMIN_PASSWORD):
            return None
    return create_token({"role": "admin", "email": email})


async def authenticate_business(email: str, password: str, db: AsyncSession) -> tuple[str, Business] | None:
    """Autentica un negocio y retorna (JWT, Business), o None si falla."""
    result = await db.execute(select(Business).where(Business.email == email))
    business = result.scalars().first()

    if not business or not verify_password(password, business.password_hash):
        return None

    if not business.active:
        return None

    token = create_token({
        "role": "business",
        "business_id": business.id,
        "email": business.email,
    })

    return token, business
