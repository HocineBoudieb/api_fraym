#!/usr/bin/env python3

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

from ..core.config import settings
from ..models.schemas import SessionRequest, SessionResponse, SessionInfo

logger = logging.getLogger(__name__)

class SessionService:
    """Service de gestion des sessions utilisateur"""
    
    def __init__(self):
        self.active_sessions = {}  # Stockage des sessions actives en mémoire
        self.session_file_path = None
        self.initialized = False
        self.session_timeout = 3600  # 1 heure par défaut
        self.max_sessions_per_user = 5
        self.cleanup_interval = 300  # Nettoyage toutes les 5 minutes
        self._cleanup_task = None
    
    async def initialize(self):
        """Initialise le service de sessions"""
        try:
            logger.info("Initialisation du service de sessions...")
            
            # Création du répertoire de sessions
            session_path = Path(settings.memory_path) / "sessions"
            session_path.mkdir(parents=True, exist_ok=True)
            
            self.session_file_path = session_path / "active_sessions.json"
            
            # Chargement des sessions existantes
            await self._load_sessions_from_file()
            
            # Nettoyage des sessions expirées
            await self._cleanup_expired_sessions()
            
            # Démarrage de la tâche de nettoyage périodique
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            
            self.initialized = True
            logger.info("Service de sessions initialisé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du service de sessions: {e}")
            raise
    
    async def _load_sessions_from_file(self):
        """Charge les sessions depuis le fichier"""
        try:
            if self.session_file_path.exists():
                with open(self.session_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.active_sessions = data
                logger.info(f"Sessions chargées: {len(self.active_sessions)} sessions actives")
            else:
                self.active_sessions = {}
                logger.info("Nouveau fichier de sessions créé")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des sessions: {e}")
            self.active_sessions = {}
    
    async def _save_sessions_to_file(self):
        """Sauvegarde les sessions dans le fichier"""
        try:
            with open(self.session_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.active_sessions, f, ensure_ascii=False, indent=2, default=str)
            logger.debug("Sessions sauvegardées")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des sessions: {e}")
    
    async def _cleanup_expired_sessions(self):
        """Nettoie les sessions expirées"""
        try:
            current_time = datetime.now()
            expired_sessions = []
            
            for session_id, session_data in self.active_sessions.items():
                last_activity = datetime.fromisoformat(session_data['last_activity'])
                if (current_time - last_activity).total_seconds() > self.session_timeout:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self.active_sessions[session_id]
                logger.debug(f"Session expirée supprimée: {session_id}")
            
            if expired_sessions:
                logger.info(f"Nettoyage terminé: {len(expired_sessions)} sessions expirées supprimées")
                await self._save_sessions_to_file()
                
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des sessions: {e}")
    
    async def _periodic_cleanup(self):
        """Tâche de nettoyage périodique"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erreur dans le nettoyage périodique: {e}")
    
    async def create_session(self, user_id: str, user_data: Optional[Dict[str, Any]] = None) -> SessionResponse:
        """Crée une nouvelle session pour un utilisateur"""
        try:
            if not self.initialized:
                await self.initialize()
            
            # Génération d'un ID de session unique
            session_id = str(uuid.uuid4())
            current_time = datetime.now()
            
            # Vérification du nombre de sessions par utilisateur
            user_sessions = [
                sid for sid, sdata in self.active_sessions.items() 
                if sdata['user_id'] == user_id
            ]
            
            # Suppression des anciennes sessions si limite atteinte
            if len(user_sessions) >= self.max_sessions_per_user:
                oldest_session = min(
                    user_sessions,
                    key=lambda sid: datetime.fromisoformat(self.active_sessions[sid]['created_at'])
                )
                del self.active_sessions[oldest_session]
                logger.info(f"Ancienne session supprimée pour utilisateur {user_id}: {oldest_session}")
            
            # Création de la nouvelle session
            session_data = {
                'session_id': session_id,
                'user_id': user_id,
                'created_at': current_time.isoformat(),
                'last_activity': current_time.isoformat(),
                'user_data': user_data or {},
                'context': {},
                'interaction_count': 0,
                'status': 'active'
            }
            
            self.active_sessions[session_id] = session_data
            await self._save_sessions_to_file()
            
            logger.info(f"Nouvelle session créée pour utilisateur {user_id}: {session_id}")
            
            return SessionResponse(
                success=True,
                message="Session créée avec succès",
                session_info=SessionInfo(
                    session_id=session_id,
                    user_id=user_id,
                    created_at=current_time,
                    last_activity=current_time,
                    status='active',
                    interaction_count=0
                )
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de session: {e}")
            return SessionResponse(
                success=False,
                message=f"Erreur lors de la création de session: {str(e)}",
                session_info=None
            )
    
    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Récupère les informations d'une session"""
        try:
            if not self.initialized:
                await self.initialize()
            
            if session_id not in self.active_sessions:
                return None
            
            session_data = self.active_sessions[session_id]
            
            # Vérification de l'expiration
            last_activity = datetime.fromisoformat(session_data['last_activity'])
            if (datetime.now() - last_activity).total_seconds() > self.session_timeout:
                del self.active_sessions[session_id]
                await self._save_sessions_to_file()
                return None
            
            return SessionInfo(
                session_id=session_data['session_id'],
                user_id=session_data['user_id'],
                created_at=datetime.fromisoformat(session_data['created_at']),
                last_activity=datetime.fromisoformat(session_data['last_activity']),
                status=session_data['status'],
                interaction_count=session_data['interaction_count']
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de session: {e}")
            return None
    
    async def update_session_activity(self, session_id: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Met à jour l'activité d'une session"""
        try:
            if not self.initialized:
                await self.initialize()
            
            if session_id not in self.active_sessions:
                return False
            
            session_data = self.active_sessions[session_id]
            session_data['last_activity'] = datetime.now().isoformat()
            session_data['interaction_count'] += 1
            
            if context:
                session_data['context'].update(context)
            
            await self._save_sessions_to_file()
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de session: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Supprime une session"""
        try:
            if not self.initialized:
                await self.initialize()
            
            if session_id in self.active_sessions:
                user_id = self.active_sessions[session_id]['user_id']
                del self.active_sessions[session_id]
                await self._save_sessions_to_file()
                logger.info(f"Session supprimée pour utilisateur {user_id}: {session_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de session: {e}")
            return False
    
    async def get_user_sessions(self, user_id: str) -> List[SessionInfo]:
        """Récupère toutes les sessions actives d'un utilisateur"""
        try:
            if not self.initialized:
                await self.initialize()
            
            user_sessions = []
            
            for session_id, session_data in self.active_sessions.items():
                if session_data['user_id'] == user_id:
                    # Vérification de l'expiration
                    last_activity = datetime.fromisoformat(session_data['last_activity'])
                    if (datetime.now() - last_activity).total_seconds() <= self.session_timeout:
                        user_sessions.append(SessionInfo(
                            session_id=session_data['session_id'],
                            user_id=session_data['user_id'],
                            created_at=datetime.fromisoformat(session_data['created_at']),
                            last_activity=datetime.fromisoformat(session_data['last_activity']),
                            status=session_data['status'],
                            interaction_count=session_data['interaction_count']
                        ))
            
            return user_sessions
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des sessions utilisateur: {e}")
            return []
    
    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Récupère le contexte d'une session"""
        try:
            if not self.initialized:
                await self.initialize()
            
            if session_id in self.active_sessions:
                return self.active_sessions[session_id].get('context', {})
            
            return {}
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du contexte de session: {e}")
            return {}
    
    async def cleanup(self):
        """Nettoie les ressources du service"""
        try:
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            await self._save_sessions_to_file()
            logger.info("Service de sessions nettoyé")
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du service de sessions: {e}")