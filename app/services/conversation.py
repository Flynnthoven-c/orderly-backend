"""
Orderly - Servicio de conversación.
Maneja el estado de cada sesión de chat (carrito, historial de mensajes)
indexado por (phone_number, business_id).
"""

import time
from dataclasses import dataclass, field


@dataclass
class CartItem:
    """Un producto en el carrito del cliente."""
    product_id: int
    product_name: str
    quantity: int
    unit_price: float


@dataclass
class ConversationSession:
    """Estado de una conversación activa."""
    business_id: int
    phone: str
    # Carrito de compras actual
    cart: list[CartItem] = field(default_factory=list)
    # Historial de mensajes para enviar a OpenAI (role + content)
    messages: list[dict] = field(default_factory=list)
    # Si el bot ya mostró el resumen y espera confirmación
    awaiting_confirmation: bool = False
    # Timestamp de última actividad (para limpiar sesiones viejas)
    last_activity: float = field(default_factory=time.time)

    @property
    def cart_total(self) -> float:
        return sum(item.quantity * item.unit_price for item in self.cart)

    @property
    def cart_summary(self) -> str:
        """Resumen del carrito en texto legible."""
        if not self.cart:
            return "Carrito vacío"
        lines = []
        for item in self.cart:
            subtotal = item.quantity * item.unit_price
            lines.append(f"  {item.quantity}x {item.product_name} - ${subtotal:.2f}")
        lines.append(f"  💰 Total: ${self.cart_total:.2f}")
        return "\n".join(lines)

    def add_to_cart(self, product_id: int, name: str, price: float, quantity: int = 1):
        """Agrega un producto al carrito o incrementa la cantidad si ya existe."""
        for item in self.cart:
            if item.product_id == product_id:
                item.quantity += quantity
                return
        self.cart.append(CartItem(
            product_id=product_id,
            product_name=name,
            quantity=quantity,
            unit_price=price,
        ))

    def clear_cart(self):
        self.cart.clear()
        self.awaiting_confirmation = False

    def touch(self):
        """Actualiza el timestamp de última actividad."""
        self.last_activity = time.time()


# Almacén global de sesiones: clave = (phone, business_id)
_sessions: dict[tuple[str, int], ConversationSession] = {}

# Tiempo máximo de inactividad antes de limpiar una sesión (30 minutos)
SESSION_TIMEOUT = 30 * 60


def get_session(phone: str, business_id: int) -> ConversationSession:
    """Obtiene o crea una sesión de conversación."""
    key = (phone, business_id)
    session = _sessions.get(key)

    if session is None:
        session = ConversationSession(business_id=business_id, phone=phone)
        _sessions[key] = session
    else:
        session.touch()

    return session


def clear_session(phone: str, business_id: int):
    """Elimina una sesión (después de completar un pedido)."""
    key = (phone, business_id)
    _sessions.pop(key, None)


def cleanup_expired_sessions():
    """Limpia sesiones que llevan más de SESSION_TIMEOUT sin actividad."""
    now = time.time()
    expired = [
        key for key, session in _sessions.items()
        if now - session.last_activity > SESSION_TIMEOUT
    ]
    for key in expired:
        del _sessions[key]
