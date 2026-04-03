"""
Orderly - Servicio de pedidos.
Crea pedidos, registra clientes, actualiza lealtad y notifica al dueño.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, Order, OrderItem, LoyaltyRule, LoyaltyProgress
from app.services.conversation import ConversationSession


async def find_or_create_customer(
    db: AsyncSession,
    business_id: int,
    phone: str,
    channel: str = "whatsapp",
) -> Customer:
    """Busca un cliente por teléfono y negocio, o lo crea si no existe."""
    result = await db.execute(
        select(Customer).where(
            Customer.business_id == business_id,
            Customer.phone == phone,
        )
    )
    customer = result.scalars().first()

    if not customer:
        customer = Customer(
            business_id=business_id,
            name=phone,  # Se puede actualizar después con su nombre real
            phone=phone,
            channel=channel,
        )
        db.add(customer)
        await db.flush()

    return customer


async def create_order_from_cart(
    db: AsyncSession,
    session: ConversationSession,
    customer: Customer,
    channel: str = "whatsapp",
) -> Order:
    """Crea un pedido en la base de datos a partir del carrito de la sesión."""
    order = Order(
        business_id=session.business_id,
        customer_id=customer.id,
        status="pending",
        total=session.cart_total,
        channel=channel,
    )
    db.add(order)
    await db.flush()

    # Crear los items del pedido
    for cart_item in session.cart:
        order_item = OrderItem(
            order_id=order.id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            unit_price=cart_item.unit_price,
        )
        db.add(order_item)

    await db.flush()
    return order


async def update_loyalty_progress(
    db: AsyncSession,
    customer: Customer,
    session: ConversationSession,
) -> list[str]:
    """
    Actualiza el progreso de lealtad del cliente después de un pedido.
    Retorna una lista de mensajes de premios ganados (si los hay).
    """
    rewards_earned = []

    # Obtener las reglas activas del negocio
    result = await db.execute(
        select(LoyaltyRule).where(
            LoyaltyRule.business_id == session.business_id,
            LoyaltyRule.active == True,  # noqa: E712
        )
    )
    rules = result.scalars().all()

    for rule in rules:
        # Obtener o crear el progreso del cliente en esta regla
        progress_result = await db.execute(
            select(LoyaltyProgress).where(
                LoyaltyProgress.customer_id == customer.id,
                LoyaltyProgress.rule_id == rule.id,
            )
        )
        progress = progress_result.scalars().first()

        if not progress:
            progress = LoyaltyProgress(
                customer_id=customer.id,
                rule_id=rule.id,
                current_count=0,
                redeemed_count=0,
            )
            db.add(progress)
            await db.flush()

        # Calcular el incremento según el tipo de regla
        increment = 0
        if rule.rule_type == "product_count" and rule.product_id:
            # Contar unidades del producto específico en el carrito
            for item in session.cart:
                if item.product_id == rule.product_id:
                    increment += item.quantity
        elif rule.rule_type == "total_spent":
            # Sumar el total del pedido (redondeado)
            increment = int(session.cart_total)

        if increment > 0:
            progress.current_count += increment

            # Verificar si alcanzó el umbral
            if progress.current_count >= rule.threshold:
                # Calcular cuántos premios ganó
                new_rewards = progress.current_count // rule.threshold
                already_redeemed = progress.redeemed_count
                pending_rewards = new_rewards - already_redeemed

                if pending_rewards > 0:
                    rewards_earned.append(
                        f"🎉 ¡Felicidades! Ganaste: {rule.reward_description}"
                    )

    await db.flush()
    return rewards_earned


def format_owner_notification(
    order: Order,
    customer: Customer,
    session: ConversationSession,
    currency: str,
) -> str:
    """Formatea el mensaje de notificación para el dueño del negocio."""
    items_text = "\n".join(
        f"  {item.quantity}x {item.product_name}"
        for item in session.cart
    )

    return (
        f"🍔 Nuevo pedido #{order.id} — {customer.name}\n"
        f"{items_text}\n"
        f"💰 Total: ${session.cart_total:.2f} {currency}\n"
        f"📱 {session.phone} ({order.channel})"
    )
