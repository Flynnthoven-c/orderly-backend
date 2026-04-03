"""
Orderly - Servicio de envío de mensajes WhatsApp via Twilio.
"""

from twilio.rest import Client

from app.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN


def get_twilio_client() -> Client | None:
    """Crea el cliente de Twilio. Retorna None si no hay credenciales."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        return None
    return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def send_whatsapp_message(to: str, from_: str, body: str):
    """
    Envía un mensaje de WhatsApp.
    to y from_ deben tener formato "whatsapp:+1234567890".
    """
    client = get_twilio_client()
    if not client:
        print(f"[Twilio no configurado] Mensaje para {to}: {body}")
        return None

    # Asegurar formato whatsapp:
    if not to.startswith("whatsapp:"):
        to = f"whatsapp:{to}"
    if not from_.startswith("whatsapp:"):
        from_ = f"whatsapp:{from_}"

    message = client.messages.create(
        body=body,
        from_=from_,
        to=to,
    )
    return message.sid
