# Système de Sessions IntentLayer

Ce document explique comment utiliser le système de sessions pour connecter votre application Next.js avec le serveur IA IntentLayer.

## Vue d'ensemble

Le système de sessions permet à chaque utilisateur de votre site Next.js de :
- Créer une session unique sur le serveur IA
- Poser des questions via l'API
- Recevoir des réponses vocales et des composants UI sélectionnés
- Maintenir un contexte de conversation

## Architecture

```
Next.js App → API Sessions → ServeurIA
     ↓              ↓           ↓
  Utilisateur → Session ID → Contexte + Mémoire
     ↓              ↓           ↓
  Question → Chat Endpoint → NLP + RAG + TTS
     ↓              ↓           ↓
  Réponse ← Audio + UI ← Composants générés
```

## Endpoints API

### 1. Créer une session
```http
POST /api/v1/sessions/create
Content-Type: application/json

{
  "user_id": "user123",
  "user_data": {
    "name": "John Doe",
    "preferences": {
      "language": "fr",
      "theme": "dark"
    }
  },
  "context": {
    "platform": "nextjs",
    "version": "1.0"
  }
}
```

**Réponse :**
```json
{
  "success": true,
  "message": "Session créée avec succès",
  "session_info": {
    "session_id": "sess_abc123",
    "user_id": "user123",
    "created_at": "2024-01-15T10:30:00Z",
    "last_activity": "2024-01-15T10:30:00Z",
    "interaction_count": 0,
    "is_active": true
  }
}
```

### 2. Chat avec la session
```http
POST /api/v1/sessions/chat
Content-Type: application/json

{
  "session_id": "sess_abc123",
  "message": "Créer un formulaire de contact",
  "input_type": "text",
  "context": {
    "page": "/contact",
    "timestamp": "2024-01-15T10:35:00Z"
  }
}
```

**Réponse :**
```json
{
  "success": true,
  "response_text": "Je vais créer un formulaire de contact pour vous...",
  "response_audio": "/audio/response_abc123.wav",
  "ui_components": [
    {
      "type": "form",
      "props": {
        "fields": [
          {"name": "name", "type": "text", "label": "Nom"},
          {"name": "email", "type": "email", "label": "Email"},
          {"name": "message", "type": "textarea", "label": "Message"}
        ]
      }
    }
  ],
  "nlp_analysis": {
    "intent": "create_form",
    "entities": [{"type": "form_type", "value": "contact"}],
    "confidence": 0.95
  },
  "session_info": {
    "session_id": "sess_abc123",
    "interaction_count": 1,
    "last_activity": "2024-01-15T10:35:00Z"
  }
}
```

### 3. Autres endpoints

- `GET /api/v1/sessions/info/{session_id}` - Informations de session
- `DELETE /api/v1/sessions/delete/{session_id}` - Supprimer une session
- `GET /api/v1/sessions/list/{user_id}` - Lister les sessions d'un utilisateur

## Intégration Next.js

### 1. Installation

Copiez le fichier `examples/nextjs-client.js` dans votre projet Next.js.

### 2. Configuration

```javascript
// config/intentlayer.js
export const INTENTLAYER_CONFIG = {
  apiUrl: process.env.NEXT_PUBLIC_INTENTLAYER_API || 'http://localhost:8000/api/v1',
  audioBaseUrl: process.env.NEXT_PUBLIC_INTENTLAYER_AUDIO || 'http://localhost:8000'
};
```

### 3. Utilisation basique

```javascript
import { useIntentLayer } from '../lib/intentlayer-client';

function ChatPage() {
  const userId = 'user123'; // Récupéré de votre système d'auth
  const {
    session,
    loading,
    error,
    createSession,
    sendMessage,
    playAudio
  } = useIntentLayer(userId);

  const handleMessage = async (message) => {
    try {
      const response = await sendMessage(message);
      
      // Jouer l'audio
      if (response.audio) {
        playAudio(response.audio);
      }
      
      // Utiliser les composants UI
      if (response.components) {
        setUIComponents(response.components);
      }
      
    } catch (error) {
      console.error('Erreur:', error);
    }
  };

  return (
    <div>
      {/* Votre interface de chat */}
    </div>
  );
}
```

### 4. Gestion des composants UI

```javascript
function UIComponentRenderer({ components }) {
  return (
    <div className="ui-components">
      {components.map((component, index) => {
        switch (component.type) {
          case 'form':
            return <DynamicForm key={index} {...component.props} />;
          case 'button':
            return <DynamicButton key={index} {...component.props} />;
          case 'card':
            return <DynamicCard key={index} {...component.props} />;
          default:
            return <div key={index}>Composant non supporté: {component.type}</div>;
        }
      })}
    </div>
  );
}
```

## Fonctionnalités

### 1. Gestion automatique des sessions
- Création automatique lors de la première connexion
- Nettoyage automatique des sessions expirées
- Limite du nombre de sessions par utilisateur

### 2. Réponses vocales
- Génération automatique d'audio pour chaque réponse
- Support de différentes voix selon la langue
- Nettoyage automatique des fichiers audio anciens

### 3. Composants UI dynamiques
- Génération de composants basée sur l'intention
- Props configurables pour chaque composant
- Support de layouts complexes

### 4. Contexte et mémoire
- Maintien du contexte de conversation
- Stockage des interactions utilisateur
- Enrichissement avec la base de connaissances RAG

## Configuration du serveur

### Variables d'environnement

```bash
# .env
OPENAI_API_KEY=your_openai_key
MISTRAL_API_KEY=your_mistral_key
OLLAMA_BASE_URL=http://localhost:11434

# Chemins de données
DATA_PATH=./data
MEMORY_PATH=./data/memory
RAG_DATA_PATH=./data/rag

# Configuration serveur
API_HOST=0.0.0.0
API_PORT=8000

# Base de données vectorielle
VECTOR_DB_TYPE=chroma
VECTOR_DB_PATH=./data/vectordb
```

### Démarrage du serveur

```bash
# Installation des dépendances
pip install -r requirements.txt

# Démarrage du serveur
python -m uvicorn src.intentlayer_aiserver.main:app --reload --host 0.0.0.0 --port 8000
```

## Exemples d'utilisation

### 1. Création de formulaire
```
Utilisateur: "Je veux créer un formulaire d'inscription"
IA: Génère un composant form avec les champs appropriés
Audio: "J'ai créé un formulaire d'inscription avec les champs nom, email et mot de passe"
```

### 2. Interface de navigation
```
Utilisateur: "Ajoute un menu de navigation"
IA: Génère un composant navigation avec des liens
Audio: "Voici un menu de navigation avec les sections principales de votre site"
```

### 3. Dashboard
```
Utilisateur: "Crée un tableau de bord avec des statistiques"
IA: Génère des composants card, chart, et layout
Audio: "J'ai créé un tableau de bord avec vos métriques principales"
```

## Sécurité

- Validation des entrées utilisateur
- Limitation du taux de requêtes
- Nettoyage automatique des sessions
- Pas de stockage de données sensibles
- CORS configuré pour votre domaine

## Monitoring

- Logs détaillés des interactions
- Métriques de performance
- Suivi des erreurs
- Statistiques d'utilisation

## Support

Pour toute question ou problème :
1. Vérifiez les logs du serveur
2. Consultez la documentation API
3. Testez avec les exemples fournis