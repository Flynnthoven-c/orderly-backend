"""
Orderly - Router del panel admin.
Solo accesible con JWT de admin. Gestión de negocios suscritos.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import require_admin, hash_password
from app.models import Business, Order, Customer

router = APIRouter(prefix="/admin", tags=["admin"])


class BusinessCreate(BaseModel):
    email: str
    password: str
    name: str
    whatsapp_number: str | None = None
    owner_whatsapp: str | None = None
    currency: str = "MXN"
    estimated_minutes: int = 15


class BusinessUpdate(BaseModel):
    email: str | None = None
    name: str | None = None
    whatsapp_number: str | None = None
    owner_whatsapp: str | None = None
    currency: str | None = None
    estimated_minutes: int | None = None
    active: bool | None = None
    # Si se envía, cambia la contraseña
    password: str | None = None


@router.get("/businesses", dependencies=[Depends(require_admin)])
async def list_businesses(db: AsyncSession = Depends(get_db)):
    """Lista todos los negocios suscritos con stats básicas."""
    result = await db.execute(select(Business).order_by(Business.created_at.desc()))
    businesses = result.scalars().all()

    response = []
    for b in businesses:
        # Contar pedidos totales
        orders_result = await db.execute(
            select(func.count(Order.id)).where(Order.business_id == b.id)
        )
        total_orders = orders_result.scalar()

        # Contar clientes
        customers_result = await db.execute(
            select(func.count(Customer.id)).where(Customer.business_id == b.id)
        )
        total_customers = customers_result.scalar()

        # Ingresos totales
        revenue_result = await db.execute(
            select(func.coalesce(func.sum(Order.total), 0))
            .where(Order.business_id == b.id, Order.status == "delivered")
        )
        total_revenue = float(revenue_result.scalar())

        response.append({
            "id": b.id,
            "name": b.name,
            "email": b.email,
            "whatsapp_number": b.whatsapp_number,
            "currency": b.currency,
            "active": b.active,
            "created_at": b.created_at,
            "total_orders": total_orders,
            "total_customers": total_customers,
            "total_revenue": total_revenue,
        })

    return response


@router.post("/businesses", dependencies=[Depends(require_admin)], status_code=201)
async def create_business(data: BusinessCreate, db: AsyncSession = Depends(get_db)):
    """Crea un nuevo negocio (dar de alta un cliente)."""
    # Verificar email único
    existing = await db.execute(select(Business).where(Business.email == data.email))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Ya existe un negocio con ese email")

    business = Business(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        whatsapp_number=data.whatsapp_number,
        owner_whatsapp=data.owner_whatsapp,
        currency=data.currency,
        estimated_minutes=data.estimated_minutes,
        active=True,
    )
    db.add(business)
    await db.flush()
    await db.refresh(business)

    return {
        "id": business.id,
        "name": business.name,
        "email": business.email,
        "message": "Negocio creado exitosamente",
    }


@router.put("/businesses/{business_id}", dependencies=[Depends(require_admin)])
async def update_business(
    business_id: int,
    data: BusinessUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Edita un negocio existente."""
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalars().first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    update_data = data.model_dump(exclude_unset=True)

    # Si envían password, hashearla
    if "password" in update_data:
        password = update_data.pop("password")
        if password:
            business.password_hash = hash_password(password)

    for field, value in update_data.items():
        setattr(business, field, value)

    await db.flush()

    return {"message": "Negocio actualizado", "id": business.id, "name": business.name}


@router.get("/stats", dependencies=[Depends(require_admin)])
async def admin_stats(db: AsyncSession = Depends(get_db)):
    """Estadísticas generales de la plataforma."""
    businesses_count = (await db.execute(select(func.count(Business.id)))).scalar()
    active_businesses = (await db.execute(
        select(func.count(Business.id)).where(Business.active == True)  # noqa: E712
    )).scalar()
    total_orders = (await db.execute(select(func.count(Order.id)))).scalar()
    total_customers = (await db.execute(select(func.count(Customer.id)))).scalar()
    total_revenue = float((await db.execute(
        select(func.coalesce(func.sum(Order.total), 0)).where(Order.status == "delivered")
    )).scalar())

    return {
        "total_businesses": businesses_count,
        "active_businesses": active_businesses,
        "total_orders": total_orders,
        "total_customers": total_customers,
        "total_revenue": total_revenue,
    }
