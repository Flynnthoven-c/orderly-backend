"""
Orderly - Modelo de negocio (multi-tenant).
Cada negocio tiene su propio menú, clientes y pedidos.
"""

from datetime import datetime
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    whatsapp_number: Mapped[str] = mapped_column(String(20), nullable=True)
    logo_url: Mapped[str] = mapped_column(String(500), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="MXN")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relaciones
    products = relationship("Product", back_populates="business")
    customers = relationship("Customer", back_populates="business")
    orders = relationship("Order", back_populates="business")
    loyalty_rules = relationship("LoyaltyRule", back_populates="business")
