"""
Orderly - Schemas de clientes.
"""

from datetime import datetime
from pydantic import BaseModel


class CustomerCreate(BaseModel):
    business_id: int
    name: str
    phone: str | None = None
    channel: str = "presencial"


class CustomerOut(BaseModel):
    id: int
    business_id: int
    name: str
    phone: str | None
    channel: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PurchaseCreate(BaseModel):
    """Registrar una compra presencial para un cliente existente."""
    items: list["PurchaseItem"]


class PurchaseItem(BaseModel):
    product_id: int
    quantity: int = 1
