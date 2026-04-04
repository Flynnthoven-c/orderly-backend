"""
Orderly - Router del panel admin.
Solo accesible con JWT de admin. Gestión de negocios y analytics de la plataforma.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, cast, Date, case, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import require_admin, hash_password
from app.models import Business, Order, OrderItem, Product, Customer

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
    password: str | None = None


# ─── CRUD de negocios ───────────────────────────────────────────────────────

@router.get("/businesses", dependencies=[Depends(require_admin)])
async def list_businesses(db: AsyncSession = Depends(get_db)):
    """Lista todos los negocios con stats detalladas."""
    result = await db.execute(select(Business).order_by(Business.created_at.desc()))
    businesses = result.scalars().all()

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    response = []
    for b in businesses:
        # Pedidos totales y del mes
        total_orders = (await db.execute(
            select(func.count(Order.id)).where(Order.business_id == b.id)
        )).scalar()

        month_orders = (await db.execute(
            select(func.count(Order.id)).where(
                Order.business_id == b.id,
                Order.created_at >= month_start,
            )
        )).scalar()

        # Clientes totales y nuevos este mes
        total_customers = (await db.execute(
            select(func.count(Customer.id)).where(Customer.business_id == b.id)
        )).scalar()

        new_customers_month = (await db.execute(
            select(func.count(Customer.id)).where(
                Customer.business_id == b.id,
                Customer.created_at >= month_start,
            )
        )).scalar()

        # Ingresos totales y del mes
        total_revenue = float((await db.execute(
            select(func.coalesce(func.sum(Order.total), 0))
            .where(Order.business_id == b.id, Order.status == "delivered")
        )).scalar())

        month_revenue = float((await db.execute(
            select(func.coalesce(func.sum(Order.total), 0))
            .where(
                Order.business_id == b.id,
                Order.status == "delivered",
                Order.created_at >= month_start,
            )
        )).scalar())

        today_revenue = float((await db.execute(
            select(func.coalesce(func.sum(Order.total), 0))
            .where(
                Order.business_id == b.id,
                Order.status == "delivered",
                Order.created_at >= today_start,
            )
        )).scalar())

        # Ticket promedio
        avg_ticket = total_revenue / total_orders if total_orders > 0 else 0

        # Pedidos por canal
        channel_result = await db.execute(
            select(Order.channel, func.count(Order.id))
            .where(Order.business_id == b.id)
            .group_by(Order.channel)
        )
        orders_by_channel = {row[0]: row[1] for row in channel_result.all()}

        response.append({
            "id": b.id,
            "name": b.name,
            "email": b.email,
            "whatsapp_number": b.whatsapp_number,
            "currency": b.currency,
            "active": b.active,
            "created_at": b.created_at,
            "total_orders": total_orders,
            "month_orders": month_orders,
            "total_customers": total_customers,
            "new_customers_month": new_customers_month,
            "total_revenue": total_revenue,
            "month_revenue": month_revenue,
            "today_revenue": today_revenue,
            "avg_ticket": round(avg_ticket, 2),
            "orders_by_channel": orders_by_channel,
        })

    return response


@router.post("/businesses", dependencies=[Depends(require_admin)], status_code=201)
async def create_business(data: BusinessCreate, db: AsyncSession = Depends(get_db)):
    """Crea un nuevo negocio (dar de alta un cliente)."""
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
    if "password" in update_data:
        password = update_data.pop("password")
        if password:
            business.password_hash = hash_password(password)

    for field, value in update_data.items():
        setattr(business, field, value)

    await db.flush()
    return {"message": "Negocio actualizado", "id": business.id, "name": business.name}


# ─── Stats globales ─────────────────────────────────────────────────────────

@router.get("/stats", dependencies=[Depends(require_admin)])
async def admin_stats(db: AsyncSession = Depends(get_db)):
    """Estadísticas generales de la plataforma con comparación vs período anterior."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
    week_start = today_start - timedelta(days=today_start.weekday())
    prev_week_start = week_start - timedelta(days=7)

    total_businesses = (await db.execute(select(func.count(Business.id)))).scalar()
    active_businesses = (await db.execute(
        select(func.count(Business.id)).where(Business.active == True)  # noqa: E712
    )).scalar()
    total_orders = (await db.execute(select(func.count(Order.id)))).scalar()
    total_customers = (await db.execute(select(func.count(Customer.id)))).scalar()
    total_revenue = float((await db.execute(
        select(func.coalesce(func.sum(Order.total), 0)).where(Order.status == "delivered")
    )).scalar())

    # Este mes vs mes anterior
    month_revenue = float((await db.execute(
        select(func.coalesce(func.sum(Order.total), 0)).where(
            Order.status == "delivered", Order.created_at >= month_start,
        )
    )).scalar())
    prev_month_revenue = float((await db.execute(
        select(func.coalesce(func.sum(Order.total), 0)).where(
            Order.status == "delivered",
            Order.created_at >= prev_month_start,
            Order.created_at < month_start,
        )
    )).scalar())

    month_orders = (await db.execute(
        select(func.count(Order.id)).where(Order.created_at >= month_start)
    )).scalar()
    prev_month_orders = (await db.execute(
        select(func.count(Order.id)).where(
            Order.created_at >= prev_month_start, Order.created_at < month_start,
        )
    )).scalar()

    month_customers = (await db.execute(
        select(func.count(Customer.id)).where(Customer.created_at >= month_start)
    )).scalar()
    prev_month_customers = (await db.execute(
        select(func.count(Customer.id)).where(
            Customer.created_at >= prev_month_start, Customer.created_at < month_start,
        )
    )).scalar()

    # Hoy vs ayer
    today_revenue = float((await db.execute(
        select(func.coalesce(func.sum(Order.total), 0)).where(
            Order.status == "delivered", Order.created_at >= today_start,
        )
    )).scalar())
    yesterday_revenue = float((await db.execute(
        select(func.coalesce(func.sum(Order.total), 0)).where(
            Order.status == "delivered",
            Order.created_at >= yesterday_start,
            Order.created_at < today_start,
        )
    )).scalar())

    today_orders = (await db.execute(
        select(func.count(Order.id)).where(Order.created_at >= today_start)
    )).scalar()
    yesterday_orders = (await db.execute(
        select(func.count(Order.id)).where(
            Order.created_at >= yesterday_start, Order.created_at < today_start,
        )
    )).scalar()

    # Esta semana vs semana anterior
    week_revenue = float((await db.execute(
        select(func.coalesce(func.sum(Order.total), 0)).where(
            Order.status == "delivered", Order.created_at >= week_start,
        )
    )).scalar())
    prev_week_revenue = float((await db.execute(
        select(func.coalesce(func.sum(Order.total), 0)).where(
            Order.status == "delivered",
            Order.created_at >= prev_week_start,
            Order.created_at < week_start,
        )
    )).scalar())

    # Ticket promedio este mes
    avg_ticket = month_revenue / month_orders if month_orders > 0 else 0
    prev_avg_ticket = prev_month_revenue / prev_month_orders if prev_month_orders > 0 else 0

    # WhatsApp adoption rate
    wa_orders = (await db.execute(
        select(func.count(Order.id)).where(
            Order.channel == "whatsapp", Order.created_at >= month_start,
        )
    )).scalar()
    wa_rate = (wa_orders / month_orders * 100) if month_orders > 0 else 0

    prev_wa_orders = (await db.execute(
        select(func.count(Order.id)).where(
            Order.channel == "whatsapp",
            Order.created_at >= prev_month_start,
            Order.created_at < month_start,
        )
    )).scalar()
    prev_wa_rate = (prev_wa_orders / prev_month_orders * 100) if prev_month_orders > 0 else 0

    # Pedidos activos ahora
    active_orders = (await db.execute(
        select(func.count(Order.id)).where(
            Order.status.in_(["pending", "preparing", "ready"])
        )
    )).scalar()

    return {
        "total_businesses": total_businesses,
        "active_businesses": active_businesses,
        "total_orders": total_orders,
        "total_customers": total_customers,
        "total_revenue": total_revenue,
        "active_orders": active_orders,
        "today": {
            "revenue": today_revenue,
            "orders": today_orders,
            "prev_revenue": yesterday_revenue,
            "prev_orders": yesterday_orders,
        },
        "week": {
            "revenue": week_revenue,
            "prev_revenue": prev_week_revenue,
        },
        "month": {
            "revenue": month_revenue,
            "orders": month_orders,
            "customers": month_customers,
            "avg_ticket": round(avg_ticket, 2),
            "wa_rate": round(wa_rate, 1),
            "prev_revenue": prev_month_revenue,
            "prev_orders": prev_month_orders,
            "prev_customers": prev_month_customers,
            "prev_avg_ticket": round(prev_avg_ticket, 2),
            "prev_wa_rate": round(prev_wa_rate, 1),
        },
    }


# ─── Analytics detallados ───────────────────────────────────────────────────

@router.get("/analytics/revenue", dependencies=[Depends(require_admin)])
async def revenue_over_time(
    days: int = Query(30, description="Últimos N días"),
    business_id: int | None = Query(None, description="Filtrar por negocio"),
    db: AsyncSession = Depends(get_db),
):
    """Ingresos por día con desglose por canal."""
    since = datetime.utcnow() - timedelta(days=days)

    query = (
        select(
            cast(Order.created_at, Date).label("date"),
            Order.channel,
            func.coalesce(func.sum(Order.total), 0).label("revenue"),
            func.count(Order.id).label("count"),
        )
        .where(Order.created_at >= since, Order.status == "delivered")
        .group_by(cast(Order.created_at, Date), Order.channel)
        .order_by(cast(Order.created_at, Date))
    )
    if business_id:
        query = query.where(Order.business_id == business_id)

    result = await db.execute(query)
    rows = result.all()

    # Agrupar por fecha
    data: dict[str, dict] = {}
    for row in rows:
        date_str = str(row.date)
        if date_str not in data:
            data[date_str] = {"date": date_str, "whatsapp": 0, "presencial": 0, "total": 0, "orders": 0}
        data[date_str][row.channel] = float(row.revenue)
        data[date_str]["total"] += float(row.revenue)
        data[date_str]["orders"] += row.count

    return list(data.values())


@router.get("/analytics/orders", dependencies=[Depends(require_admin)])
async def orders_over_time(
    days: int = Query(30, description="Últimos N días"),
    business_id: int | None = Query(None, description="Filtrar por negocio"),
    db: AsyncSession = Depends(get_db),
):
    """Pedidos por día con desglose por estado y canal."""
    since = datetime.utcnow() - timedelta(days=days)

    # Por canal
    channel_query = (
        select(
            cast(Order.created_at, Date).label("date"),
            Order.channel,
            func.count(Order.id).label("count"),
        )
        .where(Order.created_at >= since)
        .group_by(cast(Order.created_at, Date), Order.channel)
        .order_by(cast(Order.created_at, Date))
    )
    if business_id:
        channel_query = channel_query.where(Order.business_id == business_id)

    result = await db.execute(channel_query)
    rows = result.all()

    data: dict[str, dict] = {}
    for row in rows:
        date_str = str(row.date)
        if date_str not in data:
            data[date_str] = {"date": date_str, "whatsapp": 0, "presencial": 0, "total": 0}
        data[date_str][row.channel] = row.count
        data[date_str]["total"] += row.count

    return list(data.values())


@router.get("/analytics/customers", dependencies=[Depends(require_admin)])
async def customers_over_time(
    days: int = Query(30, description="Últimos N días"),
    business_id: int | None = Query(None, description="Filtrar por negocio"),
    db: AsyncSession = Depends(get_db),
):
    """Nuevos clientes por día con desglose por canal."""
    since = datetime.utcnow() - timedelta(days=days)

    query = (
        select(
            cast(Customer.created_at, Date).label("date"),
            Customer.channel,
            func.count(Customer.id).label("count"),
        )
        .where(Customer.created_at >= since)
        .group_by(cast(Customer.created_at, Date), Customer.channel)
        .order_by(cast(Customer.created_at, Date))
    )
    if business_id:
        query = query.where(Customer.business_id == business_id)

    result = await db.execute(query)
    rows = result.all()

    data: dict[str, dict] = {}
    for row in rows:
        date_str = str(row.date)
        if date_str not in data:
            data[date_str] = {"date": date_str, "whatsapp": 0, "presencial": 0, "total": 0}
        data[date_str][row.channel] = row.count
        data[date_str]["total"] += row.count

    return list(data.values())


@router.get("/analytics/top-products", dependencies=[Depends(require_admin)])
async def top_products(
    days: int = Query(30, description="Últimos N días"),
    business_id: int | None = Query(None, description="Filtrar por negocio"),
    limit: int = Query(10, description="Top N productos"),
    db: AsyncSession = Depends(get_db),
):
    """Productos más vendidos con ingresos generados."""
    since = datetime.utcnow() - timedelta(days=days)

    query = (
        select(
            Product.name,
            Business.name.label("business_name"),
            func.sum(OrderItem.quantity).label("quantity"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .join(Business, Business.id == Order.business_id)
        .where(Order.created_at >= since)
        .group_by(Product.name, Business.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
    )
    if business_id:
        query = query.where(Order.business_id == business_id)

    result = await db.execute(query)
    return [
        {
            "product": row.name,
            "business": row.business_name,
            "quantity": int(row.quantity),
            "revenue": float(row.revenue),
        }
        for row in result.all()
    ]


@router.get("/analytics/business/{business_id}", dependencies=[Depends(require_admin)])
async def business_detail(
    business_id: int,
    days: int = Query(30, description="Últimos N días"),
    db: AsyncSession = Depends(get_db),
):
    """Detalle completo de un negocio específico para drill-down."""
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalars().first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    since = datetime.utcnow() - timedelta(days=days)
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Pedidos por estado
    status_result = await db.execute(
        select(Order.status, func.count(Order.id))
        .where(Order.business_id == business_id, Order.created_at >= since)
        .group_by(Order.status)
    )
    orders_by_status = {row[0]: row[1] for row in status_result.all()}

    # Pedidos por hora del día (para saber las horas pico)
    hour_result = await db.execute(
        select(
            extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("count"),
        )
        .where(Order.business_id == business_id, Order.created_at >= since)
        .group_by(extract("hour", Order.created_at))
        .order_by(extract("hour", Order.created_at))
    )
    orders_by_hour = [{"hour": int(row.hour), "orders": row.count} for row in hour_result.all()]

    # Top 5 productos
    top_result = await db.execute(
        select(
            Product.name,
            func.sum(OrderItem.quantity).label("quantity"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.business_id == business_id, Order.created_at >= since)
        .group_by(Product.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
    )
    top_products = [
        {"product": row.name, "quantity": int(row.quantity), "revenue": float(row.revenue)}
        for row in top_result.all()
    ]

    # Top 5 clientes
    top_customers_result = await db.execute(
        select(
            Customer.name,
            Customer.phone,
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(Order.total), 0).label("spent"),
        )
        .join(Order, Order.customer_id == Customer.id)
        .where(Order.business_id == business_id, Order.created_at >= since)
        .group_by(Customer.id, Customer.name, Customer.phone)
        .order_by(func.coalesce(func.sum(Order.total), 0).desc())
        .limit(5)
    )
    top_customers = [
        {"name": row.name, "phone": row.phone, "orders": row.orders, "spent": float(row.spent)}
        for row in top_customers_result.all()
    ]

    # Pedidos activos ahora
    active_orders = (await db.execute(
        select(func.count(Order.id)).where(
            Order.business_id == business_id,
            Order.status.in_(["pending", "preparing", "ready"]),
        )
    )).scalar()

    return {
        "business": {
            "id": business.id,
            "name": business.name,
            "email": business.email,
            "currency": business.currency,
            "active": business.active,
            "created_at": business.created_at,
        },
        "orders_by_status": orders_by_status,
        "orders_by_hour": orders_by_hour,
        "top_products": top_products,
        "top_customers": top_customers,
        "active_orders": active_orders,
    }


@router.get("/analytics/business-ranking", dependencies=[Depends(require_admin)])
async def business_ranking(
    days: int = Query(30, description="Últimos N días"),
    db: AsyncSession = Depends(get_db),
):
    """Ranking de negocios por ingresos con métricas comparativas."""
    since = datetime.utcnow() - timedelta(days=days)
    prev_since = since - timedelta(days=days)

    result = await db.execute(select(Business).where(Business.active == True))  # noqa: E712
    businesses = result.scalars().all()

    ranking = []
    for b in businesses:
        # Ingresos período actual
        revenue = float((await db.execute(
            select(func.coalesce(func.sum(Order.total), 0))
            .where(Order.business_id == b.id, Order.status == "delivered", Order.created_at >= since)
        )).scalar())

        # Ingresos período anterior
        prev_revenue = float((await db.execute(
            select(func.coalesce(func.sum(Order.total), 0))
            .where(
                Order.business_id == b.id, Order.status == "delivered",
                Order.created_at >= prev_since, Order.created_at < since,
            )
        )).scalar())

        # Pedidos período actual
        orders = (await db.execute(
            select(func.count(Order.id))
            .where(Order.business_id == b.id, Order.created_at >= since)
        )).scalar()

        prev_orders = (await db.execute(
            select(func.count(Order.id))
            .where(
                Order.business_id == b.id,
                Order.created_at >= prev_since, Order.created_at < since,
            )
        )).scalar()

        # Clientes únicos
        unique_customers = (await db.execute(
            select(func.count(func.distinct(Order.customer_id)))
            .where(Order.business_id == b.id, Order.created_at >= since)
        )).scalar()

        avg_ticket = revenue / orders if orders > 0 else 0

        # Channel mix
        wa_count = (await db.execute(
            select(func.count(Order.id))
            .where(Order.business_id == b.id, Order.channel == "whatsapp", Order.created_at >= since)
        )).scalar()
        wa_pct = (wa_count / orders * 100) if orders > 0 else 0

        ranking.append({
            "id": b.id,
            "name": b.name,
            "revenue": revenue,
            "prev_revenue": prev_revenue,
            "orders": orders,
            "prev_orders": prev_orders,
            "unique_customers": unique_customers,
            "avg_ticket": round(avg_ticket, 2),
            "wa_percentage": round(wa_pct, 1),
        })

    ranking.sort(key=lambda x: x["revenue"], reverse=True)
    return ranking


@router.get("/analytics/peak-hours", dependencies=[Depends(require_admin)])
async def peak_hours(
    days: int = Query(30, description="Últimos N días"),
    business_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Pedidos por día de la semana y hora para heatmap."""
    since = datetime.utcnow() - timedelta(days=days)

    query = (
        select(
            extract("dow", Order.created_at).label("dow"),
            extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("count"),
        )
        .where(Order.created_at >= since)
        .group_by(extract("dow", Order.created_at), extract("hour", Order.created_at))
    )
    if business_id:
        query = query.where(Order.business_id == business_id)

    result = await db.execute(query)
    return [
        {"dow": int(row.dow), "hour": int(row.hour), "count": row.count}
        for row in result.all()
    ]
