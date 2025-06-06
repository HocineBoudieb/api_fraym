# IntentLayer AI Server 🚀

Serveur IA modulaire et optimisé pour l'analyse de requêtes en langage naturel, l'extraction d'intentions et la génération d'interfaces utilisateur adaptées.

## 🎯 Fonctionnalités

- **Analyse NLP avancée** : Extraction d'entités, détection d'intentions, analyse de sentiment
- **Génération d'UI intelligente** : Création automatique d'interfaces JSON pour Next.js
- **Mémoire contextuelle** : Stockage et analyse des interactions utilisateur
- **RAG (Retrieval-Augmented Generation)** : Base de connaissances vectorielle pour composants UI et données métier
- **Multi-LLM** : Support OpenAI, Mistral, et Ollama
- **API REST complète** : Endpoints FastAPI avec documentation automatique

## 🏗️ Architecture

```
src/intentlayer_aiserver/
├── main.py                 # Point d'entrée FastAPI
├── core/
│   ├── config.py          # Configuration centralisée
│   └── __init__.py
├── models/
│   ├── schemas.py         # Modèles Pydantic
│   └── __init__.py
├── services/
│   ├── rag_service.py     # Service RAG vectoriel
│   ├── nlp_service.py     # Service d'analyse NLP
│   ├── ui_generator.py    # Service de génération d'UI
│   ├── memory_service.py  # Service de mémoire contextuelle
│   └── __init__.py
└── api/
    └── v1/
        ├── nlp.py         # Routes NLP
        ├── ui_generator.py # Routes génération UI
        ├── memory.py      # Routes mémoire
        └── __init__.py
```

## 🚀 Installation

### Prérequis

- Python 3.11+
- `uv` (gestionnaire de paquets)

### Installation avec uv

```bash
# Cloner le projet
git clone <repository-url>
cd intentlayer_aiserver

# Installer les dépendances
uv sync

# Copier et configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés API
```

### Configuration

1. **Clés API** : Ajoutez vos clés dans `.env`
   ```bash
   OPENAI_API_KEY=your_openai_api_key
   MISTRAL_API_KEY=your_mistral_api_key  # Optionnel
   ```

2. **Modèle spaCy** : Installez le modèle français
   ```bash
   python -m spacy download fr_core_news_sm
   ```

3. **Répertoires de données** : Créez les dossiers nécessaires
   ```bash
   mkdir -p data/{ui_components,knowledge,memory,vectordb}
   mkdir -p logs
   ```

## 🎮 Utilisation

### Démarrage du serveur

```bash
# Mode développement
uv run python src/intentlayer_aiserver/main.py

# Ou avec uvicorn directement
uv run uvicorn src.intentlayer_aiserver.main:app --reload --host 0.0.0.0 --port 8000
```

### Documentation API

Accédez à la documentation interactive :
- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

### Endpoints principaux

#### 🧠 Analyse NLP
```bash
# Analyse complète d'un texte
POST /api/v1/nlp/analyze
{
  "text": "Je voudrais réserver une table pour ce soir",
  "input_type": "text",
  "user_id": "user123",
  "context": {}
}
```

#### 🎨 Génération d'UI
```bash
# Génération d'interface basée sur l'analyse NLP
POST /api/v1/ui/generate
{
  "nlp_result": {
    "intent": "booking",
    "entities": [...],
    "confidence": 0.9
  },
  "user_preferences": {
    "theme": "modern",
    "complexity": "simple"
  }
}
```

#### 💾 Mémoire contextuelle
```bash
# Stockage d'une interaction
POST /api/v1/memory/store
{
  "user_id": "user123",
  "session_id": "session456",
  "interaction": {
    "type": "booking",
    "data": {...}
  }
}

# Récupération du contexte utilisateur
GET /api/v1/memory/context/user123?limit=10
```

## 🔧 Configuration avancée

### Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `OPENAI_API_KEY` | Clé API OpenAI | - |
| `OPENAI_MODEL` | Modèle OpenAI | `gpt-3.5-turbo` |
| `VECTOR_DB_TYPE` | Type de DB vectorielle | `chromadb` |
| `SPACY_MODEL` | Modèle spaCy | `fr_core_news_sm` |
| `RAG_CHUNK_SIZE` | Taille des chunks RAG | `1000` |
| `API_PORT` | Port du serveur | `8000` |

### Personnalisation des composants UI

Ajoutez vos composants dans `data/ui_components/` :

```json
{
  "name": "BookingForm",
  "type": "form",
  "description": "Formulaire de réservation avec sélection de date",
  "props": {
    "fields": ["date", "time", "guests"],
    "validation": true
  },
  "variants": ["simple", "advanced"],
  "category": "booking"
}
```

### Base de connaissances

Ajoutez vos documents dans `data/knowledge/` :

```markdown
# Services de Restauration

Nous proposons des services de restauration pour tous types d'événements.

## Réservations
- Réservation en ligne disponible
- Confirmation par email
- Modification jusqu'à 2h avant
```

## 🧪 Tests

```bash
# Lancer les tests
uv run pytest

# Tests avec couverture
uv run pytest --cov=src/intentlayer_aiserver

# Tests spécifiques
uv run pytest tests/test_nlp_service.py
```

## 📊 Monitoring

### Health Checks

```bash
# Santé générale
GET /health

# Santé des services spécifiques
GET /api/v1/nlp/health
GET /api/v1/ui/health
GET /api/v1/memory/health
```

### Métriques

```bash
# Statistiques de mémoire
GET /api/v1/memory/stats

# Modèles disponibles
GET /api/v1/nlp/models

# Templates d'UI
GET /api/v1/ui/templates
```

## 🚀 Déploiement

### Docker (Recommandé)

```dockerfile
FROM python:3.11-slim

# Installation d'uv
RUN pip install uv

# Copie du projet
COPY . /app
WORKDIR /app

# Installation des dépendances
RUN uv sync --frozen

# Installation du modèle spaCy
RUN python -m spacy download fr_core_news_sm

# Exposition du port
EXPOSE 8000

# Commande de démarrage
CMD ["uv", "run", "uvicorn", "src.intentlayer_aiserver.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production avec Gunicorn

```bash
# Installation de Gunicorn
uv add gunicorn

# Démarrage en production
uv run gunicorn src.intentlayer_aiserver.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

## 🔍 Dépannage

### Problèmes courants

1. **Erreur de modèle spaCy**
   ```bash
   python -m spacy download fr_core_news_sm
   ```

2. **Erreur de clé API OpenAI**
   - Vérifiez que `OPENAI_API_KEY` est définie dans `.env`
   - Vérifiez que la clé est valide sur platform.openai.com

3. **Erreur de base vectorielle**
   - Vérifiez que le dossier `data/vectordb` existe
   - Supprimez le dossier pour réinitialiser

### Logs

```bash
# Logs en temps réel
tail -f logs/intentlayer.log

# Logs avec niveau DEBUG
LOG_LEVEL=DEBUG uv run python src/intentlayer_aiserver/main.py
```

## 🤝 Contribution

1. Fork le projet
2. Créez une branche feature (`git checkout -b feature/amazing-feature`)
3. Committez vos changements (`git commit -m 'Add amazing feature'`)
4. Poussez vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrez une Pull Request

### Standards de code

```bash
# Formatage avec Black
uv run black src/

# Linting avec Flake8
uv run flake8 src/

# Type checking avec MyPy
uv run mypy src/
```

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🙏 Remerciements

- [FastAPI](https://fastapi.tiangolo.com/) pour le framework web
- [LangChain](https://langchain.com/) pour l'orchestration LLM
- [spaCy](https://spacy.io/) pour le traitement NLP
- [ChromaDB](https://www.trychroma.com/) pour la base vectorielle
- [OpenAI](https://openai.com/) pour les modèles de langage

---

**IntentLayer AI Server** - Transformez vos intentions en interfaces intelligentes 🎯✨