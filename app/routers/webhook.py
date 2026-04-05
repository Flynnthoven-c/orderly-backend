"""
Orderly - Webhook de WhatsApp (Twilio).
Recibe mensajes entrantes, identifica el negocio por el número receptor,
procesa la conversación con GPT y responde al cliente.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.request_validator import RequestValidator

from app.database import get_db
from app.config import TWILIO_AUTH_TOKEN
from app.models import Business, Product
from app.services.conversation import get_session, clear_session, cleanup_expired_sessions
from app.services.chatbot import get_bot_response
from app.services.orders import (
    find_or_create_customer,
    create_order_from_cart,
    update_loyalty_progress,
    format_owner_notification,
)
from app.services.whatsapp import send_whatsapp_message

router = APIRouter()


def _validate_twilio_signature(request: Request, form_data: dict) -> bool:
    """Valida que el request venga realmente de Twilio usando X-Twilio-Signature."""
    if not TWILIO_AUTH_TOKEN:
        # Sin token configurado (desarrollo), permitir sin validacion
        return True
    validator = RequestValidator(TWILIO_AUTH_TOKEN)
    signature = request.headers.get("X-Twilio-Signature", "")
    # Reconstruir la URL completa tal como Twilio la ve
    url = str(request.url)
    return validator.validate(url, form_data, signature)


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Recibe mensajes de Twilio WhatsApp.
    Identifica el negocio por el número al que el cliente escribió (To).
    """
    # Limpiar sesiones expiradas periódicamente
    cleanup_expired_sessions()

    # Parsear el form data de Twilio
    form = await request.form()
    form_dict = dict(form)

    # Validar firma de Twilio para evitar requests falsos
    if not _validate_twilio_signature(request, form_dict):
        return PlainTextResponse("Forbidden", status_code=403)

    from_number = form.get("From", "")       # whatsapp:+521234567890
    to_number = form.get("To", "")           # whatsapp:+1987654321 (número del negocio)
    body = form.get("Body", "").strip()

    if not from_number or not body:
        return PlainTextResponse("")

    # Limpiar el prefijo "whatsapp:" para buscar en la DB
    clean_to = to_number.replace("whatsapp:", "")
    clean_from = from_number.replace("whatsapp:", "")

    # Identificar el negocio por el número receptor
    result = await db.execute(
        select(Business).where(
            Business.whatsapp_number == clean_to,
            Business.active == True,  # noqa: E712
        )
    )
    business = result.scalars().first()

    if not business:
        # Si no se encuentra negocio, responder con mensaje genérico
        return _twiml_response(
            "Lo sentimos, este número no está configurado en Orderly. "
            "Contacta al administrador del negocio."
        )

    # Obtener la sesión de conversación
    session = get_session(clean_from, business.id)

    # Cargar el menú del negocio (solo productos disponibles)
    products_result = await db.execute(
        select(Product).where(
            Product.business_id == business.id,
            Product.available == True,  # noqa: E712
        )
    )
    products = [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "price": float(p.price),
            "available": p.available,
        }
        for p in products_result.scalars().all()
    ]

    # Obtener respuesta del chatbot
    reply, tool_calls = await get_bot_response(
        session=session,
        user_message=body,
        business_name=business.name,
        currency=business.currency,
        products=products,
    )

    # Verificar si el pedido fue confirmado
    order_confirmed = any(
        tc["name"] == "confirm_order" and tc["result"] == "PEDIDO_CONFIRMADO"
        for tc in tool_calls
    )

    if order_confirmed and session.cart:
        # Registrar/obtener cliente
        customer = await find_or_create_customer(db, business.id, clean_from, "whatsapp")

        # Crear el pedido en la base de datos
        order = await create_order_from_cart(db, session, customer, "whatsapp")

        # Actualizar progreso de lealtad
        rewards = await update_loyalty_progress(db, customer, session)

        # Notificar al dueño
        if business.owner_whatsapp:
            notification = format_owner_notification(order, customer, session, business.currency)
            send_whatsapp_message(
                to=business.owner_whatsapp,
                from_=clean_to,
                body=notification,
            )

        # Construir respuesta final para el cliente
        reply = (
            f"✅ ¡Pedido #{order.id} confirmado!\n\n"
            f"{session.cart_summary}\n\n"
            f"⏱️ Tiempo estimado: {business.estimated_minutes} minutos.\n"
            f"Te avisaremos cuando esté listo. ¡Gracias por tu compra!"
        )

        # Agregar premios ganados al mensaje
        if rewards:
            reply += "\n\n" + "\n".join(rewards)

        await db.commit()

        # Limpiar la sesión después de confirmar
        clear_session(clean_from, business.id)
    else:
        await db.commit()

    return _twiml_response(reply)


def _twiml_response(message: str) -> PlainTextResponse:
    """Genera una respuesta TwiML para Twilio."""
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"<Message>{_escape_xml(message)}</Message>"
        "</Response>"
    )
    return PlainTextResponse(content=twiml, media_type="text/xml")


def _escape_xml(text: str) -> str:
    """Escapa caracteres especiales para XML."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
