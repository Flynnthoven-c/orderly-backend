"""
Orderly - Schemas de productos.
"""

from datetime import datetime
from pydantic import BaseModel


class ProductCreate(BaseModel):
    business_id: int
    name: str
    description: str | None = None
    price: float
    available: bool = True


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    available: bool | None = None


class ProductOut(BaseModel):
    id: int
    business_id: int
    name: str
    description: str | None
    price: float
    available: bool
    created_at: datetime

    model_config = {"from_attributes": True}
