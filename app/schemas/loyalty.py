"""
Orderly - Schemas de lealtad.
"""

from datetime import datetime
from pydantic import BaseModel


class LoyaltyRuleCreate(BaseModel):
    business_id: int
    product_id: int | None = None
    name: str
    description: str | None = None
    rule_type: str  # product_count o total_spent
    threshold: int
    reward_description: str
    active: bool = True


class LoyaltyRuleUpdate(BaseModel):
    product_id: int | None = None
    name: str | None = None
    description: str | None = None
    rule_type: str | None = None
    threshold: int | None = None
    reward_description: str | None = None
    active: bool | None = None


class LoyaltyRuleOut(BaseModel):
    id: int
    business_id: int
    product_id: int | None
    product_name: str | None = None
    name: str
    description: str | None
    rule_type: str
    threshold: int
    reward_description: str
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoyaltyProgressOut(BaseModel):
    id: int
    customer_id: int
    rule_id: int
    rule_name: str | None = None
    rule_type: str | None = None
    threshold: int | None = None
    reward_description: str | None = None
    product_name: str | None = None
    current_count: int
    redeemed_count: int
    last_updated: datetime

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    today_sales: float
    week_sales: float
    active_orders: int
    top_product: str | None
    top_product_count: int
    new_customers_today: int
    orders_by_status: dict[str, int]
