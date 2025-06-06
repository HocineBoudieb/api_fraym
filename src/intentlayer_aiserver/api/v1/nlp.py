"""Routes API pour l'analyse NLP"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging

from ...models.schemas import NLPRequest, NLPResponse, ErrorResponse
from ...services.nlp_service import NLPService
from ...services.rag_service import RAGService
from ...core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/nlp", tags=["NLP"])

# Instance globale du service NLP
nlp_service: NLPService = None

def get_nlp_service() -> NLPService:
    """Dépendance pour obtenir le service NLP"""
    global nlp_service
    if nlp_service is None:
        nlp_service = NLPService()
    return nlp_service

def get_rag_service() -> RAGService:
    """Dépendance pour obtenir le service RAG depuis l'état global"""
    from ...main import app
    return app.state.rag_service

@router.post("/analyze", response_model=NLPResponse)
async def analyze_text(
    request: NLPRequest,
    nlp_service: NLPService = Depends(get_nlp_service),
    rag_service: RAGService = Depends(get_rag_service)
) -> NLPResponse:
    """
    Analyse une requête en langage naturel
    
    - **text**: Le texte à analyser
    - **input_type**: Type d'entrée (text, voice, etc.)
    - **user_id**: Identifiant de l'utilisateur (optionnel)
    - **session_id**: Identifiant de session (optionnel)
    - **context**: Contexte additionnel (optionnel)
    
    Retourne:
    - **entities**: Entités extraites
    - **intent**: Intention détectée
    - **sentiment**: Analyse de sentiment
    - **context**: Contexte enrichi
    - **confidence**: Score de confiance global
    """
    try:
        logger.info(f"Analyse NLP demandée pour: {request.text[:100]}...")
        
        # Initialisation du service si nécessaire
        if not nlp_service.initialized:
            await nlp_service.initialize()
        
        # Enrichissement du contexte avec RAG si disponible
        enriched_context = request.context or {}
        
        if rag_service and rag_service.initialized:
            try:
                # Recherche de connaissances pertinentes
                knowledge_results = await rag_service.search_knowledge(request.text, limit=3)
                if knowledge_results:
                    enriched_context["relevant_knowledge"] = [
                        {
                            "content": result["content"][:200] + "..." if len(result["content"]) > 200 else result["content"],
                            "score": result["score"],
                            "metadata": result.get("metadata", {})
                        }
                        for result in knowledge_results
                    ]
                
                # Recherche de composants UI pertinents
                ui_results = await rag_service.search_ui_components(request.text, limit=2)
                if ui_results:
                    enriched_context["relevant_ui_components"] = [
                        {
                            "name": result.get("metadata", {}).get("name", "Unknown"),
                            "type": result.get("metadata", {}).get("type", "Unknown"),
                            "score": result["score"]
                        }
                        for result in ui_results
                    ]
                    
            except Exception as e:
                logger.warning(f"Erreur lors de l'enrichissement RAG: {e}")
        
        # Création de la requête enrichie
        enriched_request = NLPRequest(
            text=request.text,
            input_type=request.input_type,
            user_id=request.user_id,
            session_id=request.session_id,
            context=enriched_context
        )
        
        # Analyse NLP
        response = await nlp_service.analyze_request(enriched_request)
        
        logger.info(f"Analyse terminée - Intent: {response.intent}, Confiance: {response.confidence}")
        return response
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse NLP: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'analyse: {str(e)}"
        )

@router.post("/extract-entities", response_model=Dict[str, Any])
async def extract_entities(
    request: Dict[str, str],
    nlp_service: NLPService = Depends(get_nlp_service)
) -> Dict[str, Any]:
    """
    Extrait uniquement les entités d'un texte
    
    - **text**: Le texte à analyser
    
    Retourne:
    - **entities**: Liste des entités extraites
    - **entity_types**: Types d'entités trouvées
    """
    try:
        text = request.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="Le texte est requis")
        
        logger.info(f"Extraction d'entités pour: {text[:100]}...")
        
        # Initialisation du service si nécessaire
        if not nlp_service.initialized:
            await nlp_service.initialize()
        
        # Extraction des entités
        entities = await nlp_service._extract_entities(text)
        
        # Groupement par type
        entity_types = {}
        for entity in entities:
            entity_type = entity.get("label", "UNKNOWN")
            if entity_type not in entity_types:
                entity_types[entity_type] = []
            entity_types[entity_type].append(entity["text"])
        
        return {
            "entities": entities,
            "entity_types": entity_types,
            "total_entities": len(entities)
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction d'entités: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'extraction: {str(e)}"
        )

@router.post("/detect-intent", response_model=Dict[str, Any])
async def detect_intent(
    request: Dict[str, Any],
    nlp_service: NLPService = Depends(get_nlp_service)
) -> Dict[str, Any]:
    """
    Détecte uniquement l'intention d'un texte
    
    - **text**: Le texte à analyser
    - **context**: Contexte additionnel (optionnel)
    
    Retourne:
    - **intent**: Intention détectée
    - **confidence**: Score de confiance
    - **alternatives**: Intentions alternatives possibles
    """
    try:
        text = request.get("text", "")
        context = request.get("context", {})
        
        if not text:
            raise HTTPException(status_code=400, detail="Le texte est requis")
        
        logger.info(f"Détection d'intention pour: {text[:100]}...")
        
        # Initialisation du service si nécessaire
        if not nlp_service.initialized:
            await nlp_service.initialize()
        
        # Détection d'intention
        intent_result = await nlp_service._detect_intent(text, context)
        
        # Génération d'alternatives basiques
        alternatives = []
        if intent_result["confidence"] < 0.8:
            # Si la confiance est faible, proposer des alternatives
            fallback_intents = ["information", "help", "navigation", "action"]
            for alt_intent in fallback_intents:
                if alt_intent != intent_result["intent"]:
                    alternatives.append({
                        "intent": alt_intent,
                        "confidence": max(0.1, intent_result["confidence"] - 0.2)
                    })
        
        return {
            "intent": intent_result["intent"],
            "confidence": intent_result["confidence"],
            "reasoning": intent_result.get("reasoning", ""),
            "alternatives": alternatives[:3]  # Top 3 alternatives
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la détection d'intention: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la détection: {str(e)}"
        )

@router.post("/sentiment", response_model=Dict[str, Any])
async def analyze_sentiment(
    request: Dict[str, str],
    nlp_service: NLPService = Depends(get_nlp_service)
) -> Dict[str, Any]:
    """
    Analyse le sentiment d'un texte
    
    - **text**: Le texte à analyser
    
    Retourne:
    - **sentiment**: Sentiment détecté (positive, negative, neutral)
    - **confidence**: Score de confiance
    - **scores**: Scores détaillés par sentiment
    """
    try:
        text = request.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="Le texte est requis")
        
        logger.info(f"Analyse de sentiment pour: {text[:100]}...")
        
        # Initialisation du service si nécessaire
        if not nlp_service.initialized:
            await nlp_service.initialize()
        
        # Analyse de sentiment
        sentiment_result = await nlp_service._analyze_sentiment(text)
        
        return {
            "sentiment": sentiment_result["sentiment"],
            "confidence": sentiment_result["confidence"],
            "scores": sentiment_result.get("scores", {}),
            "text_length": len(text)
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse de sentiment: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'analyse: {str(e)}"
        )

@router.get("/health")
async def nlp_health(
    nlp_service: NLPService = Depends(get_nlp_service)
) -> Dict[str, Any]:
    """
    Vérifie l'état de santé du service NLP
    """
    try:
        health_status = {
            "service": "NLP",
            "status": "healthy" if nlp_service.initialized else "initializing",
            "initialized": nlp_service.initialized,
            "spacy_model": settings.spacy_model,
            "openai_configured": bool(settings.openai_api_key)
        }
        
        # Test rapide si initialisé
        if nlp_service.initialized:
            try:
                test_result = await nlp_service._extract_entities("Test de santé du service")
                health_status["test_extraction"] = "success"
                health_status["test_entities_count"] = len(test_result)
            except Exception as e:
                health_status["test_extraction"] = "failed"
                health_status["test_error"] = str(e)
        
        return health_status
        
    except Exception as e:
        logger.error(f"Erreur lors du check de santé NLP: {e}")
        return {
            "service": "NLP",
            "status": "error",
            "error": str(e)
        }

@router.get("/models")
async def get_nlp_models() -> Dict[str, Any]:
    """
    Retourne les informations sur les modèles NLP utilisés
    """
    return {
        "spacy_model": settings.spacy_model,
        "openai_model": settings.openai_model,
        "embedding_model": settings.embedding_model,
        "available_languages": ["fr", "en"],  # Langues supportées
        "supported_entities": [
            "PERSON", "ORG", "GPE", "MONEY", "DATE", 
            "TIME", "PERCENT", "EMAIL", "PHONE", "URL"
        ],
        "supported_intents": [
            "question", "request", "complaint", "compliment",
            "information", "navigation", "purchase", "support",
            "booking", "cancellation", "modification", "help"
        ]
    }