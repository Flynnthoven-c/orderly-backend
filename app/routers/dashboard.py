"""
Orderly - Router del dashboard.
Estadísticas de ventas, pedidos y clientes.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Order, OrderItem, Product, Customer
from app.schemas.loyalty import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    business_id: int = Query(..., description="ID del negocio"),
    db: AsyncSession = Depends(get_db),
):
    """Estadísticas generales del negocio."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    # Ventas del día (solo pedidos delivered)
    today_result = await db.execute(
        select(func.coalesce(func.sum(Order.total), 0))
        .where(
            Order.business_id == business_id,
            Order.created_at >= today_start,
            Order.status == "delivered",
        )
    )
    today_sales = float(today_result.scalar())

    # Ventas de la semana
    week_result = await db.execute(
        select(func.coalesce(func.sum(Order.total), 0))
        .where(
            Order.business_id == business_id,
            Order.created_at >= week_start,
            Order.status == "delivered",
        )
    )
    week_sales = float(week_result.scalar())

    # Pedidos activos (no delivered)
    active_result = await db.execute(
        select(func.count(Order.id))
        .where(
            Order.business_id == business_id,
            Order.status.in_(["pending", "preparing", "ready"]),
        )
    )
    active_orders = active_result.scalar()

    # Pedidos por estado (del día)
    status_result = await db.execute(
        select(Order.status, func.count(Order.id))
        .where(
            Order.business_id == business_id,
            Order.created_at >= today_start,
        )
        .group_by(Order.status)
    )
    orders_by_status = {row[0]: row[1] for row in status_result.all()}

    # Producto más vendido (últimos 7 días)
    top_result = await db.execute(
        select(Product.name, func.sum(OrderItem.quantity).label("total_qty"))
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.business_id == business_id,
            Order.created_at >= week_start,
        )
        .group_by(Product.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(1)
    )
    top_row = top_result.first()
    top_product = top_row[0] if top_row else None
    top_product_count = int(top_row[1]) if top_row else 0

    # Clientes nuevos hoy
    new_customers_result = await db.execute(
        select(func.count(Customer.id))
        .where(
            Customer.business_id == business_id,
            Customer.created_at >= today_start,
        )
    )
    new_customers_today = new_customers_result.scalar()

    return DashboardStats(
        today_sales=today_sales,
        week_sales=week_sales,
        active_orders=active_orders,
        top_product=top_product,
        top_product_count=top_product_count,
        new_customers_today=new_customers_today,
        orders_by_status=orders_by_status,
    )
