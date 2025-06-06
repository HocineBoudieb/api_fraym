"""Configuration du serveur IA IntentLayer"""

from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    """Configuration de l'application"""
    
    # Configuration générale
    app_name: str = "IntentLayer AI Server"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"
    
    # Configuration API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    api_reload: bool = False
    api_log_level: str = "info"
    
    # Configuration OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 1000
    
    # Configuration Mistral (optionnel)
    mistral_api_key: Optional[str] = None
    mistral_model: str = "mistral-medium"
    mistral_max_tokens: int = 1000
    mistral_temperature: float = 0.7
    
    # Configuration Ollama (optionnel)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"
    ollama_timeout: int = 30
    
    # Configuration RAG
    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 200
    rag_top_k: int = 5
    rag_similarity_threshold: float = 0.7
    
    # Configuration base vectorielle
    vector_db_type: str = "chroma"  # "chroma", "faiss"
    vector_db_path: str = "./data/vectordb"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Configuration spaCy
    spacy_model: str = "fr_core_news_sm"  # Modèle français
    
    # Configuration Tokenizers
    tokenizers_parallelism: str = "false"  # Désactive le parallélisme des tokenizers
    
    # Chemins des données
    ui_components_path: str = "./data/ui_components"
    knowledge_base_path: str = "./data/knowledge"
    memory_path: str = "./data/memory"
    
    # Configuration CORS
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    # Configuration logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: str = "./logs/intentlayer.log"
    
    # Configuration performance
    workers: int = 1
    request_timeout: int = 30
    max_request_size: int = 10
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Instance globale des paramètres
settings = Settings()