"""
Orderly - Router de pedidos.
Lista, detalle, creación presencial y cambio de estado.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Order, OrderItem, Product, Customer, Business
from app.schemas.order import OrderCreate, OrderOut, OrderItemOut, OrderStatusUpdate
from app.auth import get_current_business

router = APIRouter(prefix="/orders", tags=["orders"])

VALID_STATUSES = {"pending", "preparing", "ready", "delivered"}


@router.get("", response_model=list[OrderOut])
async def list_orders(
    status: str | None = Query(None, description="Filtrar por estado"),
    channel: str | None = Query(None, description="Filtrar por canal"),
    date_from: str | None = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    """Lista pedidos del negocio autenticado con filtros opcionales."""
    query = (
        select(Order)
        .where(Order.business_id == business.id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .options(selectinload(Order.customer))
        .order_by(Order.created_at.desc())
    )

    if status:
        query = query.where(Order.status == status)
    if channel:
        query = query.where(Order.channel == channel)
    if date_from:
        query = query.where(Order.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        # Incluir todo el día final
        query = query.where(Order.created_at < datetime.fromisoformat(date_to + "T23:59:59"))

    result = await db.execute(query)
    orders = result.scalars().all()

    return [_serialize_order(o) for o in orders]


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    """Detalle completo de un pedido del negocio autenticado."""
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.business_id == business.id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .options(selectinload(Order.customer))
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    return _serialize_order(order)


@router.post("", response_model=OrderOut, status_code=201)
async def create_order(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    """Crea un pedido presencial desde el dashboard."""
    # Calcular total e items
    total = 0.0
    items_to_create = []

    for item in data.items:
        result = await db.execute(
            select(Product).where(Product.id == item.product_id, Product.business_id == business.id)
        )
        product = result.scalars().first()
        if not product:
            raise HTTPException(status_code=400, detail=f"Producto {item.product_id} no encontrado")

        unit_price = float(product.price)
        total += unit_price * item.quantity
        items_to_create.append((item, unit_price))

    order = Order(
        business_id=business.id,
        customer_id=data.customer_id,
        status="pending",
        total=total,
        channel=data.channel,
    )
    db.add(order)
    await db.flush()

    for item, unit_price in items_to_create:
        db.add(OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=unit_price,
        ))

    await db.flush()

    # Recargar con relaciones
    result = await db.execute(
        select(Order)
        .where(Order.id == order.id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .options(selectinload(Order.customer))
    )
    order = result.scalars().first()
    return _serialize_order(order)


@router.put("/{order_id}/status", response_model=OrderOut)
async def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    """Cambia el estado de un pedido del negocio autenticado."""
    if data.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido. Opciones: {', '.join(VALID_STATUSES)}"
        )

    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.business_id == business.id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .options(selectinload(Order.customer))
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    order.status = data.status
    await db.flush()

    return _serialize_order(order)


def _serialize_order(order: Order) -> dict:
    """Serializa un pedido con sus relaciones para la respuesta."""
    return OrderOut(
        id=order.id,
        business_id=order.business_id,
        customer_id=order.customer_id,
        customer_name=order.customer.name if order.customer else None,
        status=order.status,
        total=float(order.total),
        channel=order.channel,
        items=[
            OrderItemOut(
                id=item.id,
                product_id=item.product_id,
                product_name=item.product.name if item.product else None,
                quantity=item.quantity,
                unit_price=float(item.unit_price),
            )
            for item in order.items
        ],
        created_at=order.created_at,
    )
