#!/usr/bin/env python3

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, List, Optional
import logging
import time

from ...models.schemas import (
    SessionRequest, SessionResponse, SessionInfo, ChatRequest, ChatResponse,
    NLPRequest, UIGenerationRequest, ErrorResponse
)
from ...services.session_service import SessionService
from ...services.nlp_service import NLPService
from ...services.rag_service import RAGService
from ...services.ui_generator import UIGeneratorService
from ...services.tts_service import TTSService
from ...core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Sessions"])

# Instances globales des services
session_service: SessionService = None
nlp_service: NLPService = None
ui_generator_service: UIGeneratorService = None
tts_service: TTSService = None

def get_session_service() -> SessionService:
    """Dépendance pour obtenir le service de sessions"""
    global session_service
    if session_service is None:
        session_service = SessionService()
    return session_service

def get_nlp_service() -> NLPService:
    """Dépendance pour obtenir le service NLP"""
    global nlp_service
    if nlp_service is None:
        nlp_service = NLPService()
    return nlp_service

def get_ui_generator_service() -> UIGeneratorService:
    """Dépendance pour obtenir le service de génération UI"""
    global ui_generator_service
    if ui_generator_service is None:
        rag_service = get_rag_service()
        ui_generator_service = UIGeneratorService(rag_service)
    return ui_generator_service

def get_tts_service() -> TTSService:
    """Dépendance pour obtenir le service TTS"""
    global tts_service
    if tts_service is None:
        tts_service = TTSService()
    return tts_service

def get_rag_service() -> RAGService:
    """Dépendance pour obtenir le service RAG depuis l'état global"""
    from ...main import app
    return app.state.rag_service

@router.post("/create", response_model=SessionResponse)
async def create_session(
    request: SessionRequest,
    session_service: SessionService = Depends(get_session_service)
) -> SessionResponse:
    """
    Crée une nouvelle session pour un utilisateur
    
    - **user_id**: Identifiant unique de l'utilisateur
    - **user_data**: Données utilisateur optionnelles (préférences, profil, etc.)
    - **context**: Contexte initial optionnel
    
    Retourne:
    - **success**: Succès de l'opération
    - **message**: Message de confirmation
    - **session_info**: Informations de la session créée
    """
    try:
        logger.info(f"Création de session demandée pour utilisateur: {request.user_id}")
        
        # Initialisation du service si nécessaire
        if not session_service.initialized:
            await session_service.initialize()
        
        # Validation des données
        if not request.user_id or len(request.user_id.strip()) == 0:
            raise HTTPException(status_code=400, detail="L'ID utilisateur est requis")
        
        # Création de la session
        response = await session_service.create_session(
            user_id=request.user_id,
            user_data=request.user_data
        )
        
        if response.success and request.context:
            # Mise à jour du contexte initial si fourni
            await session_service.update_session_activity(
                session_id=response.session_info.session_id,
                context=request.context
            )
        
        logger.info(f"Session créée avec succès: {response.session_info.session_id if response.session_info else 'N/A'}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la création de session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la création de session: {str(e)}"
        )

@router.get("/info/{session_id}", response_model=SessionResponse)
async def get_session_info(
    session_id: str,
    session_service: SessionService = Depends(get_session_service)
) -> SessionResponse:
    """
    Récupère les informations d'une session
    
    - **session_id**: Identifiant de la session
    
    Retourne les informations de la session si elle existe et est active
    """
    try:
        logger.info(f"Récupération d'informations pour session: {session_id}")
        
        # Initialisation du service si nécessaire
        if not session_service.initialized:
            await session_service.initialize()
        
        # Récupération de la session
        session_info = await session_service.get_session(session_id)
        
        if session_info is None:
            raise HTTPException(
                status_code=404,
                detail="Session non trouvée ou expirée"
            )
        
        return SessionResponse(
            success=True,
            message="Session trouvée",
            session_info=session_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération de session: {str(e)}"
        )

@router.delete("/delete/{session_id}", response_model=SessionResponse)
async def delete_session(
    session_id: str,
    session_service: SessionService = Depends(get_session_service)
) -> SessionResponse:
    """
    Supprime une session
    
    - **session_id**: Identifiant de la session à supprimer
    
    Retourne le statut de l'opération
    """
    try:
        logger.info(f"Suppression demandée pour session: {session_id}")
        
        # Initialisation du service si nécessaire
        if not session_service.initialized:
            await session_service.initialize()
        
        # Suppression de la session
        success = await session_service.delete_session(session_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Session non trouvée"
            )
        
        return SessionResponse(
            success=True,
            message="Session supprimée avec succès",
            session_info=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la suppression de session: {str(e)}"
        )

@router.get("/user/{user_id}", response_model=List[SessionInfo])
async def get_user_sessions(
    user_id: str,
    session_service: SessionService = Depends(get_session_service)
) -> List[SessionInfo]:
    """
    Récupère toutes les sessions actives d'un utilisateur
    
    - **user_id**: Identifiant de l'utilisateur
    
    Retourne la liste des sessions actives de l'utilisateur
    """
    try:
        logger.info(f"Récupération des sessions pour utilisateur: {user_id}")
        
        # Initialisation du service si nécessaire
        if not session_service.initialized:
            await session_service.initialize()
        
        # Récupération des sessions utilisateur
        sessions = await session_service.get_user_sessions(user_id)
        
        return sessions
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des sessions utilisateur: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des sessions: {str(e)}"
        )

@router.post("/chat", response_model=ChatResponse)
async def chat_with_session(
    request: ChatRequest,
    session_service: SessionService = Depends(get_session_service),
    nlp_service: NLPService = Depends(get_nlp_service),
    ui_generator_service: UIGeneratorService = Depends(get_ui_generator_service),
    tts_service: TTSService = Depends(get_tts_service),
    rag_service: RAGService = Depends(get_rag_service)
) -> ChatResponse:
    """
    Traite un message de chat dans le contexte d'une session
    
    - **session_id**: Identifiant de la session
    - **message**: Message de l'utilisateur
    - **input_type**: Type d'entrée (text, voice, etc.)
    - **context**: Contexte additionnel optionnel
    
    Retourne:
    - **response_text**: Réponse textuelle
    - **response_audio**: URL de la réponse vocale (si applicable)
    - **ui_components**: Composants UI sélectionnés
    - **nlp_analysis**: Analyse NLP complète
    - **session_info**: Informations de session mises à jour
    """
    start_time = time.time()
    
    try:
        logger.info(f"Message de chat reçu pour session: {request.session_id}")
        
        # Initialisation des services si nécessaire
        if not session_service.initialized:
            await session_service.initialize()
        if not nlp_service.initialized:
            await nlp_service.initialize()
        if not ui_generator_service.initialized:
            await ui_generator_service.initialize()
        if not tts_service.initialized:
            await tts_service.initialize()
        
        # Vérification de la session
        session_info = await session_service.get_session(request.session_id)
        if session_info is None:
            raise HTTPException(
                status_code=404,
                detail="Session non trouvée ou expirée"
            )
        
        # Récupération du contexte de session
        session_context = await session_service.get_session_context(request.session_id)
        
        # Enrichissement du contexte avec les données de la requête
        enriched_context = {**session_context}
        if request.context:
            enriched_context.update(request.context)
        
        # Enrichissement du contexte avec RAG si disponible
        rag_service = get_rag_service()
        if rag_service and rag_service.initialized:
            try:
                # Recherche de connaissances pertinentes
                knowledge_results = await rag_service.search_knowledge(request.message, top_k=3)
                if knowledge_results:
                    enriched_context["relevant_knowledge"] = [
                        {
                            "content": result["content"][:500] + "..." if len(result["content"]) > 500 else result["content"],
                            "score": result["score"],
                            "metadata": result.get("metadata", {})
                        }
                        for result in knowledge_results
                    ]
                
                # Recherche de composants UI pertinents
                ui_results = await rag_service.search_ui_components(request.message, top_k=2)
                if ui_results:
                    enriched_context["relevant_ui_components"] = [
                        {
                            "name": result.get("metadata", {}).get("name", "Unknown"),
                            "type": result.get("metadata", {}).get("type", "Unknown"),
                            "score": result["score"]
                        }
                        for result in ui_results
                    ]
                
                # Recherche d'images pertinentes
                image_results = await rag_service.search_images(request.message, top_k=3)
                if image_results:
                    enriched_context["relevant_images"] = [
                        {
                            "id": result.get("id", ""),
                            "url": result.get("url", ""),
                            "alt": result.get("alt", ""),
                            "description": result.get("description", ""),
                            "score": result.get("relevance_score", 0)
                        }
                        for result in image_results
                    ]
                    
            except Exception as e:
                logger.warning(f"Erreur lors de l'enrichissement RAG: {e}")
        
        # Création de la requête NLP enrichie
        nlp_request = NLPRequest(
            text=request.message,
            input_type=request.input_type,
            user_id=session_info.user_id,
            session_id=request.session_id,
            context=enriched_context
        )
        
        # Analyse NLP
        nlp_response = await nlp_service.analyze_request(nlp_request)
        
        # Génération des composants UI basée sur l'intention
        ui_components = []
        if nlp_response.intent:
            try:
                ui_request = UIGenerationRequest(
                    intent=nlp_response.intent.description,
                    context={
                        "intent_type": nlp_response.intent.type,
                        "entities": [entity.dict() for entity in nlp_response.entities],
                        "user_context": enriched_context
                    }
                )
                
                ui_response = await ui_generator_service.generate_ui(ui_request)
                if ui_response.get("layout") and ui_response["layout"].get("components"):
                    ui_components = ui_response["layout"]["components"]
                
                # Ajout des images pertinentes aux composants UI
                relevant_images = enriched_context.get("relevant_images", [])
                if relevant_images:
                    for image in relevant_images:
                        image_component = {
                            "type": "image",
                            "id": f"contextual_image_{image.get('id', 'unknown')}",
                            "properties": {
                                "src": image.get("url", ""),
                                "alt": image.get("alt", ""),
                                "title": image.get("description", ""),
                                "relevance_score": image.get("score", 0)
                            },
                            "style": {
                                "maxWidth": "300px",
                                "height": "auto",
                                "borderRadius": "8px",
                                "margin": "10px 0"
                            },
                            "metadata": {
                                "source": "rag_image_search",
                                "contextual": True
                            }
                        }
                        ui_components.append(image_component)
                    
            except Exception as e:
                logger.warning(f"Erreur lors de la génération UI: {e}")
        
        # Génération de la réponse textuelle
        response_text = await _generate_response_text(nlp_response, enriched_context)
        
        # Génération de la réponse vocale
        response_audio = None
        try:
            response_audio = await tts_service.text_to_speech(response_text, language='fr')
        except Exception as e:
            logger.warning(f"Erreur lors de la génération audio: {e}")
        
        # Mise à jour de l'activité de session
        await session_service.update_session_activity(
            session_id=request.session_id,
            context={
                "last_message": request.message,
                "last_intent": nlp_response.intent.type if nlp_response.intent else None,
                "last_entities": [entity.text for entity in nlp_response.entities]
            }
        )
        
        # Récupération des informations de session mises à jour
        updated_session_info = await session_service.get_session(request.session_id)
        
        processing_time = time.time() - start_time
        
        return ChatResponse(
            success=True,
            message="Message traité avec succès",
            response_text=response_text,
            response_audio=response_audio,
            ui_components=ui_components,
            nlp_analysis=nlp_response,
            session_info=updated_session_info,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du traitement du chat: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du traitement du message: {str(e)}"
        )

async def _generate_response_text(nlp_response, context: Dict[str, Any]) -> str:
    """
    Génère une réponse textuelle basée sur l'analyse NLP
    """
    try:
        if not nlp_response.intent:
            return "Je n'ai pas bien compris votre demande. Pouvez-vous reformuler ?"
        
        intent_type = nlp_response.intent.type
        intent_description = nlp_response.intent.description
        
        # Utiliser les connaissances RAG si disponibles
        relevant_knowledge = context.get("relevant_knowledge", [])
        
        # Réponses basées sur le type d'intention
        if intent_type == "question":
            if relevant_knowledge:
                # Construire une réponse détaillée basée sur les connaissances
                knowledge_parts = []
                for knowledge in relevant_knowledge[:2]:  # Utiliser les 2 meilleures correspondances
                    content = knowledge.get("content", "")
                    if content:
                        knowledge_parts.append(content)
                
                if knowledge_parts:
                    combined_knowledge = " ".join(knowledge_parts)
                    return f"Voici ce que je peux vous dire : {combined_knowledge}"
                else:
                    return f"Je comprends que vous avez une question sur : {intent_description}. Laissez-moi vous aider avec les informations disponibles."
            else:
                return f"Je comprends que vous avez une question sur : {intent_description}. Laissez-moi vous aider."
        
        elif intent_type == "command":
            return f"J'ai compris votre demande : {intent_description}. Je vais traiter cela pour vous."
        
        elif intent_type == "navigation":
            return f"Je vais vous aider à naviguer vers : {intent_description}."
        
        elif intent_type == "search":
            entities = [entity.text for entity in nlp_response.entities]
            search_terms = ", ".join(entities) if entities else intent_description
            
            if relevant_knowledge:
                # Fournir des résultats de recherche basés sur les connaissances
                search_results = []
                for knowledge in relevant_knowledge:
                    content = knowledge.get("content", "")
                    if content:
                        search_results.append(content)
                
                if search_results:
                    combined_results = " ".join(search_results[:2])
                    return f"Voici ce que j'ai trouvé concernant {search_terms} : {combined_results}"
            
            return f"Je recherche des informations sur : {search_terms}."
        
        elif intent_type == "form_fill":
            return f"Je vais vous aider à remplir le formulaire pour : {intent_description}."
        
        elif intent_type == "purchase":
            return f"Je vais vous assister dans votre achat : {intent_description}."
        
        elif intent_type == "support":
            return f"Je suis là pour vous aider avec : {intent_description}. Comment puis-je vous assister ?"
        
        else:
            # Type d'intention non reconnu ou autre
            if relevant_knowledge:
                knowledge_text = relevant_knowledge[0].get("content", "")
                return f"Voici des informations qui pourraient vous intéresser : {knowledge_text}"
            else:
                return f"J'ai analysé votre message : {intent_description}. Comment puis-je vous aider davantage ?"
    
    except Exception as e:
        logger.error(f"Erreur lors de la génération de la réponse textuelle: {e}")
        return "Je rencontre une difficulté technique. Pouvez-vous reformuler votre demande ?"