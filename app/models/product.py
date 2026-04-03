"""
Orderly - Modelo de producto.
Cada producto pertenece a un negocio (business_id).
"""

from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Integer, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(Integer, ForeignKey("businesses.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relaciones
    business = relationship("Business", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
    loyalty_rules = relationship("LoyaltyRule", back_populates="product")
