"""
Orderly - Router de reglas de lealtad y progreso.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import LoyaltyRule, LoyaltyProgress, Business
from app.schemas.loyalty import (
    LoyaltyRuleCreate, LoyaltyRuleUpdate, LoyaltyRuleOut, LoyaltyProgressOut,
)
from app.auth import get_current_business

router = APIRouter(prefix="/loyalty", tags=["loyalty"])


@router.get("/rules", response_model=list[LoyaltyRuleOut])
async def list_rules(
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    """Lista las reglas de lealtad del negocio autenticado."""
    result = await db.execute(
        select(LoyaltyRule)
        .where(LoyaltyRule.business_id == business.id)
        .options(selectinload(LoyaltyRule.product))
        .order_by(LoyaltyRule.created_at.desc())
    )
    rules = result.scalars().all()

    return [
        LoyaltyRuleOut(
            id=r.id,
            business_id=r.business_id,
            product_id=r.product_id,
            product_name=r.product.name if r.product else None,
            name=r.name,
            description=r.description,
            rule_type=r.rule_type,
            threshold=r.threshold,
            reward_description=r.reward_description,
            active=r.active,
            created_at=r.created_at,
        )
        for r in rules
    ]


@router.post("/rules", response_model=LoyaltyRuleOut, status_code=201)
async def create_rule(
    data: LoyaltyRuleCreate,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    """Crea una nueva regla de lealtad para el negocio autenticado."""
    rule = LoyaltyRule(**{**data.model_dump(exclude={"business_id"}), "business_id": business.id})
    db.add(rule)
    await db.flush()

    # Recargar con relación de producto
    result = await db.execute(
        select(LoyaltyRule)
        .where(LoyaltyRule.id == rule.id)
        .options(selectinload(LoyaltyRule.product))
    )
    rule = result.scalars().first()

    return LoyaltyRuleOut(
        id=rule.id,
        business_id=rule.business_id,
        product_id=rule.product_id,
        product_name=rule.product.name if rule.product else None,
        name=rule.name,
        description=rule.description,
        rule_type=rule.rule_type,
        threshold=rule.threshold,
        reward_description=rule.reward_description,
        active=rule.active,
        created_at=rule.created_at,
    )


@router.put("/rules/{rule_id}", response_model=LoyaltyRuleOut)
async def update_rule(
    rule_id: int,
    data: LoyaltyRuleUpdate,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    """Edita una regla de lealtad del negocio autenticado."""
    result = await db.execute(
        select(LoyaltyRule)
        .where(LoyaltyRule.id == rule_id, LoyaltyRule.business_id == business.id)
        .options(selectinload(LoyaltyRule.product))
    )
    rule = result.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Regla no encontrada")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)

    await db.flush()

    # Recargar por si cambió el product_id
    result = await db.execute(
        select(LoyaltyRule)
        .where(LoyaltyRule.id == rule.id)
        .options(selectinload(LoyaltyRule.product))
    )
    rule = result.scalars().first()

    return LoyaltyRuleOut(
        id=rule.id,
        business_id=rule.business_id,
        product_id=rule.product_id,
        product_name=rule.product.name if rule.product else None,
        name=rule.name,
        description=rule.description,
        rule_type=rule.rule_type,
        threshold=rule.threshold,
        reward_description=rule.reward_description,
        active=rule.active,
        created_at=rule.created_at,
    )


@router.get("/progress/{customer_id}", response_model=list[LoyaltyProgressOut])
async def get_customer_progress(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    """Progreso de lealtad de un cliente del negocio autenticado."""
    from app.models import Customer
    # Verificar que el cliente pertenece al negocio autenticado
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.business_id == business.id)
    )
    if not customer_result.scalars().first():
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    result = await db.execute(
        select(LoyaltyProgress)
        .where(LoyaltyProgress.customer_id == customer_id)
        .options(selectinload(LoyaltyProgress.rule).selectinload(LoyaltyRule.product))
    )
    progress_list = result.scalars().all()

    return [
        LoyaltyProgressOut(
            id=p.id,
            customer_id=p.customer_id,
            rule_id=p.rule_id,
            rule_name=p.rule.name,
            rule_type=p.rule.rule_type,
            threshold=p.rule.threshold,
            reward_description=p.rule.reward_description,
            product_name=p.rule.product.name if p.rule.product else None,
            current_count=p.current_count,
            redeemed_count=p.redeemed_count,
            last_updated=p.last_updated,
        )
        for p in progress_list
    ]
