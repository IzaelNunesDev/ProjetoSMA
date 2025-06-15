
// src/pages/InteractionHub.tsx

import React, { useRef, useEffect } from "react";
import { ChatBubble } from "@/components/ui/ChatBubble";
import { CardSection } from "@/components/ui/CardSection";
import { ActionComposer } from "@/components/ui/ActionComposer";
import { useWebSocket } from "@/hooks/useWebSocket"; // <-- Importar o hook

// REMOVA OS DADOS ESTÁTICOS 'initialLog' e 'plan'

export default function InteractionHub() {
  const { messages, sendMessage } = useWebSocket();
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages.length]);

  const handleCommandSubmit = (data: { action: string; payload: Record<string, string> }) => {
    console.log("Sending command from InteractionHub:", data);
    const command = {
      action: data.action,
      ...data.payload,
    };
    sendMessage(command);
  };

  // Função para renderizar as mensagens do backend
  const renderMessage = (msg: any, index: number) => {
    switch(msg.type) {
      case 'log':
        return <div key={index} className={`text-xs font-mono px-2 py-1 ${msg.level === 'error' ? 'text-red-400' : msg.level === 'warning' ? 'text-yellow-400' : 'text-slate-400'}`}>{msg.message}</div>;
      case 'result':
      case 'query_result':
        return (
          <ChatBubble key={index} side="left" name="Agent" type="info">
            <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(msg.data, null, 2)}</pre>
          </ChatBubble>
        );
      case 'error':
        return <ChatBubble key={index} side="left" name="Agent" type="error">{msg.message}</ChatBubble>;
      default: // Mensagens do usuário adicionadas manualmente
        return <ChatBubble key={index} side="right" name="User">{msg.message}</ChatBubble>;
    }
  }

  return (
    <div className="flex flex-col h-full max-h-[calc(90vh-64px)]">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-2">Interaction Hub</h1>
        <p className="text-slate-400">Communicate with your AI assistant and monitor activities</p>
      </div>
      
      <div ref={containerRef} className="flex-1 overflow-y-auto rounded-xl bg-gradient-to-b from-slate-800/50 to-slate-900/50 border border-slate-600 p-6 mb-4 shadow-inner">
        {messages.map((msg, i) => renderMessage(msg, i))}
      </div>
      
      <div className="py-2">
        <ActionComposer onSubmit={handleCommandSubmit} />
      </div>
    </div>
  );
}
