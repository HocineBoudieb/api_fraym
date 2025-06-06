"""Point d'entrée principal du serveur IA IntentLayer"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
from dotenv import load_dotenv
import os
from pathlib import Path

from .api.v1 import nlp, ui_generator, memory, sessions
from .core.config import settings
from .services.rag_service import RAGService
from .services.session_service import SessionService

# Charger les variables d'environnement
load_dotenv()

# Instances globales des services
rag_service = None
session_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie de l'application"""
    global rag_service, session_service
    
    # Initialisation au démarrage
    print("🚀 Initialisation du serveur IA IntentLayer...")
    
    # Initialisation du service RAG
    rag_service = RAGService()
    await rag_service.initialize()
    app.state.rag_service = rag_service
    
    # Initialisation du service de sessions
    session_service = SessionService()
    await session_service.initialize()
    app.state.session_service = session_service
    
    print("✅ Serveur IA initialisé avec succès")
    
    yield
    
    # Nettoyage à l'arrêt
    print("🔄 Arrêt du serveur IA...")
    if rag_service:
        await rag_service.cleanup()
    if session_service:
        await session_service.cleanup()
    print("✅ Serveur IA arrêté proprement")

# Création de l'application FastAPI
app = FastAPI(
    title="IntentLayer AI Server",
    description="Serveur IA modulaire pour analyse NLP et génération d'UI",
    version="0.1.0",
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À configurer selon vos besoins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routes
app.include_router(nlp.router, prefix="/api/v1/nlp", tags=["NLP"])
app.include_router(ui_generator.router, prefix="/api/v1/ui", tags=["UI Generator"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["Memory"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["Sessions"])

# Montage des fichiers statiques pour l'audio
audio_path = Path(settings.memory_path) / "audio"
audio_path.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(audio_path)), name="audio")

# Montage des fichiers statiques pour les images
images_path = Path("static/images")
images_path.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=str(images_path)), name="images")

@app.get("/")
async def root():
    """Point d'entrée racine de l'API"""
    return {
        "message": "IntentLayer AI Server",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "nlp": "/api/v1/nlp",
            "ui_generator": "/api/v1/ui",
            "memory": "/api/v1/memory",
            "sessions": "/api/v1/sessions",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Vérification de l'état de santé du serveur"""
    return {
        "status": "healthy",
        "rag_service": "initialized" if rag_service else "not_initialized",
        "session_service": "initialized" if session_service else "not_initialized"
    }

if __name__ == "__main__":
    uvicorn.run(
        "src.intentlayer_aiserver.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )