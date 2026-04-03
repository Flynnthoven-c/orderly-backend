"""
Orderly - Punto de entrada de la aplicación FastAPI.
Sistema de gestión de pedidos para negocios de comida rápida.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS
from app.database import engine, Base


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


@app.get("/")
async def root():
    """Endpoint raíz para verificar que la API está corriendo."""
    return {"message": "Orderly API funcionando", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Health check para Railway."""
    return {"status": "ok"}
