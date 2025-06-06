"""Service RAG pour la gestion des bases vectorielles et la recherche sémantique"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from ..core.config import settings

logger = logging.getLogger(__name__)

class RAGService:
    """Service de Retrieval-Augmented Generation"""
    
    def __init__(self):
        self.embedding_model = None
        self.chroma_client = None
        self.ui_components_collection = None
        self.layouts_collection = None
        self.knowledge_collection = None
        self.images_collection = None
        self.text_splitter = None
        self.initialized = False
    
    async def initialize(self):
        """Initialise le service RAG"""
        try:
            logger.info("Initialisation du service RAG...")
            
            # Initialisation du modèle d'embedding
            logger.info(f"Chargement du modèle d'embedding: {settings.embedding_model}")
            self.embedding_model = SentenceTransformer(settings.embedding_model)
            
            # Initialisation de ChromaDB
            await self._initialize_chromadb()
            
            # Initialisation du text splitter
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.rag_chunk_size,
                chunk_overlap=settings.rag_chunk_overlap,
                separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
            )
            
            # Chargement des données initiales
            await self._load_initial_data()
            
            self.initialized = True
            logger.info("Service RAG initialisé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du service RAG: {e}")
            raise
    
    async def _initialize_chromadb(self):
        """Initialise ChromaDB"""
        try:
            # Création du répertoire de données
            os.makedirs(settings.vector_db_path, exist_ok=True)
            
            # Configuration ChromaDB
            chroma_settings = ChromaSettings(
                persist_directory=settings.vector_db_path,
                anonymized_telemetry=False
            )
            
            self.chroma_client = chromadb.PersistentClient(
                path=settings.vector_db_path,
                settings=chroma_settings
            )
            
            # Création des collections
            self.ui_components_collection = self.chroma_client.get_or_create_collection(
                name="ui_components",
                metadata={"description": "Documentation des composants UI"}
            )
            
            self.layouts_collection = self.chroma_client.get_or_create_collection(
                name="ui_layouts",
                metadata={"description": "Layouts et positionnements des composants"}
            )
            
            self.knowledge_collection = self.chroma_client.get_or_create_collection(
                name="knowledge_base",
                metadata={"description": "Base de connaissances du site"}
            )
            
            self.images_collection = self.chroma_client.get_or_create_collection(
                name="image_catalog",
                metadata={"description": "Catalogue d'images avec descriptions"}
            )
            
            logger.info("ChromaDB initialisé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de ChromaDB: {e}")
            raise
    
    async def _load_initial_data(self):
        """Charge les données initiales dans les collections"""
        try:
            # Chargement des composants UI
            await self._load_ui_components()
            
            # Chargement des layouts
            await self._load_ui_layouts()
            
            # Chargement de la base de connaissances
            await self._load_knowledge_base()
            
            # Chargement du catalogue d'images
            await self._load_image_catalog()
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données initiales: {e}")
            # Ne pas lever l'exception pour permettre le démarrage même sans données
    
    async def _load_ui_components(self):
        """Charge la documentation des composants UI"""
        ui_components_path = Path(settings.ui_components_path)
        
        if not ui_components_path.exists():
            logger.warning(f"Répertoire des composants UI non trouvé: {ui_components_path}")
            # Créer des composants par défaut
            await self._create_default_ui_components()
            return
        
        # Parcourir les fichiers de composants
        for file_path in ui_components_path.glob("**/*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    component_data = json.load(f)
                
                # Vérifier si c'est un array ou un objet unique
                if isinstance(component_data, list):
                    # Si c'est un array, traiter chaque composant
                    for component in component_data:
                        await self._add_ui_component(component)
                else:
                    # Si c'est un objet unique, le traiter directement
                    await self._add_ui_component(component_data)
                
            except Exception as e:
                logger.error(f"Erreur lors du chargement du composant {file_path}: {e}")
    
    async def _load_ui_layouts(self):
        """Charge les layouts UI"""
        layouts_file = Path(settings.ui_components_path) / "layouts.json"
        
        if not layouts_file.exists():
            logger.warning(f"Fichier des layouts non trouvé: {layouts_file}")
            # Créer des layouts par défaut
            await self._create_default_layouts()
            return
        
        try:
            with open(layouts_file, 'r', encoding='utf-8') as f:
                layouts_data = json.load(f)
            
            # Vérifier si c'est un array ou un objet unique
            if isinstance(layouts_data, list):
                # Si c'est un array, traiter chaque layout
                for layout in layouts_data:
                    await self._add_ui_layout(layout)
            else:
                # Si c'est un objet unique, le traiter directement
                await self._add_ui_layout(layouts_data)
                
        except Exception as e:
            logger.error(f"Erreur lors du chargement des layouts: {e}")
    
    async def _create_default_ui_components(self):
        """Crée des composants UI par défaut"""
        default_components = [
            {
                "name": "Button",
                "type": "button",
                "description": "Bouton interactif pour les actions utilisateur",
                "props": {
                    "variant": ["primary", "secondary", "outline", "ghost"],
                    "size": ["sm", "md", "lg"],
                    "disabled": "boolean",
                    "onClick": "function"
                },
                "usage": "Utilisé pour les actions principales, soumissions de formulaires, navigation",
                "examples": [
                    {"variant": "primary", "children": "Valider"},
                    {"variant": "outline", "size": "sm", "children": "Annuler"}
                ]
            },
            {
                "name": "Card",
                "type": "card",
                "description": "Conteneur pour grouper du contenu connexe",
                "props": {
                    "title": "string",
                    "description": "string",
                    "image": "string",
                    "actions": "array"
                },
                "usage": "Affichage de produits, articles, profils utilisateur",
                "examples": [
                    {"title": "Produit", "description": "Description du produit", "image": "/image.jpg"}
                ]
            },
            {
                "name": "Form",
                "type": "form",
                "description": "Formulaire de saisie de données",
                "props": {
                    "fields": "array",
                    "onSubmit": "function",
                    "validation": "object"
                },
                "usage": "Collecte d'informations utilisateur, inscription, contact",
                "examples": [
                    {"fields": [{"name": "email", "type": "email", "required": True}]}
                ]
            }
        ]
        
        for component in default_components:
            await self._add_ui_component(component)
    
    async def _add_ui_component(self, component_data: Dict[str, Any]):
        """Ajoute un composant UI à la collection"""
        try:
            # Création du texte descriptif pour l'embedding
            description_text = f"""
            Composant: {component_data.get('name', '')}
            Type: {component_data.get('type', '')}
            Description: {component_data.get('description', '')}
            Usage: {component_data.get('usage', '')}
            Props: {json.dumps(component_data.get('props', {}), ensure_ascii=False)}
            """
            
            # Génération de l'embedding
            embedding = self.embedding_model.encode(description_text).tolist()
            
            # Préparation des métadonnées (ChromaDB n'accepte que les types simples)
            metadata = {
                'name': str(component_data.get('name', '')),
                'type': str(component_data.get('type', '')),
                'description': str(component_data.get('description', '')),
                'usage': str(component_data.get('usage', '')),
                'category': str(component_data.get('category', '')),
                'data': json.dumps(component_data, ensure_ascii=False)  # Sérialiser les données complètes
            }
            
            # Ajout à la collection
            self.ui_components_collection.add(
                embeddings=[embedding],
                documents=[description_text],
                metadatas=[metadata],
                ids=[f"component_{component_data.get('name', 'unknown')}"]
            )
            
            logger.debug(f"Composant UI ajouté: {component_data.get('name')}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du composant UI: {e}")
    
    async def _add_ui_layout(self, layout_data: Dict[str, Any]):
        """Ajoute un layout UI à la collection ChromaDB"""
        try:
            # Création du texte descriptif pour l'embedding
            # Gérer les deux formats: 'component_areas' (nouveau) et 'components' (existant)
            areas = layout_data.get('component_areas', layout_data.get('components', []))
            
            components_desc = ""
            if areas:
                components_desc = " ".join([
                    f"{comp.get('id', comp.get('name', ''))}: {comp.get('description', '')} (x:{comp.get('position', comp).get('x', comp.get('x', 0))}, y:{comp.get('position', comp).get('y', comp.get('y', 0))}, w:{comp.get('position', comp).get('width', comp.get('width', 0))}, h:{comp.get('position', comp).get('height', comp.get('height', 0))})"
                    for comp in areas
                ])
            
            description_text = f"""
            Layout: {layout_data.get('name', '')}
            Type: {layout_data.get('type', '')}
            Description: {layout_data.get('description', '')}
            Catégorie: {layout_data.get('category', '')}
            Composants: {components_desc}
            Tags: {', '.join(layout_data.get('tags', []))}
            """
            
            # Génération de l'embedding
            embedding = self.embedding_model.encode(description_text).tolist()
            
            # Préparation des métadonnées
            metadata = {
                'name': str(layout_data.get('name', '')),
                'type': str(layout_data.get('type', '')),
                'description': str(layout_data.get('description', '')),
                'category': str(layout_data.get('category', '')),
                'tags': ', '.join(layout_data.get('tags', [])),
                'data': json.dumps(layout_data, ensure_ascii=False)  # Sérialiser les données complètes
            }
            
            # Ajout à la collection
            self.layouts_collection.add(
                embeddings=[embedding],
                documents=[description_text],
                metadatas=[metadata],
                ids=[f"layout_{layout_data.get('name', 'unknown')}"]
            )
            
            logger.debug(f"Layout UI ajouté: {layout_data.get('name')}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du layout UI: {e}")
    
    async def _load_image_catalog(self):
        """Charge le catalogue d'images"""
        image_catalog_path = Path("data/knowledge/image_catalog.json")
        
        if not image_catalog_path.exists():
            logger.warning(f"Fichier catalogue d'images non trouvé: {image_catalog_path}")
            return
        
        try:
            with open(image_catalog_path, 'r', encoding='utf-8') as f:
                catalog_data = json.load(f)
            
            images = catalog_data.get('images', [])
            logger.info(f"Chargement de {len(images)} images du catalogue")
            
            for image_data in images:
                await self._add_image_to_catalog(image_data)
            
            logger.info(f"Catalogue d'images chargé avec succès: {len(images)} images")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement du catalogue d'images: {e}")
    
    async def _add_image_to_catalog(self, image_data: Dict[str, Any]):
        """Ajoute une image au catalogue"""
        try:
            # Création du texte de description pour l'embedding
            description_parts = [
                image_data.get('description', ''),
                image_data.get('alt', ''),
                ' '.join(image_data.get('keywords', []))
            ]
            description_text = ' '.join(filter(None, description_parts))
            
            # Génération de l'embedding
            embedding = self.embedding_model.encode(description_text).tolist()
            
            # Métadonnées
            metadata = {
                'id': str(image_data.get('id', '')),
                'url': str(image_data.get('url', '')),
                'alt': str(image_data.get('alt', '')),
                'description': str(image_data.get('description', '')),
                'keywords': ', '.join(image_data.get('keywords', [])),
                'data': json.dumps(image_data, ensure_ascii=False)
            }
            
            # Ajout à la collection
            self.images_collection.add(
                embeddings=[embedding],
                documents=[description_text],
                metadatas=[metadata],
                ids=[f"image_{image_data.get('id', 'unknown')}"]
            )
            
            logger.debug(f"Image ajoutée au catalogue: {image_data.get('id')}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de l'image au catalogue: {e}")
    
    async def _create_default_layouts(self):
        """Crée des layouts par défaut"""
        default_layouts = [
            {
                "name": "HeaderContentFooter",
                "description": "Layout classique avec header, contenu principal et footer",
                "type": "page_layout",
                "components": [
                    {
                        "id": "header",
                        "position": {"x": 0, "y": 0, "width": 100, "height": 10},
                        "unit": "percentage",
                        "description": "Zone header"
                    },
                    {
                        "id": "main_content",
                        "position": {"x": 0, "y": 10, "width": 100, "height": 80},
                        "unit": "percentage",
                        "description": "Zone de contenu principal"
                    },
                    {
                        "id": "footer",
                        "position": {"x": 0, "y": 90, "width": 100, "height": 10},
                        "unit": "percentage",
                        "description": "Zone footer"
                    }
                ],
                "category": "basic",
                "tags": ["header", "footer", "classic"]
            }
        ]
        
        for layout in default_layouts:
            await self._add_ui_layout(layout)
    
    async def _load_knowledge_base(self):
        """Charge la base de connaissances"""
        knowledge_path = Path(settings.knowledge_base_path)
        
        if not knowledge_path.exists():
            logger.warning(f"Répertoire de la base de connaissances non trouvé: {knowledge_path}")
            # Créer une base de connaissances par défaut
            await self._create_default_knowledge()
            return
        
        # Parcourir les fichiers de connaissances
        for file_path in knowledge_path.glob("**/*.md"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                await self._add_knowledge_document(content, str(file_path))
                
            except Exception as e:
                logger.error(f"Erreur lors du chargement du document {file_path}: {e}")
    
    async def _create_default_knowledge(self):
        """Crée une base de connaissances par défaut"""
        default_knowledge = [
            {
                "title": "À propos de notre entreprise",
                "content": "Nous sommes une entreprise innovante spécialisée dans les solutions technologiques. Notre mission est de simplifier la vie de nos clients grâce à des outils intuitifs et performants.",
                "category": "entreprise"
            },
            {
                "title": "Support client",
                "content": "Notre équipe de support est disponible 24h/24 et 7j/7 pour vous aider. Vous pouvez nous contacter par email, téléphone ou chat en direct.",
                "category": "support"
            },
            {
                "title": "Politique de retour",
                "content": "Vous disposez de 30 jours pour retourner un produit. Le produit doit être dans son état d'origine avec tous les accessoires.",
                "category": "politique"
            }
        ]
        
        for knowledge in default_knowledge:
            content = f"# {knowledge['title']}\n\n{knowledge['content']}"
            await self._add_knowledge_document(content, knowledge['title'], knowledge)
    
    async def _add_knowledge_document(self, content: str, source: str, metadata: Optional[Dict] = None):
        """Ajoute un document à la base de connaissances"""
        try:
            # Division du contenu en chunks
            documents = self.text_splitter.create_documents([content], [metadata or {}])
            
            for i, doc in enumerate(documents):
                # Génération de l'embedding
                embedding = self.embedding_model.encode(doc.page_content).tolist()
                
                # Métadonnées enrichies
                doc_metadata = {
                    "source": source,
                    "chunk_index": i,
                    "total_chunks": len(documents),
                    **(metadata or {})
                }
                
                # Ajout à la collection
                self.knowledge_collection.add(
                    embeddings=[embedding],
                    documents=[doc.page_content],
                    metadatas=[doc_metadata],
                    ids=[f"{source}_chunk_{i}"]
                )
            
            logger.debug(f"Document ajouté à la base de connaissances: {source} ({len(documents)} chunks)")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du document: {e}")
    
    async def search_ui_components(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """Recherche des composants UI pertinents"""
        if not self.initialized:
            raise RuntimeError("Service RAG non initialisé")
        
        top_k = top_k or settings.rag_top_k
        
        try:
            # Génération de l'embedding de la requête
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Recherche dans la collection
            results = self.ui_components_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            # Formatage des résultats
            components = []
            if results['metadatas'] and results['metadatas'][0]:
                for metadata, distance in zip(results['metadatas'][0], results['distances'][0]):
                    if distance <= (1 - settings.rag_similarity_threshold):
                        # Désérialiser les données complètes du composant
                        try:
                            component_data = json.loads(metadata.get('data', '{}'))
                            component_data['relevance_score'] = 1 - distance
                            components.append(component_data)
                        except json.JSONDecodeError:
                            # Fallback vers les métadonnées simples
                            components.append({
                                **metadata,
                                'relevance_score': 1 - distance
                            })
            
            return components
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de composants UI: {e}")
            return []
    
    async def search_ui_layouts(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """Recherche des layouts UI pertinents"""
        if not self.initialized:
            raise RuntimeError("Service RAG non initialisé")
        
        top_k = top_k or settings.rag_top_k
        
        try:
            # Génération de l'embedding de la requête
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Recherche dans la collection
            results = self.layouts_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            # Formatage des résultats
            layouts = []
            if results['metadatas'] and results['metadatas'][0]:
                for metadata, distance in zip(results['metadatas'][0], results['distances'][0]):
                    if distance <= (1 - settings.rag_similarity_threshold):
                        # Désérialiser les données complètes du layout
                        try:
                            layout_data = json.loads(metadata.get('data', '{}'))
                            layout_data['relevance_score'] = 1 - distance
                            layouts.append(layout_data)
                        except json.JSONDecodeError:
                            # Fallback vers les métadonnées simples
                            layouts.append({
                                **metadata,
                                'relevance_score': 1 - distance
                            })
            
            return layouts
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de layouts UI: {e}")
            return []
    
    async def search_images(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """Recherche des images pertinentes dans le catalogue"""
        if not self.initialized:
            raise RuntimeError("Service RAG non initialisé")
        
        top_k = top_k or settings.rag_top_k
        
        try:
            # Génération de l'embedding de la requête
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Recherche dans la collection
            results = self.images_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            # Formatage des résultats
            images = []
            if results['metadatas'] and results['metadatas'][0]:
                for metadata, distance in zip(results['metadatas'][0], results['distances'][0]):
                    if distance <= (1 - settings.rag_similarity_threshold):
                        # Désérialiser les données complètes de l'image
                        try:
                            image_data = json.loads(metadata.get('data', '{}'))
                            image_data['relevance_score'] = 1 - distance
                            images.append(image_data)
                        except json.JSONDecodeError:
                            # Fallback vers les métadonnées simples
                            images.append({
                                **metadata,
                                'relevance_score': 1 - distance
                            })
            
            return images
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche d'images: {e}")
            return []
    
    async def search_knowledge(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """Recherche dans la base de connaissances"""
        if not self.initialized:
            raise RuntimeError("Service RAG non initialisé")
        
        top_k = top_k or settings.rag_top_k
        
        try:
            # Génération de l'embedding de la requête
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Recherche dans la collection
            results = self.knowledge_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            # Formatage des résultats
            knowledge_items = []
            if results['documents'] and results['documents'][0]:
                for doc, metadata, distance in zip(
                    results['documents'][0], 
                    results['metadatas'][0], 
                    results['distances'][0]
                ):
                    if distance <= (1 - settings.rag_similarity_threshold):
                        knowledge_items.append({
                            'content': doc,
                            'metadata': metadata,
                            'relevance_score': 1 - distance
                        })
            
            return knowledge_items
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche dans la base de connaissances: {e}")
            return []
    
    async def add_ui_component_runtime(self, component_data: Dict[str, Any]) -> bool:
        """Ajoute un composant UI à l'exécution"""
        try:
            await self._add_ui_component(component_data)
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du composant à l'exécution: {e}")
            return False
    
    async def add_knowledge_runtime(self, content: str, source: str, metadata: Optional[Dict] = None) -> bool:
        """Ajoute une connaissance à l'exécution"""
        try:
            await self._add_knowledge_document(content, source, metadata)
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de la connaissance à l'exécution: {e}")
            return False
    
    async def cleanup(self):
        """Nettoyage des ressources"""
        try:
            if self.chroma_client:
                # ChromaDB se ferme automatiquement
                pass
            
            self.initialized = False
            logger.info("Service RAG nettoyé")
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du service RAG: {e}")