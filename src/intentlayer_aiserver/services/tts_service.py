#!/usr/bin/env python3

import asyncio
import os
import uuid
from pathlib import Path
from typing import Optional
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)

class TTSService:
    """Service de synthèse vocale (Text-to-Speech)"""
    
    def __init__(self):
        self.initialized = False
        self.audio_output_path = None
        self.supported_languages = ['fr', 'en']
        self.default_voice = 'fr'
    
    async def initialize(self):
        """Initialise le service TTS"""
        try:
            logger.info("Initialisation du service TTS...")
            
            # Création du répertoire de sortie audio
            audio_path = Path(settings.memory_path) / "audio"
            audio_path.mkdir(parents=True, exist_ok=True)
            self.audio_output_path = audio_path
            
            # Vérification de la disponibilité de 'say' sur macOS
            if await self._check_system_tts():
                logger.info("Service TTS système disponible")
            else:
                logger.warning("Service TTS système non disponible, utilisation du mode texte uniquement")
            
            self.initialized = True
            logger.info("Service TTS initialisé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du service TTS: {e}")
            raise
    
    async def _check_system_tts(self) -> bool:
        """Vérifie si le TTS système est disponible"""
        try:
            # Test de la commande 'say' sur macOS
            process = await asyncio.create_subprocess_exec(
                'which', 'say',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            return process.returncode == 0
        except Exception:
            return False
    
    async def text_to_speech(
        self, 
        text: str, 
        language: str = 'fr',
        voice: Optional[str] = None
    ) -> Optional[str]:
        """Convertit du texte en audio"""
        try:
            if not self.initialized:
                await self.initialize()
            
            if not text or len(text.strip()) == 0:
                return None
            
            # Génération d'un nom de fichier unique
            audio_filename = f"tts_{uuid.uuid4().hex[:8]}.aiff"
            audio_file_path = self.audio_output_path / audio_filename
            
            # Nettoyage du texte pour éviter les problèmes avec la commande
            clean_text = text.replace('"', '').replace("'", "").strip()
            
            # Utilisation de la commande 'say' sur macOS
            if await self._check_system_tts():
                # Sélection de la voix selon la langue
                voice_option = self._get_voice_for_language(language, voice)
                
                # Commande TTS
                cmd = [
                    'say',
                    '-o', str(audio_file_path),
                    '-r', '200',  # Vitesse de parole
                ]
                
                if voice_option:
                    cmd.extend(['-v', voice_option])
                
                cmd.append(clean_text)
                
                # Exécution de la commande
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0 and audio_file_path.exists():
                    # Retourner l'URL relative du fichier audio
                    relative_path = f"/audio/{audio_filename}"
                    logger.info(f"Audio généré avec succès: {relative_path}")
                    return relative_path
                else:
                    logger.error(f"Erreur TTS: {stderr.decode() if stderr else 'Erreur inconnue'}")
                    return None
            else:
                logger.warning("TTS système non disponible")
                return None
                
        except Exception as e:
            logger.error(f"Erreur lors de la génération audio: {e}")
            return None
    
    def _get_voice_for_language(self, language: str, voice: Optional[str] = None) -> Optional[str]:
        """Sélectionne une voix appropriée selon la langue"""
        if voice:
            return voice
        
        # Voix par défaut selon la langue sur macOS
        voice_mapping = {
            'fr': 'Thomas',      # Voix française
            'en': 'Alex',        # Voix anglaise
            'es': 'Diego',       # Voix espagnole
            'de': 'Anna',        # Voix allemande
            'it': 'Luca',        # Voix italienne
        }
        
        return voice_mapping.get(language, 'Thomas')
    
    async def get_available_voices(self) -> list:
        """Récupère la liste des voix disponibles"""
        try:
            if not await self._check_system_tts():
                return []
            
            # Commande pour lister les voix disponibles
            process = await asyncio.create_subprocess_exec(
                'say', '-v', '?',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                voices = []
                for line in stdout.decode().split('\n'):
                    if line.strip():
                        # Format: "VoiceName    language    # description"
                        parts = line.split()
                        if len(parts) >= 2:
                            voice_name = parts[0]
                            language = parts[1] if len(parts) > 1 else 'unknown'
                            voices.append({
                                'name': voice_name,
                                'language': language,
                                'description': ' '.join(parts[2:]) if len(parts) > 2 else ''
                            })
                return voices
            else:
                return []
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des voix: {e}")
            return []
    
    async def cleanup_old_audio_files(self, max_age_hours: int = 24):
        """Nettoie les anciens fichiers audio"""
        try:
            if not self.audio_output_path or not self.audio_output_path.exists():
                return
            
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            cleaned_count = 0
            for audio_file in self.audio_output_path.glob("tts_*.aiff"):
                file_age = current_time - audio_file.stat().st_mtime
                if file_age > max_age_seconds:
                    audio_file.unlink()
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Nettoyage audio: {cleaned_count} fichiers supprimés")
                
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des fichiers audio: {e}")
    
    async def cleanup(self):
        """Nettoie les ressources du service"""
        try:
            # Nettoyage des anciens fichiers audio
            await self.cleanup_old_audio_files()
            logger.info("Service TTS nettoyé")
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du service TTS: {e}")