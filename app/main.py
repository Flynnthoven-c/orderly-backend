"""
Orderly - Punto de entrada de la aplicación FastAPI.
Sistema de gestión de pedidos para negocios de comida rápida.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS
from app.database import engine, Base
from app.routers.webhook import router as webhook_router
from app.routers.products import router as products_router
from app.routers.orders import router as orders_router
from app.routers.customers import router as customers_router
from app.routers.loyalty import router as loyalty_router
from app.routers.dashboard import router as dashboard_router
from app.routers.auth import router as auth_router
from app.routers.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la app: crea tablas al iniciar (solo desarrollo)."""
    yield


app = FastAPI(
    title="Orderly API",
    description="API para gestión de pedidos de comida rápida con chatbot WhatsApp",
    version="1.0.0",
    lifespan=lifespan,
)

# Configuración de CORS para permitir peticiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Registrar routers
app.include_router(webhook_router)
app.include_router(products_router)
app.include_router(orders_router)
app.include_router(customers_router)
app.include_router(loyalty_router)
app.include_router(dashboard_router)
app.include_router(auth_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    """Endpoint raíz para verificar que la API está corriendo."""
    return {"message": "Orderly API funcionando", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Health check para Railway."""
    return {"status": "ok"}
