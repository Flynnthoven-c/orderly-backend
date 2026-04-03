"""
Orderly - Seeds de ejemplo.
Crea datos iniciales: 1 negocio, 5 productos y 2 reglas de lealtad.
Ejecutar: python -m app.seeds
"""

import asyncio
from sqlalchemy import select

from app.database import engine, async_session, Base
from app.models import Business, Product, LoyaltyRule


async def seed():
    """Inserta datos de ejemplo si la base de datos está vacía."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Verificar si ya existen datos
        result = await session.execute(select(Business))
        if result.scalars().first():
            print("La base de datos ya tiene datos. No se insertaron seeds.")
            return

        # Negocio de ejemplo
        negocio = Business(
            name="Burger Palace",
            whatsapp_number="+521234567890",
            currency="MXN",
            active=True,
        )
        session.add(negocio)
        await session.flush()

        # Productos de ejemplo
        productos = [
            Product(
                business_id=negocio.id,
                name="Hamburguesa Clásica",
                description="Carne de res, lechuga, tomate, cebolla y aderezo especial",
                price=89.00,
                available=True,
            ),
            Product(
                business_id=negocio.id,
                name="Hamburguesa Doble",
                description="Doble carne, doble queso, lechuga y tomate",
                price=129.00,
                available=True,
            ),
            Product(
                business_id=negocio.id,
                name="Papas Francesas",
                description="Papas fritas crujientes con sal",
                price=45.00,
                available=True,
            ),
            Product(
                business_id=negocio.id,
                name="Refresco",
                description="Refresco de 600ml (Coca-Cola, Sprite, Fanta)",
                price=30.00,
                available=True,
            ),
            Product(
                business_id=negocio.id,
                name="Combo Clásico",
                description="Hamburguesa Clásica + Papas + Refresco",
                price=139.00,
                available=True,
            ),
        ]
        session.add_all(productos)
        await session.flush()

        # Reglas de lealtad de ejemplo
        reglas = [
            LoyaltyRule(
                business_id=negocio.id,
                product_id=productos[0].id,  # Hamburguesa Clásica
                name="Hamburguesa Gratis",
                description="Cada 6 hamburguesas clásicas, la 7ma es gratis",
                rule_type="product_count",
                threshold=6,
                reward_description="1 Hamburguesa Clásica GRATIS",
                active=True,
            ),
            LoyaltyRule(
                business_id=negocio.id,
                product_id=None,  # Aplica a cualquier compra
                name="Papas Gratis por Monto",
                description="Por cada $500 gastados, unas papas gratis",
                rule_type="total_spent",
                threshold=500,
                reward_description="1 orden de Papas Francesas GRATIS",
                active=True,
            ),
        ]
        session.add_all(reglas)

        await session.commit()
        print("Seeds insertados correctamente:")
        print(f"  - 1 negocio: {negocio.name}")
        print(f"  - {len(productos)} productos")
        print(f"  - {len(reglas)} reglas de lealtad")


if __name__ == "__main__":
    asyncio.run(seed())
