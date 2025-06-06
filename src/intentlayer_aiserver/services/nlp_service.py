"""Service NLP pour l'analyse des requêtes en langage naturel"""

import asyncio
import time
import re
from typing import Dict, List, Any, Optional, Tuple
import logging

try:
    import spacy
except ImportError:
    spacy = None

from openai import AsyncOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ..core.config import settings
from ..models.schemas import (
    NLPRequest, NLPResponse, Intent, Entity, IntentType
)

logger = logging.getLogger(__name__)

class NLPService:
    """Service d'analyse NLP"""
    
    def __init__(self):
        self.openai_client = None
        self.langchain_llm = None
        self.spacy_nlp = None
        self.initialized = False
    
    async def initialize(self):
        """Initialise le service NLP"""
        try:
            logger.info("Initialisation du service NLP...")
            
            # Initialisation OpenAI
            if settings.openai_api_key:
                self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
                self.langchain_llm = ChatOpenAI(
                    api_key=settings.openai_api_key,
                    model=settings.openai_model,
                    temperature=settings.openai_temperature,
                    max_tokens=settings.openai_max_tokens
                )
                logger.info("Client OpenAI initialisé")
            else:
                logger.warning("Clé API OpenAI non configurée")
            
            # Initialisation spaCy
            await self._initialize_spacy()
            
            self.initialized = True
            logger.info("Service NLP initialisé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du service NLP: {e}")
            raise
    
    async def _initialize_spacy(self):
        """Initialise spaCy"""
        if not spacy:
            logger.warning("spaCy non disponible")
            return
        
        try:
            # Tentative de chargement du modèle français
            try:
                self.spacy_nlp = spacy.load(settings.spacy_model)
                logger.info(f"Modèle spaCy chargé: {settings.spacy_model}")
            except OSError:
                # Fallback vers le modèle anglais
                try:
                    self.spacy_nlp = spacy.load("en_core_web_sm")
                    logger.info("Modèle spaCy anglais chargé en fallback")
                except OSError:
                    logger.warning("Aucun modèle spaCy disponible")
                    self.spacy_nlp = None
        
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de spaCy: {e}")
            self.spacy_nlp = None
    
    async def analyze_request(self, request: NLPRequest) -> NLPResponse:
        """Analyse une requête NLP complète"""
        start_time = time.time()
        
        try:
            # Extraction des entités avec spaCy
            entities = await self._extract_entities_spacy(request.text)
            
            # Détection d'intention avec LLM
            intent = await self._detect_intent_llm(request.text, request.context)
            
            # Analyse de sentiment (optionnel)
            sentiment = await self._analyze_sentiment(request.text)
            
            # Enrichissement du contexte
            enriched_context = await self._enrich_context(
                request.text, intent, entities, request.context
            )
            
            # Calcul du score de confiance global
            confidence_score = self._calculate_confidence(intent, entities)
            
            processing_time = time.time() - start_time
            
            return NLPResponse(
                intent=intent,
                entities=entities,
                sentiment=sentiment,
                context=enriched_context,
                processing_time=processing_time,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse NLP: {e}")
            # Retour d'une réponse par défaut en cas d'erreur
            return NLPResponse(
                intent=Intent(
                    type=IntentType.OTHER,
                    confidence=0.1,
                    parameters={},
                    description="Intention non déterminée (erreur)"
                ),
                entities=[],
                sentiment=None,
                context=request.context or {},
                processing_time=time.time() - start_time,
                confidence_score=0.1
            )
    
    async def _extract_entities_spacy(self, text: str) -> List[Entity]:
        """Extrait les entités avec spaCy"""
        entities = []
        
        if not self.spacy_nlp:
            # Extraction basique par regex en fallback
            return await self._extract_entities_regex(text)
        
        try:
            doc = self.spacy_nlp(text)
            
            for ent in doc.ents:
                entities.append(Entity(
                    text=ent.text,
                    label=ent.label_,
                    confidence=0.8,  # spaCy ne fournit pas de score de confiance
                    start=ent.start_char,
                    end=ent.end_char
                ))
            
            # Ajout d'entités personnalisées
            custom_entities = await self._extract_custom_entities(text)
            entities.extend(custom_entities)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction d'entités spaCy: {e}")
            # Fallback vers regex
            entities = await self._extract_entities_regex(text)
        
        return entities
    
    async def _extract_entities_regex(self, text: str) -> List[Entity]:
        """Extraction d'entités basique par regex"""
        entities = []
        
        # Patterns regex pour différents types d'entités
        patterns = {
            "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "PHONE": r'\b(?:\+33|0)[1-9](?:[0-9]{8})\b',
            "MONEY": r'\b\d+(?:[.,]\d{2})?\s*(?:€|euros?|EUR)\b',
            "PERCENT": r'\b\d+(?:[.,]\d+)?\s*%\b',
            "DATE": r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
        }
        
        for label, pattern in patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append(Entity(
                    text=match.group(),
                    label=label,
                    confidence=0.7,
                    start=match.start(),
                    end=match.end()
                ))
        
        return entities
    
    async def _extract_custom_entities(self, text: str) -> List[Entity]:
        """Extraction d'entités personnalisées pour le domaine"""
        entities = []
        
        # Mots-clés du domaine e-commerce/site web
        domain_keywords = {
            "PRODUCT": ["produit", "article", "item", "commande", "achat"],
            "ACTION": ["acheter", "commander", "ajouter", "supprimer", "modifier"],
            "NAVIGATION": ["page", "section", "menu", "accueil", "contact"],
            "SUPPORT": ["aide", "support", "problème", "bug", "erreur"]
        }
        
        text_lower = text.lower()
        
        for label, keywords in domain_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    start = text_lower.find(keyword)
                    end = start + len(keyword)
                    entities.append(Entity(
                        text=text[start:end],
                        label=label,
                        confidence=0.6,
                        start=start,
                        end=end
                    ))
        
        return entities
    
    async def _detect_intent_llm(self, text: str, context: Optional[Dict] = None) -> Intent:
        """Détecte l'intention avec un LLM"""
        if not self.langchain_llm:
            # Fallback vers détection basique
            return await self._detect_intent_basic(text)
        
        try:
            # Prompt pour la détection d'intention
            system_prompt = """
            Tu es un expert en analyse d'intentions utilisateur pour un site web e-commerce.
            
            Analyse le texte utilisateur et détermine:
            1. Le type d'intention parmi: question, command, navigation, search, form_fill, purchase, support, other
            2. Les paramètres extraits du texte
            3. Une description de l'intention
            4. Un score de confiance entre 0 et 1
            
            Réponds au format JSON:
            {
                "type": "type_intention",
                "confidence": 0.95,
                "parameters": {"param1": "valeur1"},
                "description": "Description de l'intention"
            }
            """
            
            context_info = f"Contexte: {context}" if context else ""
            user_prompt = f"{context_info}\n\nTexte utilisateur: {text}"
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = await self.langchain_llm.ainvoke(messages)
            
            # Parsing de la réponse JSON
            import json
            try:
                intent_data = json.loads(response.content)
                
                return Intent(
                    type=IntentType(intent_data.get("type", "other")),
                    confidence=intent_data.get("confidence", 0.5),
                    parameters=intent_data.get("parameters", {}),
                    description=intent_data.get("description", "")
                )
            except (json.JSONDecodeError, ValueError):
                logger.warning("Réponse LLM non parsable, utilisation du fallback")
                return await self._detect_intent_basic(text)
        
        except Exception as e:
            logger.error(f"Erreur lors de la détection d'intention LLM: {e}")
            return await self._detect_intent_basic(text)
    
    async def _detect_intent_basic(self, text: str) -> Intent:
        """Détection d'intention basique par mots-clés"""
        text_lower = text.lower()
        
        # Patterns d'intention
        intent_patterns = {
            IntentType.QUESTION: ["comment", "pourquoi", "qu'est-ce", "?", "aide"],
            IntentType.SEARCH: ["chercher", "trouver", "recherche", "où"],
            IntentType.PURCHASE: ["acheter", "commander", "panier", "payer"],
            IntentType.NAVIGATION: ["aller", "page", "section", "menu"],
            IntentType.SUPPORT: ["problème", "bug", "erreur", "support"],
            IntentType.FORM_FILL: ["remplir", "formulaire", "inscription", "contact"]
        }
        
        # Calcul des scores pour chaque intention
        scores = {}
        for intent_type, keywords in intent_patterns.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                scores[intent_type] = score / len(keywords)
        
        if scores:
            # Intention avec le meilleur score
            best_intent = max(scores.keys(), key=lambda k: scores[k])
            confidence = min(scores[best_intent] * 2, 1.0)  # Normalisation
            
            return Intent(
                type=best_intent,
                confidence=confidence,
                parameters={"detected_keywords": [k for k in intent_patterns[best_intent] if k in text_lower]},
                description=f"Intention détectée: {best_intent.value}"
            )
        else:
            return Intent(
                type=IntentType.OTHER,
                confidence=0.3,
                parameters={},
                description="Intention non déterminée"
            )
    
    async def _analyze_sentiment(self, text: str) -> Optional[Dict[str, float]]:
        """Analyse de sentiment basique"""
        # Mots positifs et négatifs en français
        positive_words = ["bon", "bien", "excellent", "parfait", "super", "génial", "merci"]
        negative_words = ["mauvais", "nul", "horrible", "problème", "erreur", "bug"]
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total_words = len(text.split())
        
        if total_words == 0:
            return None
        
        positive_score = positive_count / total_words
        negative_score = negative_count / total_words
        neutral_score = max(0, 1 - positive_score - negative_score)
        
        return {
            "positive": positive_score,
            "negative": negative_score,
            "neutral": neutral_score
        }
    
    async def _enrich_context(self, text: str, intent: Intent, entities: List[Entity], 
                            original_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Enrichit le contexte avec les informations extraites"""
        enriched = original_context.copy() if original_context else {}
        
        # Ajout des informations d'analyse
        enriched.update({
            "analyzed_text": text,
            "text_length": len(text),
            "word_count": len(text.split()),
            "entity_count": len(entities),
            "entity_types": list(set(e.label for e in entities)),
            "intent_type": intent.type.value,
            "intent_confidence": intent.confidence
        })
        
        # Extraction de métadonnées supplémentaires
        if "@" in text:
            enriched["contains_email"] = True
        if any(char.isdigit() for char in text):
            enriched["contains_numbers"] = True
        if "?" in text:
            enriched["is_question"] = True
        
        return enriched
    
    def _calculate_confidence(self, intent: Intent, entities: List[Entity]) -> float:
        """Calcule un score de confiance global"""
        # Score basé sur la confiance de l'intention et la qualité des entités
        intent_weight = 0.7
        entity_weight = 0.3
        
        intent_score = intent.confidence
        
        if entities:
            entity_score = sum(e.confidence for e in entities) / len(entities)
        else:
            entity_score = 0.5  # Score neutre si pas d'entités
        
        return intent_weight * intent_score + entity_weight * entity_score
    
    async def cleanup(self):
        """Nettoyage des ressources"""
        try:
            # Fermeture des clients si nécessaire
            if self.openai_client:
                await self.openai_client.close()
            
            self.initialized = False
            logger.info("Service NLP nettoyé")
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du service NLP: {e}")