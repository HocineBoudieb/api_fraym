"""Routes API pour la génération d'UI"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import logging

from ...models.schemas import UIGenerationRequest, UIGenerationResponse, UIComponent, UILayout, ErrorResponse
from ...services.ui_generator import UIGeneratorService
from ...services.rag_service import RAGService
from ...services.nlp_service import NLPService
from ...core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ui", tags=["UI Generation"])

# Instance globale du service UI
ui_service: UIGeneratorService = None

def get_ui_service() -> UIGeneratorService:
    """Dépendance pour obtenir le service UI"""
    global ui_service
    if ui_service is None:
        ui_service = UIGeneratorService()
    return ui_service

def get_rag_service() -> RAGService:
    """Dépendance pour obtenir le service RAG depuis l'état global"""
    from ...main import app
    return app.state.rag_service

def get_nlp_service() -> NLPService:
    """Dépendance pour obtenir le service NLP"""
    # Import local pour éviter les imports circulaires
    from .nlp import get_nlp_service
    return get_nlp_service()

@router.post("/generate", response_model=UIGenerationResponse)
async def generate_ui(
    request: UIGenerationRequest,
    ui_service: UIGeneratorService = Depends(get_ui_service),
    rag_service: RAGService = Depends(get_rag_service),
    nlp_service: NLPService = Depends(get_nlp_service)
) -> UIGenerationResponse:
    """
    Génère une interface utilisateur basée sur l'analyse NLP
    
    - **nlp_result**: Résultat de l'analyse NLP
    - **user_preferences**: Préférences utilisateur (optionnel)
    - **context**: Contexte additionnel (optionnel)
    - **ui_constraints**: Contraintes d'UI (optionnel)
    
    Retourne:
    - **layout**: Structure de l'interface générée
    - **components**: Composants UI recommandés
    - **confidence**: Score de confiance
    - **alternatives**: Layouts alternatifs
    """
    try:
        logger.info(f"Génération d'UI demandée pour intent: {request.nlp_result.intent}")
        
        # Initialisation des services si nécessaire
        if not ui_service.initialized:
            await ui_service.initialize()
        
        if rag_service and not rag_service.initialized:
            await rag_service.initialize()
        
        # Génération de l'UI
        response = await ui_service.generate_ui_layout(
            nlp_result=request.nlp_result,
            rag_service=rag_service,
            user_preferences=request.user_preferences,
            context=request.context,
            ui_constraints=request.ui_constraints
        )
        
        logger.info(f"UI générée avec confiance: {response.confidence}")
        return response
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération d'UI: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération: {str(e)}"
        )

@router.post("/components/search", response_model=List[Dict[str, Any]])
async def search_ui_components(
    request: Dict[str, Any],
    rag_service: RAGService = Depends(get_rag_service)
) -> List[Dict[str, Any]]:
    """
    Recherche des composants UI pertinents
    
    - **query**: Requête de recherche
    - **component_type**: Type de composant (optionnel)
    - **limit**: Nombre maximum de résultats (défaut: 10)
    
    Retourne une liste de composants UI avec leurs métadonnées
    """
    try:
        query = request.get("query", "")
        component_type = request.get("component_type")
        limit = request.get("limit", 10)
        
        if not query:
            raise HTTPException(status_code=400, detail="La requête est requise")
        
        logger.info(f"Recherche de composants UI pour: {query}")
        
        # Initialisation du service RAG si nécessaire
        if not rag_service.initialized:
            await rag_service.initialize()
        
        # Recherche des composants
        results = await rag_service.search_ui_components(query, limit=limit)
        
        # Filtrage par type si spécifié
        if component_type:
            results = [
                result for result in results
                if result.get("metadata", {}).get("type") == component_type
            ]
        
        # Formatage des résultats
        formatted_results = []
        for result in results:
            metadata = result.get("metadata", {})
            formatted_results.append({
                "name": metadata.get("name", "Unknown"),
                "type": metadata.get("type", "Unknown"),
                "description": result.get("content", "")[:200] + "..." if len(result.get("content", "")) > 200 else result.get("content", ""),
                "props": metadata.get("props", {}),
                "variants": metadata.get("variants", []),
                "score": result.get("score", 0.0),
                "category": metadata.get("category", "general")
            })
        
        logger.info(f"Trouvé {len(formatted_results)} composants")
        return formatted_results
        
    except Exception as e:
        logger.error(f"Erreur lors de la recherche de composants: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la recherche: {str(e)}"
        )

@router.post("/layout/validate", response_model=Dict[str, Any])
async def validate_ui_layout(
    layout: UILayout,
    ui_service: UIGeneratorService = Depends(get_ui_service)
) -> Dict[str, Any]:
    """
    Valide une structure d'UI
    
    - **layout**: Structure d'UI à valider
    
    Retourne:
    - **valid**: Booléen indiquant si le layout est valide
    - **errors**: Liste des erreurs trouvées
    - **warnings**: Liste des avertissements
    - **suggestions**: Suggestions d'amélioration
    """
    try:
        logger.info(f"Validation de layout: {layout.title}")
        
        errors = []
        warnings = []
        suggestions = []
        
        # Validation de base
        if not layout.title:
            errors.append("Le titre est requis")
        
        if not layout.components:
            errors.append("Au moins un composant est requis")
        
        # Validation des composants
        component_ids = set()
        for component in layout.components:
            # Vérification des IDs uniques
            if component.id in component_ids:
                errors.append(f"ID de composant dupliqué: {component.id}")
            component_ids.add(component.id)
            
            # Vérification des propriétés requises
            if not component.type:
                errors.append(f"Type de composant manquant pour {component.id}")
            
            # Suggestions d'amélioration
            if component.type == "button" and not component.props.get("onClick"):
                suggestions.append(f"Bouton {component.id}: considérer ajouter une action onClick")
            
            if component.type == "form" and not component.children:
                warnings.append(f"Formulaire {component.id}: aucun champ défini")
        
        # Validation de la structure
        if layout.layout_type == "grid" and not layout.grid_config:
            warnings.append("Configuration de grille manquante pour un layout de type grid")
        
        # Suggestions générales
        if len(layout.components) > 10:
            suggestions.append("Layout complexe: considérer diviser en plusieurs sections")
        
        # Vérification de l'accessibilité
        button_count = sum(1 for c in layout.components if c.type == "button")
        if button_count > 5:
            suggestions.append("Beaucoup de boutons: considérer grouper ou utiliser un menu")
        
        is_valid = len(errors) == 0
        
        result = {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
            "component_count": len(layout.components),
            "layout_type": layout.layout_type,
            "accessibility_score": max(0, 100 - len(warnings) * 10 - len(errors) * 20)
        }
        
        logger.info(f"Validation terminée - Valide: {is_valid}, Erreurs: {len(errors)}")
        return result
        
    except Exception as e:
        logger.error(f"Erreur lors de la validation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la validation: {str(e)}"
        )

@router.post("/layout/optimize", response_model=UILayout)
async def optimize_ui_layout(
    layout: UILayout,
    optimization_goals: Dict[str, Any],
    ui_service: UIGeneratorService = Depends(get_ui_service)
) -> UILayout:
    """
    Optimise une structure d'UI selon des objectifs
    
    - **layout**: Structure d'UI à optimiser
    - **optimization_goals**: Objectifs d'optimisation (performance, accessibility, ux)
    
    Retourne la structure optimisée
    """
    try:
        logger.info(f"Optimisation de layout: {layout.title}")
        
        # Initialisation du service si nécessaire
        if not ui_service.initialized:
            await ui_service.initialize()
        
        # Copie du layout pour modification
        optimized_layout = layout.copy(deep=True)
        
        # Optimisations basées sur les objectifs
        goals = optimization_goals.get("goals", [])
        
        if "performance" in goals:
            # Optimisation pour la performance
            optimized_layout = await ui_service._optimize_for_performance(optimized_layout)
        
        if "accessibility" in goals:
            # Optimisation pour l'accessibilité
            optimized_layout = await ui_service._optimize_for_accessibility(optimized_layout)
        
        if "ux" in goals:
            # Optimisation pour l'expérience utilisateur
            optimized_layout = await ui_service._optimize_for_ux(optimized_layout)
        
        # Post-traitement
        optimized_layout = await ui_service._post_process_layout(optimized_layout)
        
        logger.info(f"Optimisation terminée pour: {layout.title}")
        return optimized_layout
        
    except Exception as e:
        logger.error(f"Erreur lors de l'optimisation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'optimisation: {str(e)}"
        )

@router.get("/templates", response_model=List[Dict[str, Any]])
async def get_ui_templates(
    category: str = None,
    intent: str = None
) -> List[Dict[str, Any]]:
    """
    Retourne les templates d'UI disponibles
    
    - **category**: Catégorie de template (optionnel)
    - **intent**: Intention associée (optionnel)
    """
    try:
        logger.info(f"Récupération des templates - Catégorie: {category}, Intent: {intent}")
        
        # Templates de base
        templates = [
            {
                "id": "form_contact",
                "name": "Formulaire de Contact",
                "category": "form",
                "intents": ["contact", "support", "question"],
                "description": "Formulaire standard pour contacter le support",
                "components": ["input", "textarea", "button"],
                "preview_url": "/templates/form_contact.png"
            },
            {
                "id": "product_showcase",
                "name": "Vitrine Produit",
                "category": "display",
                "intents": ["information", "purchase", "browse"],
                "description": "Affichage de produits avec détails et actions",
                "components": ["card", "image", "button", "price"],
                "preview_url": "/templates/product_showcase.png"
            },
            {
                "id": "search_results",
                "name": "Résultats de Recherche",
                "category": "list",
                "intents": ["search", "browse", "filter"],
                "description": "Liste de résultats avec filtres",
                "components": ["list", "filter", "pagination"],
                "preview_url": "/templates/search_results.png"
            },
            {
                "id": "dashboard",
                "name": "Tableau de Bord",
                "category": "dashboard",
                "intents": ["overview", "analytics", "monitoring"],
                "description": "Vue d'ensemble avec métriques et graphiques",
                "components": ["chart", "metric", "table", "card"],
                "preview_url": "/templates/dashboard.png"
            },
            {
                "id": "booking_form",
                "name": "Formulaire de Réservation",
                "category": "form",
                "intents": ["booking", "reservation", "appointment"],
                "description": "Formulaire pour prendre rendez-vous ou réserver",
                "components": ["datepicker", "timepicker", "select", "button"],
                "preview_url": "/templates/booking_form.png"
            },
            {
                "id": "help_center",
                "name": "Centre d'Aide",
                "category": "help",
                "intents": ["help", "faq", "support"],
                "description": "Interface d'aide avec FAQ et recherche",
                "components": ["search", "accordion", "link", "category"],
                "preview_url": "/templates/help_center.png"
            }
        ]
        
        # Filtrage par catégorie
        if category:
            templates = [t for t in templates if t["category"] == category]
        
        # Filtrage par intention
        if intent:
            templates = [t for t in templates if intent in t["intents"]]
        
        logger.info(f"Retourné {len(templates)} templates")
        return templates
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des templates: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération: {str(e)}"
        )

@router.get("/health")
async def ui_health(
    ui_service: UIGeneratorService = Depends(get_ui_service)
) -> Dict[str, Any]:
    """
    Vérifie l'état de santé du service UI
    """
    try:
        health_status = {
            "service": "UI Generator",
            "status": "healthy" if ui_service.initialized else "initializing",
            "initialized": ui_service.initialized,
            "openai_configured": bool(settings.openai_api_key)
        }
        
        # Test rapide si initialisé
        if ui_service.initialized:
            try:
                # Test de génération simple
                from ...models.schemas import NLPResponse
                test_nlp = NLPResponse(
                    entities=[],
                    intent="test",
                    sentiment={"sentiment": "neutral", "confidence": 0.5},
                    context={},
                    confidence=0.8
                )
                test_layout = await ui_service._generate_fallback_layout("test")
                health_status["test_generation"] = "success"
                health_status["test_components_count"] = len(test_layout.components)
            except Exception as e:
                health_status["test_generation"] = "failed"
                health_status["test_error"] = str(e)
        
        return health_status
        
    except Exception as e:
        logger.error(f"Erreur lors du check de santé UI: {e}")
        return {
            "service": "UI Generator",
            "status": "error",
            "error": str(e)
        }