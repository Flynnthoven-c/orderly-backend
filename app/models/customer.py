"""
Orderly - Modelo de cliente.
Los clientes pueden llegar por WhatsApp o presencialmente.
"""

from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(Integer, ForeignKey("businesses.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    # Canal por el que se registró: "whatsapp" o "presencial"
    channel: Mapped[str] = mapped_column(String(20), default="presencial")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relaciones
    business = relationship("Business", back_populates="customers")
    orders = relationship("Order", back_populates="customer")
    loyalty_progress = relationship("LoyaltyProgress", back_populates="customer")
