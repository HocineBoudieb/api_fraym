"""Service de gestion de la mémoire contextuelle"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging
import uuid

from ..core.config import settings
from ..models.schemas import MemoryRequest, MemoryResponse, MemoryEntry

logger = logging.getLogger(__name__)

class MemoryService:
    """Service de gestion de la mémoire contextuelle des utilisateurs"""
    
    def __init__(self):
        self.memory_storage = {}  # Stockage en mémoire temporaire
        self.memory_file_path = None
        self.initialized = False
        self.max_memory_entries = 1000
        self.memory_retention_days = 30
    
    async def initialize(self):
        """Initialise le service de mémoire"""
        try:
            logger.info("Initialisation du service de mémoire...")
            
            # Création du répertoire de mémoire
            memory_path = Path(settings.memory_path)
            memory_path.mkdir(parents=True, exist_ok=True)
            
            self.memory_file_path = memory_path / "user_memory.json"
            
            # Chargement de la mémoire existante
            await self._load_memory_from_file()
            
            # Nettoyage des anciennes entrées
            await self._cleanup_old_entries()
            
            self.initialized = True
            logger.info("Service de mémoire initialisé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du service de mémoire: {e}")
            raise
    
    async def _load_memory_from_file(self):
        """Charge la mémoire depuis le fichier"""
        try:
            if self.memory_file_path.exists():
                with open(self.memory_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memory_storage = data
                logger.info(f"Mémoire chargée: {len(self.memory_storage)} utilisateurs")
            else:
                self.memory_storage = {}
                logger.info("Nouveau fichier de mémoire créé")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la mémoire: {e}")
            self.memory_storage = {}
    
    async def _save_memory_to_file(self):
        """Sauvegarde la mémoire dans le fichier"""
        try:
            with open(self.memory_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.memory_storage, f, ensure_ascii=False, indent=2, default=str)
            logger.debug("Mémoire sauvegardée")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la mémoire: {e}")
    
    async def _cleanup_old_entries(self):
        """Nettoie les anciennes entrées de mémoire"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.memory_retention_days)
            cleaned_count = 0
            
            for user_id in list(self.memory_storage.keys()):
                user_memory = self.memory_storage[user_id]
                original_count = len(user_memory.get('entries', []))
                
                # Filtrage des entrées récentes
                user_memory['entries'] = [
                    entry for entry in user_memory.get('entries', [])
                    if datetime.fromisoformat(entry['timestamp']) > cutoff_date
                ]
                
                cleaned_count += original_count - len(user_memory['entries'])
                
                # Suppression des utilisateurs sans entrées
                if not user_memory['entries']:
                    del self.memory_storage[user_id]
            
            if cleaned_count > 0:
                logger.info(f"Nettoyage terminé: {cleaned_count} entrées supprimées")
                await self._save_memory_to_file()
                
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage de la mémoire: {e}")
    
    async def store_interaction(self, request: MemoryRequest) -> MemoryResponse:
        """Stocke une interaction utilisateur"""
        try:
            # Création de l'entrée de mémoire
            entry = MemoryEntry(
                id=str(uuid.uuid4()),
                user_id=request.user_id,
                session_id=request.session_id,
                timestamp=datetime.now(),
                interaction_type=request.interaction.get('type', 'unknown'),
                data=request.interaction,
                context=request.context or {},
                relevance_score=self._calculate_relevance_score(request.interaction)
            )
            
            # Ajout à la mémoire utilisateur
            if request.user_id not in self.memory_storage:
                self.memory_storage[request.user_id] = {
                    'user_id': request.user_id,
                    'created_at': datetime.now().isoformat(),
                    'last_interaction': datetime.now().isoformat(),
                    'entries': [],
                    'preferences': {},
                    'context_summary': {}
                }
            
            user_memory = self.memory_storage[request.user_id]
            user_memory['entries'].append(entry.dict())
            user_memory['last_interaction'] = datetime.now().isoformat()
            
            # Limitation du nombre d'entrées par utilisateur
            if len(user_memory['entries']) > self.max_memory_entries:
                # Garde les entrées les plus récentes et les plus pertinentes
                user_memory['entries'] = sorted(
                    user_memory['entries'],
                    key=lambda x: (x['relevance_score'], x['timestamp']),
                    reverse=True
                )[:self.max_memory_entries]
            
            # Mise à jour du résumé contextuel
            await self._update_context_summary(request.user_id)
            
            # Sauvegarde
            await self._save_memory_to_file()
            
            return MemoryResponse(
                success=True,
                message="Interaction stockée avec succès",
                memory_entries=[entry],
                context_summary=user_memory['context_summary']
            )
            
        except Exception as e:
            logger.error(f"Erreur lors du stockage de l'interaction: {e}")
            return MemoryResponse(
                success=False,
                message=f"Erreur lors du stockage: {str(e)}"
            )
    
    async def get_user_context(self, user_id: str, session_id: Optional[str] = None, 
                             limit: int = 10) -> MemoryResponse:
        """Récupère le contexte d'un utilisateur"""
        try:
            if user_id not in self.memory_storage:
                return MemoryResponse(
                    success=True,
                    message="Aucun historique trouvé pour cet utilisateur",
                    memory_entries=[],
                    context_summary={}
                )
            
            user_memory = self.memory_storage[user_id]
            entries = user_memory['entries']
            
            # Filtrage par session si spécifiée
            if session_id:
                entries = [e for e in entries if e.get('session_id') == session_id]
            
            # Tri par pertinence et récence
            entries = sorted(
                entries,
                key=lambda x: (x['relevance_score'], x['timestamp']),
                reverse=True
            )[:limit]
            
            # Conversion en objets MemoryEntry
            memory_entries = [
                MemoryEntry(**entry) for entry in entries
            ]
            
            return MemoryResponse(
                success=True,
                message=f"Contexte récupéré: {len(memory_entries)} entrées",
                memory_entries=memory_entries,
                context_summary=user_memory['context_summary']
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du contexte: {e}")
            return MemoryResponse(
                success=False,
                message=f"Erreur lors de la récupération: {str(e)}"
            )
    
    async def search_user_memory(self, user_id: str, query: str, 
                               limit: int = 5) -> MemoryResponse:
        """Recherche dans la mémoire d'un utilisateur"""
        try:
            if user_id not in self.memory_storage:
                return MemoryResponse(
                    success=True,
                    message="Aucun historique trouvé",
                    memory_entries=[]
                )
            
            user_memory = self.memory_storage[user_id]
            query_lower = query.lower()
            
            # Recherche textuelle simple
            matching_entries = []
            for entry in user_memory['entries']:
                score = self._calculate_search_score(entry, query_lower)
                if score > 0:
                    entry_copy = entry.copy()
                    entry_copy['search_score'] = score
                    matching_entries.append(entry_copy)
            
            # Tri par score de recherche
            matching_entries = sorted(
                matching_entries,
                key=lambda x: x['search_score'],
                reverse=True
            )[:limit]
            
            # Conversion en objets MemoryEntry
            memory_entries = [
                MemoryEntry(**{k: v for k, v in entry.items() if k != 'search_score'})
                for entry in matching_entries
            ]
            
            return MemoryResponse(
                success=True,
                message=f"Recherche terminée: {len(memory_entries)} résultats",
                memory_entries=memory_entries
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {e}")
            return MemoryResponse(
                success=False,
                message=f"Erreur lors de la recherche: {str(e)}"
            )
    
    async def update_user_preferences(self, user_id: str, 
                                    preferences: Dict[str, Any]) -> MemoryResponse:
        """Met à jour les préférences utilisateur"""
        try:
            if user_id not in self.memory_storage:
                self.memory_storage[user_id] = {
                    'user_id': user_id,
                    'created_at': datetime.now().isoformat(),
                    'last_interaction': datetime.now().isoformat(),
                    'entries': [],
                    'preferences': {},
                    'context_summary': {}
                }
            
            # Mise à jour des préférences
            self.memory_storage[user_id]['preferences'].update(preferences)
            self.memory_storage[user_id]['last_interaction'] = datetime.now().isoformat()
            
            await self._save_memory_to_file()
            
            return MemoryResponse(
                success=True,
                message="Préférences mises à jour"
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des préférences: {e}")
            return MemoryResponse(
                success=False,
                message=f"Erreur: {str(e)}"
            )
    
    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Récupère les préférences utilisateur"""
        try:
            if user_id in self.memory_storage:
                return self.memory_storage[user_id].get('preferences', {})
            return {}
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des préférences: {e}")
            return {}
    
    async def _update_context_summary(self, user_id: str):
        """Met à jour le résumé contextuel d'un utilisateur"""
        try:
            user_memory = self.memory_storage[user_id]
            entries = user_memory['entries']
            
            if not entries:
                return
            
            # Analyse des patterns d'interaction
            interaction_types = {}
            recent_intents = []
            common_entities = {}
            
            # Analyse des 20 dernières interactions
            recent_entries = sorted(entries, key=lambda x: x['timestamp'], reverse=True)[:20]
            
            for entry in recent_entries:
                # Types d'interaction
                interaction_type = entry.get('interaction_type', 'unknown')
                interaction_types[interaction_type] = interaction_types.get(interaction_type, 0) + 1
                
                # Intentions récentes
                if 'intent' in entry.get('data', {}):
                    recent_intents.append(entry['data']['intent'])
                
                # Entités communes
                entities = entry.get('context', {}).get('entity_types', [])
                for entity in entities:
                    common_entities[entity] = common_entities.get(entity, 0) + 1
            
            # Création du résumé
            context_summary = {
                'total_interactions': len(entries),
                'recent_interactions': len(recent_entries),
                'most_common_interaction': max(interaction_types.items(), key=lambda x: x[1])[0] if interaction_types else None,
                'interaction_types': interaction_types,
                'recent_intents': recent_intents[-5:],  # 5 dernières intentions
                'common_entities': dict(sorted(common_entities.items(), key=lambda x: x[1], reverse=True)[:5]),
                'last_updated': datetime.now().isoformat(),
                'user_activity_level': self._calculate_activity_level(entries)
            }
            
            user_memory['context_summary'] = context_summary
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du résumé contextuel: {e}")
    
    def _calculate_relevance_score(self, interaction: Dict[str, Any]) -> float:
        """Calcule un score de pertinence pour une interaction"""
        base_score = 0.5
        
        # Bonus pour certains types d'interaction
        interaction_type = interaction.get('type', '')
        if interaction_type in ['purchase', 'support', 'form_fill']:
            base_score += 0.3
        elif interaction_type in ['question', 'search']:
            base_score += 0.2
        
        # Bonus si l'interaction contient des entités importantes
        if 'entities' in interaction:
            entity_count = len(interaction['entities'])
            base_score += min(entity_count * 0.1, 0.3)
        
        # Bonus pour les interactions avec contexte riche
        if 'context' in interaction and len(interaction['context']) > 2:
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _calculate_search_score(self, entry: Dict[str, Any], query: str) -> float:
        """Calcule un score de correspondance pour la recherche"""
        score = 0.0
        
        # Recherche dans les données d'interaction
        data_text = json.dumps(entry.get('data', {}), ensure_ascii=False).lower()
        if query in data_text:
            score += 1.0
        
        # Recherche dans le contexte
        context_text = json.dumps(entry.get('context', {}), ensure_ascii=False).lower()
        if query in context_text:
            score += 0.5
        
        # Recherche par mots-clés
        query_words = query.split()
        for word in query_words:
            if word in data_text:
                score += 0.3
            if word in context_text:
                score += 0.1
        
        # Bonus pour la pertinence de l'entrée
        score *= entry.get('relevance_score', 0.5)
        
        return score
    
    def _calculate_activity_level(self, entries: List[Dict[str, Any]]) -> str:
        """Calcule le niveau d'activité d'un utilisateur"""
        if not entries:
            return "inactive"
        
        # Interactions des 7 derniers jours
        week_ago = datetime.now() - timedelta(days=7)
        recent_entries = [
            e for e in entries
            if datetime.fromisoformat(e['timestamp']) > week_ago
        ]
        
        recent_count = len(recent_entries)
        
        if recent_count >= 10:
            return "very_active"
        elif recent_count >= 5:
            return "active"
        elif recent_count >= 1:
            return "moderate"
        else:
            return "low"
    
    async def cleanup_user_data(self, user_id: str) -> MemoryResponse:
        """Supprime toutes les données d'un utilisateur"""
        try:
            if user_id in self.memory_storage:
                del self.memory_storage[user_id]
                await self._save_memory_to_file()
                
                return MemoryResponse(
                    success=True,
                    message="Données utilisateur supprimées"
                )
            else:
                return MemoryResponse(
                    success=True,
                    message="Aucune donnée trouvée pour cet utilisateur"
                )
                
        except Exception as e:
            logger.error(f"Erreur lors de la suppression des données: {e}")
            return MemoryResponse(
                success=False,
                message=f"Erreur: {str(e)}"
            )
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques sur la mémoire"""
        try:
            total_users = len(self.memory_storage)
            total_entries = sum(len(user['entries']) for user in self.memory_storage.values())
            
            # Calcul de la taille moyenne des entrées par utilisateur
            avg_entries = total_entries / total_users if total_users > 0 else 0
            
            # Utilisateurs actifs (interaction dans les 7 derniers jours)
            week_ago = datetime.now() - timedelta(days=7)
            active_users = 0
            
            for user_data in self.memory_storage.values():
                last_interaction = datetime.fromisoformat(user_data['last_interaction'])
                if last_interaction > week_ago:
                    active_users += 1
            
            return {
                'total_users': total_users,
                'total_entries': total_entries,
                'average_entries_per_user': round(avg_entries, 2),
                'active_users_last_week': active_users,
                'memory_file_size': self.memory_file_path.stat().st_size if self.memory_file_path.exists() else 0,
                'last_cleanup': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des statistiques: {e}")
            return {}
    
    async def cleanup(self):
        """Nettoyage des ressources"""
        try:
            # Sauvegarde finale
            await self._save_memory_to_file()
            
            self.initialized = False
            logger.info("Service de mémoire nettoyé")
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du service de mémoire: {e}")