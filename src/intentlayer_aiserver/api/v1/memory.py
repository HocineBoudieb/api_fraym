"""Routes API pour la gestion de la mémoire contextuelle"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, List, Optional
import logging

from ...models.schemas import MemoryRequest, MemoryResponse, MemoryEntry, ErrorResponse
from ...services.memory_service import MemoryService
from ...core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["Memory"])

# Instance globale du service de mémoire
memory_service: MemoryService = None

def get_memory_service() -> MemoryService:
    """Dépendance pour obtenir le service de mémoire"""
    global memory_service
    if memory_service is None:
        memory_service = MemoryService()
    return memory_service

@router.post("/store", response_model=MemoryResponse)
async def store_interaction(
    request: MemoryRequest,
    memory_service: MemoryService = Depends(get_memory_service)
) -> MemoryResponse:
    """
    Stocke une interaction utilisateur dans la mémoire contextuelle
    
    - **user_id**: Identifiant de l'utilisateur
    - **session_id**: Identifiant de session (optionnel)
    - **interaction**: Données de l'interaction
    - **context**: Contexte additionnel (optionnel)
    
    Retourne:
    - **success**: Succès de l'opération
    - **message**: Message de confirmation
    - **memory_entries**: Entrées de mémoire créées
    - **context_summary**: Résumé du contexte utilisateur
    """
    try:
        logger.info(f"Stockage d'interaction pour utilisateur: {request.user_id}")
        
        # Initialisation du service si nécessaire
        if not memory_service.initialized:
            await memory_service.initialize()
        
        # Validation des données
        if not request.user_id:
            raise HTTPException(status_code=400, detail="L'ID utilisateur est requis")
        
        if not request.interaction:
            raise HTTPException(status_code=400, detail="Les données d'interaction sont requises")
        
        # Stockage de l'interaction
        response = await memory_service.store_interaction(request)
        
        logger.info(f"Interaction stockée avec succès pour: {request.user_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du stockage de l'interaction: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du stockage: {str(e)}"
        )

@router.get("/context/{user_id}", response_model=MemoryResponse)
async def get_user_context(
    user_id: str,
    session_id: Optional[str] = Query(None, description="ID de session pour filtrer"),
    limit: int = Query(10, ge=1, le=50, description="Nombre maximum d'entrées à retourner"),
    memory_service: MemoryService = Depends(get_memory_service)
) -> MemoryResponse:
    """
    Récupère le contexte d'un utilisateur
    
    - **user_id**: Identifiant de l'utilisateur
    - **session_id**: Filtrer par session (optionnel)
    - **limit**: Nombre maximum d'entrées (1-50, défaut: 10)
    
    Retourne le contexte et l'historique de l'utilisateur
    """
    try:
        logger.info(f"Récupération du contexte pour utilisateur: {user_id}")
        
        # Initialisation du service si nécessaire
        if not memory_service.initialized:
            await memory_service.initialize()
        
        # Récupération du contexte
        response = await memory_service.get_user_context(
            user_id=user_id,
            session_id=session_id,
            limit=limit
        )
        
        logger.info(f"Contexte récupéré: {len(response.memory_entries or [])} entrées")
        return response
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du contexte: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération: {str(e)}"
        )

@router.get("/search/{user_id}", response_model=MemoryResponse)
async def search_user_memory(
    user_id: str,
    query: str = Query(..., description="Requête de recherche"),
    limit: int = Query(5, ge=1, le=20, description="Nombre maximum de résultats"),
    memory_service: MemoryService = Depends(get_memory_service)
) -> MemoryResponse:
    """
    Recherche dans la mémoire d'un utilisateur
    
    - **user_id**: Identifiant de l'utilisateur
    - **query**: Requête de recherche
    - **limit**: Nombre maximum de résultats (1-20, défaut: 5)
    
    Retourne les entrées correspondant à la recherche
    """
    try:
        logger.info(f"Recherche dans la mémoire de {user_id}: {query}")
        
        # Initialisation du service si nécessaire
        if not memory_service.initialized:
            await memory_service.initialize()
        
        # Validation de la requête
        if len(query.strip()) < 2:
            raise HTTPException(
                status_code=400, 
                detail="La requête doit contenir au moins 2 caractères"
            )
        
        # Recherche
        response = await memory_service.search_user_memory(
            user_id=user_id,
            query=query,
            limit=limit
        )
        
        logger.info(f"Recherche terminée: {len(response.memory_entries or [])} résultats")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la recherche: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la recherche: {str(e)}"
        )

@router.put("/preferences/{user_id}", response_model=MemoryResponse)
async def update_user_preferences(
    user_id: str,
    preferences: Dict[str, Any],
    memory_service: MemoryService = Depends(get_memory_service)
) -> MemoryResponse:
    """
    Met à jour les préférences d'un utilisateur
    
    - **user_id**: Identifiant de l'utilisateur
    - **preferences**: Dictionnaire des préférences à mettre à jour
    
    Exemples de préférences:
    - language: "fr" ou "en"
    - theme: "light" ou "dark"
    - ui_complexity: "simple" ou "advanced"
    - notification_preferences: {...}
    """
    try:
        logger.info(f"Mise à jour des préférences pour: {user_id}")
        
        # Initialisation du service si nécessaire
        if not memory_service.initialized:
            await memory_service.initialize()
        
        # Validation des préférences
        if not preferences:
            raise HTTPException(
                status_code=400,
                detail="Les préférences ne peuvent pas être vides"
            )
        
        # Mise à jour
        response = await memory_service.update_user_preferences(
            user_id=user_id,
            preferences=preferences
        )
        
        logger.info(f"Préférences mises à jour pour: {user_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des préférences: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la mise à jour: {str(e)}"
        )

@router.get("/preferences/{user_id}", response_model=Dict[str, Any])
async def get_user_preferences(
    user_id: str,
    memory_service: MemoryService = Depends(get_memory_service)
) -> Dict[str, Any]:
    """
    Récupère les préférences d'un utilisateur
    
    - **user_id**: Identifiant de l'utilisateur
    
    Retourne le dictionnaire des préférences utilisateur
    """
    try:
        logger.info(f"Récupération des préférences pour: {user_id}")
        
        # Initialisation du service si nécessaire
        if not memory_service.initialized:
            await memory_service.initialize()
        
        # Récupération des préférences
        preferences = await memory_service.get_user_preferences(user_id)
        
        logger.info(f"Préférences récupérées pour: {user_id}")
        return preferences
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des préférences: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération: {str(e)}"
        )

@router.delete("/user/{user_id}", response_model=MemoryResponse)
async def cleanup_user_data(
    user_id: str,
    memory_service: MemoryService = Depends(get_memory_service)
) -> MemoryResponse:
    """
    Supprime toutes les données d'un utilisateur (RGPD)
    
    - **user_id**: Identifiant de l'utilisateur
    
    ⚠️ Cette action est irréversible
    """
    try:
        logger.warning(f"Suppression des données utilisateur: {user_id}")
        
        # Initialisation du service si nécessaire
        if not memory_service.initialized:
            await memory_service.initialize()
        
        # Suppression des données
        response = await memory_service.cleanup_user_data(user_id)
        
        logger.warning(f"Données supprimées pour: {user_id}")
        return response
        
    except Exception as e:
        logger.error(f"Erreur lors de la suppression des données: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la suppression: {str(e)}"
        )

@router.get("/stats", response_model=Dict[str, Any])
async def get_memory_stats(
    memory_service: MemoryService = Depends(get_memory_service)
) -> Dict[str, Any]:
    """
    Retourne les statistiques de la mémoire
    
    Informations sur l'utilisation de la mémoire, nombre d'utilisateurs, etc.
    """
    try:
        logger.info("Récupération des statistiques de mémoire")
        
        # Initialisation du service si nécessaire
        if not memory_service.initialized:
            await memory_service.initialize()
        
        # Récupération des statistiques
        stats = await memory_service.get_memory_stats()
        
        logger.info("Statistiques récupérées")
        return stats
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération: {str(e)}"
        )

@router.post("/analyze-patterns/{user_id}", response_model=Dict[str, Any])
async def analyze_user_patterns(
    user_id: str,
    analysis_type: str = Query("behavior", description="Type d'analyse: behavior, preferences, trends"),
    memory_service: MemoryService = Depends(get_memory_service)
) -> Dict[str, Any]:
    """
    Analyse les patterns de comportement d'un utilisateur
    
    - **user_id**: Identifiant de l'utilisateur
    - **analysis_type**: Type d'analyse (behavior, preferences, trends)
    
    Retourne une analyse des patterns d'utilisation
    """
    try:
        logger.info(f"Analyse des patterns pour {user_id}: {analysis_type}")
        
        # Initialisation du service si nécessaire
        if not memory_service.initialized:
            await memory_service.initialize()
        
        # Récupération du contexte utilisateur
        context_response = await memory_service.get_user_context(user_id, limit=50)
        
        if not context_response.memory_entries:
            return {
                "user_id": user_id,
                "analysis_type": analysis_type,
                "message": "Pas assez de données pour l'analyse",
                "patterns": {}
            }
        
        entries = context_response.memory_entries
        patterns = {}
        
        if analysis_type == "behavior":
            # Analyse comportementale
            interaction_types = {}
            hourly_activity = {str(i): 0 for i in range(24)}
            
            for entry in entries:
                # Types d'interaction
                interaction_type = entry.interaction_type
                interaction_types[interaction_type] = interaction_types.get(interaction_type, 0) + 1
                
                # Activité par heure
                hour = entry.timestamp.hour
                hourly_activity[str(hour)] += 1
            
            patterns = {
                "most_common_interactions": dict(sorted(interaction_types.items(), key=lambda x: x[1], reverse=True)[:5]),
                "activity_by_hour": hourly_activity,
                "total_interactions": len(entries),
                "interaction_diversity": len(interaction_types)
            }
        
        elif analysis_type == "preferences":
            # Analyse des préférences
            preferences = await memory_service.get_user_preferences(user_id)
            
            # Analyse des entités fréquentes
            entity_frequency = {}
            for entry in entries:
                entities = entry.context.get("entity_types", [])
                for entity in entities:
                    entity_frequency[entity] = entity_frequency.get(entity, 0) + 1
            
            patterns = {
                "explicit_preferences": preferences,
                "inferred_interests": dict(sorted(entity_frequency.items(), key=lambda x: x[1], reverse=True)[:10]),
                "preference_stability": len(preferences) > 0
            }
        
        elif analysis_type == "trends":
            # Analyse des tendances
            from datetime import datetime, timedelta
            
            # Activité des 7 derniers jours
            week_ago = datetime.now() - timedelta(days=7)
            recent_entries = [e for e in entries if e.timestamp > week_ago]
            
            # Évolution de l'activité
            daily_activity = {}
            for entry in recent_entries:
                day = entry.timestamp.date().isoformat()
                daily_activity[day] = daily_activity.get(day, 0) + 1
            
            patterns = {
                "recent_activity_trend": daily_activity,
                "activity_level": "high" if len(recent_entries) > 10 else "moderate" if len(recent_entries) > 3 else "low",
                "engagement_score": min(100, len(recent_entries) * 10),
                "last_activity": entries[0].timestamp.isoformat() if entries else None
            }
        
        result = {
            "user_id": user_id,
            "analysis_type": analysis_type,
            "patterns": patterns,
            "analyzed_entries": len(entries),
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Analyse terminée pour {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse des patterns: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'analyse: {str(e)}"
        )

@router.get("/health")
async def memory_health(
    memory_service: MemoryService = Depends(get_memory_service)
) -> Dict[str, Any]:
    """
    Vérifie l'état de santé du service de mémoire
    """
    try:
        health_status = {
            "service": "Memory",
            "status": "healthy" if memory_service.initialized else "initializing",
            "initialized": memory_service.initialized,
            "memory_path": str(settings.memory_path)
        }
        
        # Test rapide si initialisé
        if memory_service.initialized:
            try:
                stats = await memory_service.get_memory_stats()
                health_status["test_stats"] = "success"
                health_status["total_users"] = stats.get("total_users", 0)
                health_status["total_entries"] = stats.get("total_entries", 0)
            except Exception as e:
                health_status["test_stats"] = "failed"
                health_status["test_error"] = str(e)
        
        return health_status
        
    except Exception as e:
        logger.error(f"Erreur lors du check de santé Memory: {e}")
        return {
            "service": "Memory",
            "status": "error",
            "error": str(e)
        }