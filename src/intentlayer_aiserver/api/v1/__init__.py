"""API v1 pour le serveur IA IntentLayer"""

from fastapi import APIRouter

from . import nlp, ui_generator, memory

# Router principal pour l'API v1
api_router = APIRouter(prefix="/api/v1")

# Inclusion des sous-routers
api_router.include_router(nlp.router)
api_router.include_router(ui_generator.router)
api_router.include_router(memory.router)

__all__ = ["api_router"]