"""
Orderly - Router de clientes.
Lista, registro, perfil con historial, y registro de compra presencial.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Customer, Order, OrderItem, Product, LoyaltyRule, LoyaltyProgress, Business
from app.schemas.customer import CustomerCreate, CustomerOut, PurchaseCreate
from app.schemas.order import OrderOut, OrderItemOut
from app.auth import get_current_business

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerOut])
async def list_customers(
    search: str | None = Query(None, description="Buscar por nombre o teléfono"),
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    """Lista clientes del negocio autenticado con búsqueda opcional."""
    query = select(Customer).where(Customer.business_id == business.id)

    if search:
        query = query.where(
            (Customer.name.ilike(f"%{search}%")) |
            (Customer.phone.ilike(f"%{search}%"))
        )

    query = query.order_by(Customer.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{customer_id}")
async def get_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    """Perfil completo: datos, historial de pedidos y progreso de lealtad."""
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.business_id == business.id)
    )
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Historial de pedidos
    orders_result = await db.execute(
        select(Order)
        .where(Order.customer_id == customer_id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .order_by(Order.created_at.desc())
        .limit(20)
    )
    orders = orders_result.scalars().all()

    # Progreso de lealtad
    progress_result = await db.execute(
        select(LoyaltyProgress)
        .where(LoyaltyProgress.customer_id == customer_id)
        .options(selectinload(LoyaltyProgress.rule).selectinload(LoyaltyRule.product))
    )
    progress_list = progress_result.scalars().all()

    # Total gastado
    total_result = await db.execute(
        select(func.coalesce(func.sum(Order.total), 0))
        .where(Order.customer_id == customer_id, Order.status == "delivered")
    )
    total_spent = float(total_result.scalar())

    return {
        "customer": CustomerOut.model_validate(customer),
        "total_spent": total_spent,
        "orders_count": len(orders),
        "orders": [
            OrderOut(
                id=o.id,
                business_id=o.business_id,
                customer_id=o.customer_id,
                status=o.status,
                total=float(o.total),
                channel=o.channel,
                items=[
                    OrderItemOut(
                        id=item.id,
                        product_id=item.product_id,
                        product_name=item.product.name if item.product else None,
                        quantity=item.quantity,
                        unit_price=float(item.unit_price),
                    )
                    for item in o.items
                ],
                created_at=o.created_at,
            )
            for o in orders
        ],
        "loyalty_progress": [
            {
                "rule_id": p.rule_id,
                "rule_name": p.rule.name,
                "rule_type": p.rule.rule_type,
                "threshold": p.rule.threshold,
                "reward_description": p.rule.reward_description,
                "product_name": p.rule.product.name if p.rule.product else None,
                "current_count": p.current_count,
                "redeemed_count": p.redeemed_count,
                "pending_rewards": (p.current_count // p.rule.threshold) - p.redeemed_count,
                "last_updated": p.last_updated,
            }
            for p in progress_list
        ],
    }


@router.post("", response_model=CustomerOut, status_code=201)
async def create_customer(
    data: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    """Registra un nuevo cliente presencial para el negocio autenticado."""
    # Verificar duplicado por teléfono si se proporcionó
    if data.phone:
        result = await db.execute(
            select(Customer).where(
                Customer.business_id == business.id,
                Customer.phone == data.phone,
            )
        )
        existing = result.scalars().first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Ya existe un cliente con ese teléfono en este negocio"
            )

    customer = Customer(**{**data.model_dump(exclude={"business_id"}), "business_id": business.id})
    db.add(customer)
    await db.flush()
    await db.refresh(customer)
    return customer


@router.post("/{customer_id}/purchase")
async def register_purchase(
    customer_id: int,
    data: PurchaseCreate,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    """
    Registra una compra presencial: crea pedido y actualiza lealtad.
    Usado desde el dashboard cuando un cliente compra en mostrador.
    """
    # Verificar que el cliente existe y pertenece al negocio autenticado
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.business_id == business.id)
    )
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Crear el pedido
    total = 0.0
    items_to_create = []

    for item in data.items:
        result = await db.execute(select(Product).where(Product.id == item.product_id))
        product = result.scalars().first()
        if not product:
            raise HTTPException(status_code=400, detail=f"Producto {item.product_id} no encontrado")

        unit_price = float(product.price)
        total += unit_price * item.quantity
        items_to_create.append((item, product))

    order = Order(
        business_id=customer.business_id,
        customer_id=customer.id,
        status="delivered",  # Compra presencial = ya entregada
        total=total,
        channel="presencial",
    )
    db.add(order)
    await db.flush()

    for item, product in items_to_create:
        db.add(OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=float(product.price),
        ))

    await db.flush()

    # Actualizar progreso de lealtad
    rewards_earned = []
    rules_result = await db.execute(
        select(LoyaltyRule).where(
            LoyaltyRule.business_id == customer.business_id,
            LoyaltyRule.active == True,  # noqa: E712
        )
    )
    rules = rules_result.scalars().all()

    for rule in rules:
        # Obtener o crear progreso
        prog_result = await db.execute(
            select(LoyaltyProgress).where(
                LoyaltyProgress.customer_id == customer.id,
                LoyaltyProgress.rule_id == rule.id,
            )
        )
        progress = prog_result.scalars().first()

        if not progress:
            progress = LoyaltyProgress(
                customer_id=customer.id,
                rule_id=rule.id,
                current_count=0,
                redeemed_count=0,
            )
            db.add(progress)
            await db.flush()

        # Calcular incremento
        increment = 0
        if rule.rule_type == "product_count" and rule.product_id:
            for item, product in items_to_create:
                if item.product_id == rule.product_id:
                    increment += item.quantity
        elif rule.rule_type == "total_spent":
            increment = int(total)

        if increment > 0:
            progress.current_count += increment
            new_rewards = (progress.current_count // rule.threshold) - progress.redeemed_count
            if new_rewards > 0:
                rewards_earned.append({
                    "rule": rule.name,
                    "reward": rule.reward_description,
                    "pending_count": new_rewards,
                })

    await db.flush()

    return {
        "message": "Compra registrada exitosamente",
        "order_id": order.id,
        "total": total,
        "rewards_earned": rewards_earned,
    }
