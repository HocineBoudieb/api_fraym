// Exemple de client Next.js pour utiliser l'API de sessions IntentLayer

// Configuration de l'API
const API_BASE_URL = 'http://localhost:8000/api/v1';

// Service de gestion des sessions
class IntentLayerClient {
  constructor(userId) {
    this.userId = userId;
    this.sessionId = null;
    this.baseUrl = API_BASE_URL;
  }

  // Créer une nouvelle session
  async createSession(userData = {}) {
    try {
      const response = await fetch(`${this.baseUrl}/sessions/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: this.userId,
          user_data: userData,
          context: {
            platform: 'nextjs',
            timestamp: new Date().toISOString()
          }
        })
      });

      const data = await response.json();
      
      if (data.success && data.session_info) {
        this.sessionId = data.session_info.session_id;
        console.log('Session créée:', this.sessionId);
        return data.session_info;
      } else {
        throw new Error(data.message || 'Erreur lors de la création de session');
      }
    } catch (error) {
      console.error('Erreur création session:', error);
      throw error;
    }
  }

  // Envoyer un message de chat
  async sendMessage(message, inputType = 'text') {
    if (!this.sessionId) {
      throw new Error('Aucune session active. Créez une session d\'abord.');
    }

    try {
      const response = await fetch(`${this.baseUrl}/sessions/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: this.sessionId,
          message: message,
          input_type: inputType,
          context: {
            timestamp: new Date().toISOString()
          }
        })
      });

      const data = await response.json();
      
      if (data.success) {
        return {
          text: data.response_text,
          audio: data.response_audio,
          components: data.ui_components,
          analysis: data.nlp_analysis,
          session: data.session_info
        };
      } else {
        throw new Error(data.message || 'Erreur lors du traitement du message');
      }
    } catch (error) {
      console.error('Erreur envoi message:', error);
      throw error;
    }
  }

  // Récupérer les informations de session
  async getSessionInfo() {
    if (!this.sessionId) {
      return null;
    }

    try {
      const response = await fetch(`${this.baseUrl}/sessions/info/${this.sessionId}`);
      const data = await response.json();
      
      if (data.success) {
        return data.session_info;
      }
      return null;
    } catch (error) {
      console.error('Erreur récupération session:', error);
      return null;
    }
  }

  // Supprimer la session
  async deleteSession() {
    if (!this.sessionId) {
      return true;
    }

    try {
      const response = await fetch(`${this.baseUrl}/sessions/delete/${this.sessionId}`, {
        method: 'DELETE'
      });
      
      const data = await response.json();
      
      if (data.success) {
        this.sessionId = null;
        return true;
      }
      return false;
    } catch (error) {
      console.error('Erreur suppression session:', error);
      return false;
    }
  }

  // Jouer l'audio de réponse
  playAudio(audioUrl) {
    if (!audioUrl) return;
    
    const fullUrl = audioUrl.startsWith('http') ? audioUrl : `http://localhost:8000${audioUrl}`;
    const audio = new Audio(fullUrl);
    audio.play().catch(error => {
      console.error('Erreur lecture audio:', error);
    });
  }
}

// Hook React pour utiliser IntentLayer
export function useIntentLayer(userId) {
  const [client, setClient] = useState(null);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (userId) {
      const newClient = new IntentLayerClient(userId);
      setClient(newClient);
    }
  }, [userId]);

  const createSession = async (userData = {}) => {
    if (!client) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const sessionInfo = await client.createSession(userData);
      setSession(sessionInfo);
      return sessionInfo;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async (message, inputType = 'text') => {
    if (!client) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await client.sendMessage(message, inputType);
      setSession(response.session);
      return response;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const deleteSession = async () => {
    if (!client) return;
    
    try {
      await client.deleteSession();
      setSession(null);
    } catch (err) {
      setError(err.message);
    }
  };

  return {
    client,
    session,
    loading,
    error,
    createSession,
    sendMessage,
    deleteSession,
    playAudio: client?.playAudio.bind(client)
  };
}

// Composant React d'exemple
export function ChatInterface({ userId }) {
  const {
    session,
    loading,
    error,
    createSession,
    sendMessage,
    deleteSession,
    playAudio
  } = useIntentLayer(userId);
  
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([]);
  const [components, setComponents] = useState([]);

  useEffect(() => {
    // Créer une session au montage du composant
    if (userId && !session) {
      createSession({
        preferences: {
          language: 'fr',
          theme: 'default'
        }
      });
    }
  }, [userId, session, createSession]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!message.trim() || loading) return;

    const userMessage = message;
    setMessage('');
    
    // Ajouter le message utilisateur
    setMessages(prev => [...prev, {
      type: 'user',
      content: userMessage,
      timestamp: new Date()
    }]);

    try {
      const response = await sendMessage(userMessage);
      
      // Ajouter la réponse
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: response.text,
        audio: response.audio,
        timestamp: new Date()
      }]);
      
      // Mettre à jour les composants UI
      if (response.components) {
        setComponents(response.components);
      }
      
      // Jouer l'audio si disponible
      if (response.audio) {
        playAudio(response.audio);
      }
      
    } catch (err) {
      setMessages(prev => [...prev, {
        type: 'error',
        content: `Erreur: ${err.message}`,
        timestamp: new Date()
      }]);
    }
  };

  if (!session && !loading) {
    return (
      <div className="p-4">
        <p>Connexion en cours...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto">
      {/* En-tête */}
      <div className="bg-blue-600 text-white p-4">
        <h1 className="text-xl font-bold">IntentLayer Chat</h1>
        {session && (
          <p className="text-sm opacity-75">
            Session: {session.session_id.slice(0, 8)}... | 
            Interactions: {session.interaction_count}
          </p>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${
              msg.type === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                msg.type === 'user'
                  ? 'bg-blue-500 text-white'
                  : msg.type === 'error'
                  ? 'bg-red-500 text-white'
                  : 'bg-gray-200 text-gray-800'
              }`}
            >
              <p>{msg.content}</p>
              {msg.audio && (
                <button
                  onClick={() => playAudio(msg.audio)}
                  className="mt-2 text-xs underline"
                >
                  🔊 Écouter
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Composants UI générés */}
      {components.length > 0 && (
        <div className="border-t p-4 bg-gray-50">
          <h3 className="font-semibold mb-2">Composants suggérés:</h3>
          <div className="space-y-2">
            {components.map((comp, index) => (
              <div key={index} className="p-2 bg-white rounded border">
                <span className="font-medium">{comp.type}</span>
                {comp.props && (
                  <pre className="text-xs mt-1 text-gray-600">
                    {JSON.stringify(comp.props, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Formulaire de saisie */}
      <form onSubmit={handleSendMessage} className="border-t p-4">
        <div className="flex space-x-2">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Tapez votre message..."
            className="flex-1 border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !message.trim()}
            className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 disabled:opacity-50"
          >
            {loading ? 'Envoi...' : 'Envoyer'}
          </button>
        </div>
        {error && (
          <p className="text-red-500 text-sm mt-2">{error}</p>
        )}
      </form>
    </div>
  );
}

export default IntentLayerClient;