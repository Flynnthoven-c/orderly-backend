"""
Orderly - Schemas de pedidos.
"""

from datetime import datetime
from pydantic import BaseModel


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = 1


class OrderCreate(BaseModel):
    """Para crear pedidos presenciales desde el dashboard."""
    business_id: int
    customer_id: int | None = None
    items: list[OrderItemCreate]
    channel: str = "presencial"


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str | None = None
    quantity: int
    unit_price: float

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    business_id: int
    customer_id: int | None
    customer_name: str | None = None
    status: str
    total: float
    channel: str
    items: list[OrderItemOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderStatusUpdate(BaseModel):
    status: str  # pending, preparing, ready, delivered
