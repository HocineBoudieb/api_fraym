"""Schémas Pydantic pour la validation des données"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from datetime import datetime

class InputType(str, Enum):
    """Types d'entrée supportés"""
    TEXT = "text"
    VOICE = "voice"
    MULTIMODAL = "multimodal"

class IntentType(str, Enum):
    """Types d'intentions détectées"""
    QUESTION = "question"
    COMMAND = "command"
    NAVIGATION = "navigation"
    SEARCH = "search"
    FORM_FILL = "form_fill"
    PURCHASE = "purchase"
    SUPPORT = "support"
    OTHER = "other"

class UIComponentType(str, Enum):
    """Types de composants UI"""
    BUTTON = "button"
    INPUT = "input"
    CARD = "card"
    MODAL = "modal"
    FORM = "form"
    LIST = "list"
    GRID = "grid"
    NAVIGATION = "navigation"
    HERO = "hero"
    FOOTER = "footer"
    DIV = "div"
    SPAN = "span"
    TEXT = "text"
    IMAGE = "image"
    LINK = "link"
    CONTAINER = "container"
    SECTION = "section"
    HEADER = "header"

# Modèles d'entrée
class NLPRequest(BaseModel):
    """Requête d'analyse NLP"""
    text: str = Field(..., description="Texte à analyser")
    input_type: InputType = Field(default=InputType.TEXT, description="Type d'entrée")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Contexte additionnel")
    user_id: Optional[str] = Field(default=None, description="ID utilisateur pour la mémoire")
    session_id: Optional[str] = Field(default=None, description="ID de session")

class UIGenerationRequest(BaseModel):
    """Requête de génération d'UI"""
    intent: str = Field(..., description="Intention détectée")
    context: Dict[str, Any] = Field(..., description="Contexte de l'intention")
    user_preferences: Optional[Dict[str, Any]] = Field(default=None, description="Préférences utilisateur")
    target_device: Optional[str] = Field(default="desktop", description="Appareil cible")
    theme: Optional[str] = Field(default="default", description="Thème UI")

class MemoryRequest(BaseModel):
    """Requête de gestion mémoire"""
    user_id: str = Field(..., description="ID utilisateur")
    session_id: Optional[str] = Field(default=None, description="ID de session")
    interaction: Dict[str, Any] = Field(..., description="Données d'interaction")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Contexte")

class SessionRequest(BaseModel):
    """Requête de gestion de session"""
    user_id: str = Field(..., description="ID utilisateur")
    user_data: Optional[Dict[str, Any]] = Field(default=None, description="Données utilisateur")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Contexte initial")

class ChatRequest(BaseModel):
    """Requête de chat avec session"""
    session_id: str = Field(..., description="ID de session")
    message: str = Field(..., description="Message utilisateur")
    input_type: InputType = Field(default=InputType.TEXT, description="Type d'entrée")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Contexte additionnel")

# Modèles de sortie
class Entity(BaseModel):
    """Entité extraite du texte"""
    text: str = Field(..., description="Texte de l'entité")
    label: str = Field(..., description="Type d'entité")
    confidence: float = Field(..., description="Score de confiance")
    start: int = Field(..., description="Position de début")
    end: int = Field(..., description="Position de fin")

class Intent(BaseModel):
    """Intention détectée"""
    type: IntentType = Field(..., description="Type d'intention")
    confidence: float = Field(..., description="Score de confiance")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Paramètres extraits")
    description: str = Field(..., description="Description de l'intention")

class NLPResponse(BaseModel):
    """Réponse d'analyse NLP"""
    intent: Intent = Field(..., description="Intention détectée")
    entities: List[Entity] = Field(default_factory=list, description="Entités extraites")
    sentiment: Optional[Dict[str, float]] = Field(default=None, description="Analyse de sentiment")
    context: Dict[str, Any] = Field(default_factory=dict, description="Contexte enrichi")
    processing_time: float = Field(..., description="Temps de traitement en secondes")
    confidence_score: float = Field(..., description="Score de confiance global")

class UIComponent(BaseModel):
    """Composant UI généré"""
    type: str = Field(..., description="Type de composant (ex: Button, Card, TextField, Dialog, etc.)")
    props: Dict[str, Any] = Field(default_factory=dict, description="Propriétés du composant")
    children: Optional[List[Union['UIComponent', str]]] = Field(default=None, description="Composants enfants ou texte simple")
    style: Optional[Dict[str, Any]] = Field(default=None, description="Styles CSS")
    events: Optional[Dict[str, str]] = Field(default=None, description="Gestionnaires d'événements")
    id: Optional[str] = Field(default=None, description="ID unique du composant")
    className: Optional[str] = Field(default=None, description="Classes CSS")

class UILayout(BaseModel):
    """Layout UI complet"""
    components: List[UIComponent] = Field(..., description="Liste des composants")
    layout_type: str = Field(..., description="Type de layout")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées du layout")
    responsive: bool = Field(default=True, description="Layout responsive")
    theme: str = Field(default="default", description="Thème appliqué")

class UIGenerationResponse(BaseModel):
    """Réponse de génération d'UI"""
    layout: UILayout = Field(..., description="Layout généré")
    reasoning: str = Field(..., description="Explication du choix de design")
    alternatives: Optional[List[UILayout]] = Field(default=None, description="Alternatives proposées")
    processing_time: float = Field(..., description="Temps de génération")
    confidence_score: float = Field(..., description="Score de confiance")

class MemoryEntry(BaseModel):
    """Entrée de mémoire"""
    id: str = Field(..., description="ID unique")
    user_id: str = Field(..., description="ID utilisateur")
    session_id: Optional[str] = Field(default=None, description="ID de session")
    timestamp: datetime = Field(..., description="Horodatage")
    interaction_type: str = Field(..., description="Type d'interaction")
    data: Dict[str, Any] = Field(..., description="Données de l'interaction")
    context: Dict[str, Any] = Field(default_factory=dict, description="Contexte")
    relevance_score: float = Field(default=1.0, description="Score de pertinence")

class MemoryResponse(BaseModel):
    """Réponse de gestion mémoire"""
    success: bool = Field(..., description="Succès de l'opération")
    message: str = Field(..., description="Message de retour")
    memory_entries: Optional[List[MemoryEntry]] = Field(default=None, description="Entrées de mémoire")
    context_summary: Optional[Dict[str, Any]] = Field(default=None, description="Résumé du contexte")
    processing_time: Optional[float] = Field(default=None, description="Temps de traitement")

class SessionInfo(BaseModel):
    """Informations de session"""
    session_id: str = Field(..., description="ID de session")
    user_id: str = Field(..., description="ID utilisateur")
    created_at: datetime = Field(..., description="Date de création")
    last_activity: datetime = Field(..., description="Dernière activité")
    status: str = Field(..., description="Statut de la session")
    interaction_count: int = Field(default=0, description="Nombre d'interactions")

class SessionResponse(BaseModel):
    """Réponse de gestion de session"""
    success: bool = Field(..., description="Succès de l'opération")
    message: str = Field(..., description="Message de retour")
    session_info: Optional[SessionInfo] = Field(default=None, description="Informations de session")

class ChatResponse(BaseModel):
    """Réponse de chat avec session"""
    success: bool = Field(..., description="Succès de l'opération")
    message: str = Field(..., description="Message de retour")
    response_text: Optional[str] = Field(default=None, description="Réponse textuelle")
    response_audio: Optional[str] = Field(default=None, description="URL de la réponse vocale")
    ui_components: Optional[List[Dict[str, Any]]] = Field(default=None, description="Composants UI sélectionnés")
    nlp_analysis: Optional[NLPResponse] = Field(default=None, description="Analyse NLP")
    session_info: Optional[SessionInfo] = Field(default=None, description="Informations de session mises à jour")
    processing_time: Optional[float] = Field(default=None, description="Temps de traitement")

class ErrorResponse(BaseModel):
    """Réponse d'erreur standardisée"""
    error: str = Field(..., description="Type d'erreur")
    message: str = Field(..., description="Message d'erreur")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Détails additionnels")
    timestamp: datetime = Field(default_factory=datetime.now, description="Horodatage de l'erreur")

# Mise à jour des références forward
UIComponent.model_rebuild()