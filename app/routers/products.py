"""
Orderly - Router de productos.
CRUD completo con filtro por business_id.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Product, Business
from app.schemas.product import ProductCreate, ProductUpdate, ProductOut
from app.auth import get_current_business

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
async def list_products(
    available: bool | None = Query(None, description="Filtrar por disponibilidad"),
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    """Lista productos del negocio autenticado."""
    query = select(Product).where(Product.business_id == business.id)
    if available is not None:
        query = query.where(Product.available == available)
    query = query.order_by(Product.name)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=ProductOut, status_code=201)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    """Crea un nuevo producto para el negocio autenticado."""
    product = Product(**{**data.model_dump(exclude={"business_id"}), "business_id": business.id})
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    """Edita un producto existente del negocio autenticado."""
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.business_id == business.id)
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await db.flush()
    await db.refresh(product)
    return product


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    """Desactiva un producto del negocio autenticado (soft delete)."""
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.business_id == business.id)
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    product.available = False
    await db.flush()
    return {"message": "Producto desactivado"}
