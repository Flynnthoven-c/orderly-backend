"""
Orderly - Router de autenticación.
Login para negocios y admin. Retorna JWT de 30 días.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import authenticate_admin, authenticate_business, get_current_business
from app.models import Business

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    role: str  # "admin" o "business"
    business_id: int | None = None
    business_name: str | None = None


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Login unificado. Primero intenta admin, luego negocio.
    Retorna JWT válido por 30 días.
    """
    # Intentar login como admin
    admin_token = authenticate_admin(data.email, data.password)
    if admin_token:
        return LoginResponse(token=admin_token, role="admin")

    # Intentar login como negocio
    result = await authenticate_business(data.email, data.password, db)
    if result:
        token, business = result
        return LoginResponse(
            token=token,
            role="business",
            business_id=business.id,
            business_name=business.name,
        )

    raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")


@router.get("/me")
async def get_me(business: Business = Depends(get_current_business)):
    """Retorna los datos del negocio autenticado. Útil para verificar sesión."""
    return {
        "id": business.id,
        "name": business.name,
        "email": business.email,
        "currency": business.currency,
        "whatsapp_number": business.whatsapp_number,
        "estimated_minutes": business.estimated_minutes,
        "logo_url": business.logo_url,
        "active": business.active,
    }
