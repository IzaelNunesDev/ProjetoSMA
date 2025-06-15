// src/hooks/useWebSocket.tsx
import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';

// Tipos para as mensagens que esperamos do backend
interface LogMessage {
  type: 'log';
  level: 'info' | 'warning' | 'error';
  message: string;
}

interface Suggestion {
  action: "SUGGEST_MOVE";
  from: string;
  to: string;
  reason: string;
}

interface SuggestionMessage {
  type: 'suggestion';
  data: Suggestion;
}

interface ResultMessage {
    type: 'result' | 'query_result';
    data: any;
}

interface ErrorMessage {
    type: 'error';
    message: string;
}

// Unimos todos os tipos de mensagens que o backend pode enviar
type BackendMessage = LogMessage | SuggestionMessage | ResultMessage | ErrorMessage;

interface WebSocketContextType {
  isConnected: boolean;
  messages: any[]; // Vamos usar 'any' por enquanto para simplificar o log do InteractionHub
  suggestions: Suggestion[];
  sendMessage: (payload: object) => void;
  approveSuggestion: (suggestion: Suggestion) => void;
  declineSuggestion: (suggestion: Suggestion) => void;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<any[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);

  // Conexão com o backend
  useEffect(() => {
    // Endereço do seu backend FastAPI
    const ws = new WebSocket('ws://127.0.0.1:8000/ws');

    ws.onopen = () => {
      console.log('WebSocket Connected');
      setIsConnected(true);
      setMessages(prev => [...prev, { type: 'log', level: 'info', message: 'Conectado ao File Agent Co-pilot.' }]);
    };

    ws.onmessage = (event) => {
      const parsedMessage: BackendMessage = JSON.parse(event.data);
      console.log('Received from backend:', parsedMessage);

      // Atualiza o estado com base no tipo de mensagem
      if (parsedMessage.type === 'suggestion') {
        setSuggestions(prev => [...prev, parsedMessage.data]);
        // Adiciona um log para o usuário saber que chegou uma sugestão
        setMessages(prev => [...prev, { type: 'log', level: 'info', message: `✨ Nova sugestão recebida! Verifique o Dashboard.` }]);
      } else {
         // Para todos os outros tipos (log, result, error), adicionamos ao feed de mensagens principal
         setMessages(prev => [...prev, parsedMessage]);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket Disconnected');
      setIsConnected(false);
       setMessages(prev => [...prev, { type: 'log', level: 'error', message: 'Desconectado do servidor. Tentando reconectar...' }]);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket Error:', error);
        setMessages(prev => [...prev, { type: 'log', level: 'error', message: 'Erro na conexão WebSocket.' }]);
    }

    setSocket(ws);

    // Limpeza ao desmontar o componente
    return () => {
      ws.close();
    };
  }, []);

  const sendMessage = useCallback((payload: object) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(payload));
    } else {
      console.error('WebSocket is not connected.');
    }
  }, [socket]);

  const approveSuggestion = useCallback((suggestion: Suggestion) => {
    sendMessage({
        action: 'approve_suggestion',
        suggestion: suggestion,
    });
    // Remove a sugestão da lista após a ação
    setSuggestions(prev => prev.filter(s => s.from !== suggestion.from));
  }, [sendMessage]);

  const declineSuggestion = useCallback((suggestion: Suggestion) => {
    // Apenas remove da UI. O backend não precisa ser notificado, a menos que queira registrar a recusa.
    setSuggestions(prev => prev.filter(s => s.from !== suggestion.from));
    setMessages(prev => [...prev, { type: 'log', level: 'info', message: `Sugestão para '${suggestion.from}' recusada.` }]);
  }, []);


  const value = {
    isConnected,
    messages,
    suggestions,
    sendMessage,
    approveSuggestion,
    declineSuggestion,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};
