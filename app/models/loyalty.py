"""
Orderly - Modelos de lealtad.
LoyaltyRule: reglas configuradas por el negocio (ej: cada 6 hamburguesas, 1 gratis).
LoyaltyProgress: progreso de cada cliente en cada regla.
"""

from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LoyaltyRule(Base):
    __tablename__ = "loyalty_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(Integer, ForeignKey("businesses.id"), nullable=False)
    # Producto específico (nullable = aplica a cualquier compra)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    # Tipo de regla: "product_count" (por cantidad de producto) o "total_spent" (por monto gastado)
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Umbral para ganar el premio (ej: 6 hamburguesas o $500 gastados)
    threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_description: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relaciones
    business = relationship("Business", back_populates="loyalty_rules")
    product = relationship("Product", back_populates="loyalty_rules")
    progress = relationship("LoyaltyProgress", back_populates="rule")


class LoyaltyProgress(Base):
    __tablename__ = "loyalty_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False)
    rule_id: Mapped[int] = mapped_column(Integer, ForeignKey("loyalty_rules.id"), nullable=False)
    current_count: Mapped[int] = mapped_column(Integer, default=0)
    redeemed_count: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    customer = relationship("Customer", back_populates="loyalty_progress")
    rule = relationship("LoyaltyRule", back_populates="progress")
