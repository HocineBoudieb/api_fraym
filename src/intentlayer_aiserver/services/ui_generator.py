"""Service de génération d'UI basé sur l'intention et le contexte"""

import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Union
import logging

from openai import AsyncOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ..core.config import settings
from ..models.schemas import (
    UIGenerationRequest, UIGenerationResponse, UILayout, UIComponent, 
    UIComponentType, Intent, IntentType
)
from .rag_service import RAGService

logger = logging.getLogger(__name__)

class UIGeneratorService:
    """Service de génération d'interfaces utilisateur"""
    
    def __init__(self, rag_service: RAGService = None):
        self.rag_service = rag_service
        self.openai_client = None
        self.langchain_llm = None
        self.initialized = False
    
    async def initialize(self):
        """Initialise le service de génération d'UI"""
        try:
            logger.info("Initialisation du service de génération d'UI...")
            
            # Initialisation OpenAI
            if settings.openai_api_key:
                self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
                self.langchain_llm = ChatOpenAI(
                    api_key=settings.openai_api_key,
                    model=settings.openai_model,
                    temperature=0.3,  # Plus déterministe pour l'UI
                    max_tokens=2000
                )
                logger.info("Client OpenAI initialisé pour la génération d'UI")
            else:
                logger.warning("Clé API OpenAI non configurée")
            
            self.initialized = True
            logger.info("Service de génération d'UI initialisé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du service UI: {e}")
            raise
    
    async def generate_ui_layout(self, nlp_result, rag_service=None, user_preferences=None, context=None, ui_constraints=None) -> UIGenerationResponse:
        """Génère un layout UI basé sur le résultat NLP"""
        # Créer une requête UIGenerationRequest à partir des paramètres
        request = UIGenerationRequest(
            intent=nlp_result.intent.description if hasattr(nlp_result.intent, 'description') else str(nlp_result.intent),
            context=context or {},
            user_preferences=user_preferences,
            target_device="desktop",
            theme="default"
        )
        
        # Utiliser le service RAG fourni si disponible
        if rag_service:
            self.rag_service = rag_service
            
        return await self.generate_ui(request)
    
    async def generate_ui(self, request: UIGenerationRequest) -> UIGenerationResponse:
        """Génère une interface utilisateur basée sur l'intention"""
        start_time = time.time()
        
        try:
            # Recherche des composants pertinents via RAG
            relevant_components = await self._get_relevant_components(request.intent, request.context)
            
            # Recherche des layouts pertinents via RAG
            relevant_layouts = await self._get_relevant_layouts(request.intent, request.context)
            
            # Génération du layout avec LLM - retour direct des données JSON
            if self.langchain_llm:
                layout_data = await self._generate_layout_llm_raw(request, relevant_components, relevant_layouts)
            else:
                layout_data = await self._generate_layout_fallback_raw(request, relevant_components)
            
            processing_time = time.time() - start_time
            
            # Retourner directement les données sans validation Pydantic
            return {
                "layout": layout_data,
                "reasoning": f"Interface générée basée sur l'intention '{request.intent}' avec {len(relevant_components)} composants pertinents",
                "alternatives": None,
                "processing_time": processing_time,
                "confidence_score": 0.8
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération d'UI: {e}")
            # Retour d'un layout par défaut en cas d'erreur
            return {
                "layout": await self._get_default_layout_raw(),
                "reasoning": "Layout par défaut (erreur de génération)",
                "alternatives": None,
                "processing_time": time.time() - start_time,
                "confidence_score": 0.3
            }
    
    async def _get_relevant_components(self, intent: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Récupère les composants UI pertinents via RAG"""
        try:
            # Construction de la requête de recherche
            search_query = f"intention: {intent}"
            
            # Ajout du contexte à la recherche
            if context.get('intent_type'):
                search_query += f" type: {context['intent_type']}"
            
            if context.get('entity_types'):
                search_query += f" entités: {', '.join(context['entity_types'])}"
            
            # Recherche dans la base vectorielle
            components = await self.rag_service.search_ui_components(search_query, top_k=10)
            
            logger.debug(f"Trouvé {len(components)} composants pertinents pour: {search_query}")
            return components
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de composants: {e}")
            return []
    
    async def _get_relevant_layouts(self, intent: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Récupère les layouts UI pertinents via RAG"""
        try:
            # Construction de la requête de recherche
            search_query = f"intention: {intent}"
            
            # Ajout du contexte à la recherche
            if context.get('intent_type'):
                search_query += f" type: {context['intent_type']}"
            
            if context.get('entity_types'):
                search_query += f" entités: {', '.join(context['entity_types'])}"
            
            # Recherche des layouts dans la base vectorielle
            layouts = await self.rag_service.search_ui_layouts(search_query, top_k=5)
            
            logger.debug(f"Trouvé {len(layouts)} layouts pertinents pour: {search_query}")
            return layouts
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de layouts: {e}")
            return []
    
    async def _generate_layout_llm(self, request: UIGenerationRequest, 
                                 relevant_components: List[Dict[str, Any]],
                                 relevant_layouts: List[Dict[str, Any]] = None) -> UILayout:
        """Génère un layout avec LLM"""
        try:
            # Préparation du contexte pour le LLM
            components_context = self._format_components_for_llm(relevant_components)
            layouts_context = self._format_layouts_for_llm(relevant_layouts or [])
            
            # Obtenir les types de composants valides
            from ..models.schemas import UIComponentType
            valid_types = [t.value for t in UIComponentType]
            
            system_prompt = f"""
            Tu es un expert en design d'interfaces utilisateur React avec ShadCN UI, MUI et Aceternity UI.
            
            Génère une interface utilisateur JSON basée sur:
            - L'intention utilisateur: {request.intent}
            - Le contexte: {json.dumps(request.context, ensure_ascii=False)}
            - L'appareil cible: {request.target_device}
            - Le thème: {request.theme}
            
            COMPOSANTS REACT DISPONIBLES:
            - ShadCN UI: Button, Card, Input, Form, Dialog, Sheet, Tabs, Badge, Avatar, Alert, etc.
            - MUI: Button, Card, TextField, Dialog, Drawer, Tabs, Chip, Avatar, Grid, Typography, etc.
            - Aceternity UI: FloatingNav, HeroParallax, InfiniteMovingCards, TextGenerateEffect, etc.
            - HTML natifs: div, span, h1, h2, h3, p, img, section, header, footer, etc.
            - Autres: Tout composant React valide
            
            Composants disponibles dans la base:
            {components_context}
            
            Layouts de positionnement disponibles:
            {layouts_context}
            
            Règles de génération:
            1. Utilise des noms de composants React réels (Button, Card, TextField, Typography, etc.)
            2. Structure hiérarchique avec children pour les composants conteneurs
            3. Props compatibles avec les bibliothèques React modernes
            4. Responsive design avec Tailwind CSS
            5. Accessibilité (aria-label, role, etc.)
            6. Optimisé pour le rendu côté client Next.js
            7. IMPORTANT: Ajoute une propriété "position" à chaque composant avec x, y, width, height
            8. Utilise les layouts suggérés pour positionner harmonieusement les composants
            9. Les positions sont en pourcentage (0-100) par rapport au conteneur parent
            10. Pour le texte simple, utilise des composants comme Typography, p, h1, h2, etc.
            11. children peut être un tableau de composants OU une chaîne de texte simple
            
            Format de réponse JSON OBLIGATOIRE:
            {{
                "components": [
                    {{
                        "type": "Button",
                        "props": {{
                            "variant": "primary",
                            "size": "md",
                            "onClick": "handleClick",
                            "className": "mb-4"
                        }},
                        "position": {{
                            "x": 25,
                            "y": 10,
                            "width": 50,
                            "height": 10
                        }},
                        "children": "Texte du bouton"
                    }},
                    {{
                        "type": "Card",
                        "props": {{
                            "className": "p-6 shadow-lg"
                        }},
                        "position": {{
                            "x": 0,
                            "y": 25,
                            "width": 100,
                            "height": 60
                        }},
                        "children": [
                            {{
                                "type": "h2",
                                "props": {{
                                    "className": "text-xl font-bold mb-2"
                                }},
                                "children": "Titre de la carte"
                            }},
                            {{
                                "type": "p",
                                "props": {{
                                    "className": "text-gray-600"
                                }},
                                "children": "Description de la carte"
                            }}
                        ]
                    }}
                ]
            }}
            """
            
            user_prompt = f"""
            Génère une interface pour l'intention: "{request.intent}"
            
            Contexte additionnel:
            {json.dumps(request.context, ensure_ascii=False, indent=2)}
            
            Préférences utilisateur:
            {json.dumps(request.user_preferences or {}, ensure_ascii=False, indent=2)}
            """
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = await self.langchain_llm.ainvoke(messages)
            
            # Parsing de la réponse JSON
            try:
                layout_data = json.loads(response.content)
                return self._parse_layout_from_json(layout_data)
            except json.JSONDecodeError:
                logger.warning("Réponse LLM non parsable, utilisation du fallback")
                return await self._generate_layout_fallback(request, relevant_components)
        
        except Exception as e:
            logger.error(f"Erreur lors de la génération de layout LLM: {e}")
            return await self._generate_layout_fallback(request, relevant_components)
    
    def _build_layout_prompt(self, request: UIGenerationRequest, 
                            relevant_components: List[Dict[str, Any]],
                            relevant_layouts: Optional[List[Dict[str, Any]]] = None) -> str:
        """Construit le prompt système pour la génération de layout"""
        # Préparation du contexte pour le LLM
        components_context = self._format_components_for_llm(relevant_components)
        layouts_context = self._format_layouts_for_llm(relevant_layouts or [])
        
        # Obtenir les types de composants valides
        from ..models.schemas import UIComponentType
        valid_types = [t.value for t in UIComponentType]
        
        system_prompt = f"""
        Tu es un architecte UX/UI expert spécialisé dans la création d'interfaces sophistiquées et immersives.
        
        ANALYSE CONTEXTUELLE APPROFONDIE:
        - Intention utilisateur: {request.intent}
        - Contexte métier: {json.dumps(request.context, ensure_ascii=False)}
        - Appareil cible: {request.target_device}
        - Thème: {request.theme}
        
        COMPOSANTS AVANCÉS DISPONIBLES:
        {components_context}
        
        LAYOUTS ARCHITECTURAUX:
        {layouts_context}
        
        DIRECTIVES DE CONCEPTION AVANCÉE:
        
        1. ÉVITER LES BOUTONS SIMPLES - Privilégier:
           - Cartes interactives avec hover effects
           - Zones cliquables intégrées dans le design
           - Navigation par onglets ou accordéons
           - Formulaires intégrés et contextuels
        
        2. CRÉER DES INTERFACES RICHES:
           - Utiliser des grilles complexes (Grid, Flexbox)
           - Intégrer des composants de données (Tables, Charts, Lists)
           - Ajouter des éléments visuels (Images, Icons, Badges)
           - Créer des hiérarchies d'information claires
        
        3. RAISONNEMENT CONTEXTUEL:
           - Analyser l'intention pour déterminer le type d'interface optimal
           - Utiliser les entités du contexte pour personnaliser le contenu
           - Adapter la complexité selon le domaine métier
           - Intégrer des données pertinentes du RAG
        
        4. COMPOSANTS SOPHISTIQUÉS À PRIVILÉGIER:
           - DataTable avec filtres et tri
           - Timeline pour les processus
           - Dashboard avec métriques
           - Formulaires multi-étapes
           - Galeries et carousels
           - Accordéons et onglets
           - Modales et drawers contextuels
        
        5. ARCHITECTURE RESPONSIVE:
           - Layouts adaptatifs selon l'appareil
           - Grilles flexibles et modulaires
           - Composants imbriqués intelligemment
           - Espacement et proportions harmonieux
        
        IMPORTANT - FORMAT DE RÉPONSE OBLIGATOIRE:
        Tu DOIS répondre UNIQUEMENT avec un objet JSON valide, sans aucun texte avant ou après.
        Pas de markdown, pas d'explication, SEULEMENT le JSON.
        
        Structure JSON EXACTE requise:
        {{
            "components": [
                {{
                    "type": "nom_du_composant",
                    "props": {{}},
                    "position": {{"x": 0, "y": 0, "width": 100, "height": 50}},
                    "children": []
                }}
            ]
        }}
        
        EXEMPLE COMPLET pour un e-commerce:
        {{
            "components": [
                {{
                    "type": "Grid",
                    "props": {{"container": true, "spacing": 3, "className": "min-h-screen p-6"}},
                    "position": {{"x": 0, "y": 0, "width": 100, "height": 100}},
                    "children": [
                        {{
                            "type": "Grid",
                            "props": {{"item": true, "xs": 12, "md": 3}},
                            "children": [
                                {{
                                    "type": "Card",
                                    "props": {{"className": "p-4 h-full"}},
                                    "children": [
                                        {{"type": "h3", "children": "Filtres", "props": {{"className": "mb-4 font-bold"}}}},
                                        {{"type": "Accordion", "props": {{"defaultExpanded": true}}, "children": "Catégories, Prix, Marques..."}}
                                    ]
                                }}
                            ]
                        }},
                        {{
                            "type": "Grid",
                            "props": {{"item": true, "xs": 12, "md": 9}},
                            "children": [
                                {{"type": "Typography", "props": {{"variant": "h4", "className": "mb-6"}}, "children": "Nos Produits"}},
                                {{
                                    "type": "Grid",
                                    "props": {{"container": true, "spacing": 2}},
                                    "children": "[Grille de cartes produits avec images, prix, descriptions]"
                                }}
                            ]
                        }}
                    ]
                }}
            ]
        }}
        
        GÉNÈRE UNE INTERFACE SOPHISTIQUÉE ET CONTEXTUELLE - RÉPONSE JSON UNIQUEMENT!
        """
        
        return system_prompt
    
    async def _generate_layout_llm_raw(self, request: UIGenerationRequest, 
                                     relevant_components: List[Dict[str, Any]],
                                     relevant_layouts: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Génère un layout avec LLM et retourne directement les données JSON"""
        try:
            # Utiliser la même logique que _generate_layout_llm mais retourner JSON
            prompt = self._build_layout_prompt(request, relevant_components, relevant_layouts)
            
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=f"Génère une interface pour: {request.intent}")
            ]
            
            response = await self.langchain_llm.ainvoke(messages)
            
            # Parsing de la réponse JSON
            try:
                # Nettoyer la réponse (enlever les markdown blocks si présents)
                content = response.content.strip()
                if content.startswith('```json'):
                    content = content[7:]
                if content.startswith('```'):
                    content = content[3:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()
                
                layout_data = json.loads(content)
                return layout_data  # Retourner directement les données JSON
            except json.JSONDecodeError as e:
                logger.warning(f"Réponse LLM non parsable: {e}")
                logger.warning(f"Contenu reçu: {response.content[:500]}...")
                return await self._generate_layout_fallback_raw(request, relevant_components)
        
        except Exception as e:
            logger.error(f"Erreur lors de la génération de layout LLM: {e}")
            return await self._generate_layout_fallback_raw(request, relevant_components)
    
    async def _generate_layout_fallback_raw(self, request: UIGenerationRequest, 
                                          relevant_components: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Génère un layout de fallback et retourne directement les données JSON"""
        # Layout simple par défaut
        return {
            "components": [
                {
                    "type": "div",
                    "props": {"className": "container"},
                    "children": [
                        {
                            "type": "h1",
                            "props": {},
                            "children": "Bienvenue!"
                        },
                        {
                            "type": "p",
                            "props": {},
                            "children": "Interface générée automatiquement."
                        }
                    ]
                }
            ],
            "layout_type": "react",
            "metadata": {},
            "responsive": True,
            "theme": "default"
        }
    
    async def _get_default_layout_raw(self) -> Dict[str, Any]:
        """Retourne un layout par défaut en format JSON"""
        return {
            "components": [
                {
                    "type": "div",
                    "props": {"className": "error-container"},
                    "children": [
                        {
                            "type": "h2",
                            "props": {},
                            "children": "Erreur de génération"
                        },
                        {
                            "type": "p",
                            "props": {},
                            "children": "Une erreur s'est produite lors de la génération de l'interface."
                        },
                        {
                            "type": "button",
                            "props": {"children": "Réessayer"},
                            "children": None
                        }
                    ]
                }
            ],
            "layout_type": "react",
            "metadata": {},
            "responsive": True,
            "theme": "default"
        }
    
    def _format_components_for_llm(self, components: List[Dict[str, Any]]) -> str:
        """Formate les composants pour le prompt LLM"""
        if not components:
            return "Aucun composant spécifique trouvé, utilise les composants standards."
        
        formatted = []
        for comp in components[:5]:  # Limite pour éviter un prompt trop long
            formatted.append(f"""
            - {comp.get('name', 'Composant')}: {comp.get('description', '')}
              Type: {comp.get('type', '')}
              Props: {json.dumps(comp.get('props', {}), ensure_ascii=False)}
              Usage: {comp.get('usage', '')}
            """)
        
        return "\n".join(formatted)
    
    def _format_layouts_for_llm(self, layouts: List[Dict[str, Any]]) -> str:
        """Formate les layouts pour le prompt LLM"""
        if not layouts:
            return "Aucun layout spécifique trouvé, utilise un positionnement libre."
        
        formatted = []
        for layout in layouts[:3]:  # Limite pour éviter un prompt trop long
            areas_info = []
            # Gérer les deux formats: 'component_areas' (nouveau) et 'components' (existant)
            areas = layout.get('component_areas', layout.get('components', []))
            
            for area in areas:
                # Extraire les positions selon le format
                if 'position' in area:
                    # Format existant avec sous-objet position
                    pos = area['position']
                    x, y, w, h = pos.get('x', 0), pos.get('y', 0), pos.get('width', 100), pos.get('height', 100)
                else:
                    # Format direct
                    x, y, w, h = area.get('x', 0), area.get('y', 0), area.get('width', 100), area.get('height', 100)
                
                name = area.get('name', area.get('id', 'Zone'))
                areas_info.append(
                    f"    - {name}: x={x}%, y={y}%, w={w}%, h={h}%"
                )
            
            formatted.append(f"""
            - {layout.get('name', 'Layout')}: {layout.get('description', '')}
              Type: {layout.get('type', '')}
              Catégorie: {layout.get('category', '')}
              Zones de composants:
{chr(10).join(areas_info)}
            """)
        
        return "\n".join(formatted)
    
    def _parse_layout_from_json(self, layout_data: Dict[str, Any]) -> UILayout:
        """Parse les données JSON en objet UILayout pour composants React"""
        try:
            # Log de la réponse de l'IA pour debugging
            logger.info(f"Réponse de l'IA à parser: {json.dumps(layout_data, ensure_ascii=False, indent=2)}")
            
            # Conversion des composants React
            components = []
            for i, comp_data in enumerate(layout_data.get('components', [])):
                try:
                    comp_type = comp_data.get('type', 'div')
                    
                    # Pas de validation stricte - accepter tous les types de composants React
                    component = UIComponent(
                        type=comp_type,  # Utiliser directement le type sans validation enum
                        props=comp_data.get('props', {}),
                        children=self._parse_children_react(comp_data.get('children')),
                        style=comp_data.get('style'),
                        events=comp_data.get('events'),
                        id=comp_data.get('id'),
                        className=comp_data.get('className')
                    )
                    components.append(component)
                    
                except Exception as comp_error:
                    logger.error(f"Erreur lors du parsing du composant {i}: {comp_error}")
                    # Ajouter un composant par défaut en cas d'erreur
                    components.append(UIComponent(
                        type="div",
                        props={"children": "Erreur de composant"},
                        children=None,
                        style=None,
                        events=None,
                        id=f"error_component_{i}",
                        className="error"
                    ))
            
            return UILayout(
                components=components,
                layout_type=layout_data.get('layout_type', 'react'),
                metadata=layout_data.get('metadata', {}),
                responsive=layout_data.get('responsive', True),
                theme=layout_data.get('theme', 'default')
            )
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing du layout: {e}")
            logger.error(f"Données reçues: {json.dumps(layout_data, ensure_ascii=False, indent=2)}")
            raise
    
    def _parse_children_react(self, children_data: Optional[any]) -> Optional[any]:
        """Parse récursivement les children des composants React"""
        if children_data is None:
            return None
        
        # Si c'est une string, la retourner directement
        if isinstance(children_data, str):
            return children_data
        
        # Si c'est une liste, parser chaque élément
        if isinstance(children_data, list):
            children = []
            for child_data in children_data:
                if isinstance(child_data, dict):
                    try:
                        comp_type = child_data.get('type', 'span')
                        
                        # Pas de validation stricte pour les composants React
                        child_component = UIComponent(
                            type=comp_type,
                            props=child_data.get('props', {}),
                            children=self._parse_children_react(child_data.get('children')),
                            style=child_data.get('style'),
                            events=child_data.get('events'),
                            id=child_data.get('id'),
                            className=child_data.get('className')
                        )
                        children.append(child_component)
                        
                    except Exception as e:
                        logger.error(f"Erreur lors du parsing d'un composant enfant: {e}")
                        # Ajouter un composant texte par défaut
                        children.append(UIComponent(
                            type="span",
                            props={"children": "Erreur"},
                            children=None
                        ))
                elif isinstance(child_data, str):
                    # Texte simple - l'ajouter directement
                    children.append(child_data)
            
            return children if children else None
        
        # Si c'est un dict, le traiter comme un composant unique
        if isinstance(children_data, dict):
            try:
                comp_type = children_data.get('type', 'span')
                return UIComponent(
                    type=comp_type,
                    props=children_data.get('props', {}),
                    children=self._parse_children_react(children_data.get('children')),
                    style=children_data.get('style'),
                    events=children_data.get('events'),
                    id=children_data.get('id'),
                    className=children_data.get('className')
                )
            except Exception as e:
                logger.error(f"Erreur lors du parsing d'un composant enfant unique: {e}")
                return "Erreur"
        
        # Pour tout autre type, le retourner tel quel
        return children_data
    
    def _parse_children(self, children_data: Optional[List]) -> Optional[List[Union[UIComponent, str]]]:
        """Parse récursivement les composants enfants"""
        if not children_data:
            return None
        
        children = []
        for child_data in children_data:
            if isinstance(child_data, dict):
                child = UIComponent(
                    type=child_data.get('type', 'button'),
                    props=child_data.get('props', {}),
                    children=self._parse_children(child_data.get('children')),
                    style=child_data.get('style'),
                    events=child_data.get('events'),
                    id=child_data.get('id'),
                    className=child_data.get('className')
                )
                children.append(child)
            elif isinstance(child_data, str):
                # Ajouter directement les chaînes de caractères
                children.append(child_data)
        
        return children if children else None
    
    async def _generate_layout_fallback(self, request: UIGenerationRequest, 
                                      relevant_components: List[Dict[str, Any]],
                                      relevant_layouts: Optional[List[Dict[str, Any]]] = None) -> UILayout:
        """Génère un layout de fallback basé sur des règles"""
        # Mapping intention -> composants
        intent_to_components = {
            "question": ["card", "form"],
            "search": ["input", "button", "list"],
            "purchase": ["card", "button", "form"],
            "navigation": ["navigation", "button"],
            "support": ["form", "card"],
            "command": ["button", "modal"]
        }
        
        # Détermination des composants à utiliser
        intent_key = request.context.get('intent_type', 'other')
        component_types = intent_to_components.get(intent_key, ["card", "button"])
        
        # Génération des composants avec positionnement
        components = []
        
        # Déterminer le layout à utiliser
        selected_layout = None
        if relevant_layouts:
            # Utiliser le premier layout pertinent
            selected_layout = relevant_layouts[0]
        
        # Positions par défaut si aucun layout spécifique
        default_positions = {
            "header": {"x": 0, "y": 0, "width": 100, "height": 15},
            "content": {"x": 0, "y": 20, "width": 100, "height": 70},
            "footer": {"x": 0, "y": 95, "width": 100, "height": 5}
        }
        
        # Titre principal
        header_pos = default_positions["header"]
        if selected_layout:
            # Gérer les deux formats de layout
            areas = selected_layout.get('component_areas', selected_layout.get('components', []))
            # Chercher une zone header dans le layout
            for area in areas:
                area_name = area.get('name', area.get('id', '')).lower()
                if 'header' in area_name or 'hero' in area_name:
                    # Extraire la position selon le format
                    if 'position' in area:
                        pos = area['position']
                        header_pos = {
                            "x": pos.get('x', 0),
                            "y": pos.get('y', 0),
                            "width": pos.get('width', 100),
                            "height": pos.get('height', 15)
                        }
                    else:
                        header_pos = {
                            "x": area.get('x', 0),
                            "y": area.get('y', 0),
                            "width": area.get('width', 100),
                            "height": area.get('height', 15)
                        }
                    break
        
        components.append(UIComponent(
                type="card",
            props={
                "title": self._generate_title(request.intent),
                "description": f"Interface générée pour: {request.intent}"
            },
            id="main-header",
            className="mb-6",
            position=header_pos
        ))
        
        # Composants spécifiques à l'intention avec positionnement
        content_pos = default_positions["content"]
        if selected_layout:
            # Gérer les deux formats de layout
            areas = selected_layout.get('component_areas', selected_layout.get('components', []))
            # Chercher une zone content dans le layout
            for area in areas:
                area_name = area.get('name', area.get('id', '')).lower()
                if 'content' in area_name or 'main' in area_name:
                    # Extraire la position selon le format
                    if 'position' in area:
                        pos = area['position']
                        content_pos = {
                            "x": pos.get('x', 0),
                            "y": pos.get('y', 20),
                            "width": pos.get('width', 100),
                            "height": pos.get('height', 70)
                        }
                    else:
                        content_pos = {
                            "x": area.get('x', 0),
                            "y": area.get('y', 20),
                            "width": area.get('width', 100),
                            "height": area.get('height', 70)
                        }
                    break
        
        component_y_offset = content_pos["y"]
        
        if "input" in component_types:
            components.append(UIComponent(
                type="input",
                props={
                    "placeholder": "Saisissez votre recherche...",
                    "type": "text"
                },
                id="search-input",
                className="mb-4",
                position={
                    "x": content_pos["x"] + 10,
                    "y": component_y_offset,
                    "width": content_pos["width"] - 20,
                    "height": 8
                }
            ))
            component_y_offset += 12
        
        if "button" in component_types:
            components.append(UIComponent(
                type="button",
                props={
                    "variant": "primary",
                    "children": self._generate_button_text(intent_key)
                },
                id="action-button",
                events={"onClick": "handleAction"},
                position={
                    "x": content_pos["x"] + 10,
                    "y": component_y_offset,
                    "width": 30,
                    "height": 8
                }
            ))
            component_y_offset += 12
        
        if "form" in component_types:
            components.append(UIComponent(
                type="form",
                props={
                    "fields": self._generate_form_fields(request.context)
                },
                id="main-form",
                className="mt-4",
                position={
                    "x": content_pos["x"] + 10,
                    "y": component_y_offset,
                    "width": content_pos["width"] - 20,
                    "height": 25
                }
            ))
        
        return UILayout(
            components=components,
            layout_type="fallback",
            metadata={
                "title": self._generate_title(request.intent),
                "description": f"Interface pour {request.intent}",
                "generated_by": "fallback"
            },
            responsive=True,
            theme=request.theme or "default"
        )
    
    def _generate_title(self, intent: str) -> str:
        """Génère un titre basé sur l'intention"""
        title_map = {
            "question": "Aide et Support",
            "search": "Recherche",
            "purchase": "Commande",
            "navigation": "Navigation",
            "support": "Support Client",
            "command": "Action"
        }
        
        return title_map.get(intent.lower(), "Interface Utilisateur")
    
    def _generate_button_text(self, intent_type: str) -> str:
        """Génère le texte du bouton basé sur l'intention"""
        button_map = {
            "question": "Obtenir de l'aide",
            "search": "Rechercher",
            "purchase": "Ajouter au panier",
            "navigation": "Aller à",
            "support": "Contacter le support",
            "command": "Exécuter"
        }
        
        return button_map.get(intent_type, "Valider")
    
    def _generate_form_fields(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Génère les champs de formulaire basés sur le contexte"""
        fields = []
        
        # Champs basés sur les entités détectées
        entity_types = context.get('entity_types', [])
        
        if 'EMAIL' in entity_types or 'contact' in context.get('analyzed_text', '').lower():
            fields.append({
                "name": "email",
                "type": "email",
                "label": "Email",
                "required": True
            })
        
        if 'PHONE' in entity_types:
            fields.append({
                "name": "phone",
                "type": "tel",
                "label": "Téléphone",
                "required": False
            })
        
        # Champ message par défaut
        fields.append({
            "name": "message",
            "type": "textarea",
            "label": "Message",
            "required": True,
            "placeholder": "Décrivez votre demande..."
        })
        
        return fields
    
    async def _generate_alternatives(self, request: UIGenerationRequest, 
                                   relevant_components: List[Dict[str, Any]]) -> Optional[List[UILayout]]:
        """Génère des alternatives de layout"""
        # Pour l'instant, retourne None (peut être implémenté plus tard)
        return None
    
    def _calculate_ui_confidence(self, layout: UILayout, 
                               relevant_components: List[Dict[str, Any]]) -> float:
        """Calcule un score de confiance pour l'UI générée"""
        base_score = 0.7
        
        # Bonus si des composants pertinents ont été trouvés
        if relevant_components:
            base_score += 0.2
        
        # Bonus si le layout a plusieurs composants
        if len(layout.components) > 1:
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    async def _get_default_layout(self) -> UILayout:
        """Retourne un layout par défaut en cas d'erreur"""
        return UILayout(
            components=[
                UIComponent(
                    type="card",
                    props={
                        "title": "Interface par défaut",
                        "description": "Une erreur s'est produite lors de la génération de l'interface."
                    },
                    id="error-card"
                ),
                UIComponent(
                    type="button",
                    props={
                        "variant": "primary",
                        "children": "Réessayer"
                    },
                    id="retry-button",
                    events={"onClick": "retry"}
                )
            ],
            layout_type="error",
            metadata={"title": "Erreur", "description": "Layout par défaut"},
            responsive=True,
            theme="default"
        )
    
    async def _post_process_layout(self, layout: UILayout, 
                                 request: UIGenerationRequest) -> UILayout:
        """Post-traite le layout généré"""
        # Validation et nettoyage
        for component in layout.components:
            # Ajout d'IDs uniques si manquants
            if not component.id:
                component.id = f"comp_{hash(str(component.props))}"[:8]
            
            # Ajout de classes responsive si device mobile
            if request.target_device == "mobile":
                if component.className:
                    component.className += " mobile-responsive"
                else:
                    component.className = "mobile-responsive"
        
        return layout
    
    async def cleanup(self):
        """Nettoyage des ressources"""
        try:
            if self.openai_client:
                await self.openai_client.close()
            
            self.initialized = False
            logger.info("Service de génération d'UI nettoyé")
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du service UI: {e}")