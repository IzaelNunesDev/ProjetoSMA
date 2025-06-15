
// src/pages/InteractionHub.tsx

import React, { useRef, useEffect } from "react";
import { ChatBubble } from "@/components/ui/ChatBubble";
import { CardSection } from "@/components/ui/CardSection";
import { ActionComposer } from "@/components/ui/ActionComposer";
import { useWebSocket } from "@/hooks/useWebSocket"; // <-- Importar o hook

// REMOVA OS DADOS ESTÁTICOS 'initialLog' e 'plan'

export default function InteractionHub() {
  const { messages, sendMessage } = useWebSocket(); // <-- Usar o contexto
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages.length]);

  // Função para lidar com o envio de comandos do ActionComposer
  function handleComposer({ action, directory, goal, query }: { action: string, directory?: string, goal?: string, query?: string }) {
    let payload: any = { action };
    let userMessage = "";

    if (action === 'organize') {
        payload = { ...payload, directory, goal };
        userMessage = `Organizar: "${directory}" com o objetivo: "${goal}"`;
    } else if (action === 'index') {
        payload = { ...payload, directory };
        userMessage = `Indexar: "${directory}"`;
    } else if (action === 'query') {
        payload = { ...payload, query };
        userMessage = `Consultar: "${query}"`;
    }
    // Adicione a lógica para 'maintenance' e 'start_watching' aqui
    
    // Envia a mensagem para o backend
    sendMessage(payload);
  }

  // Novo componente para o ActionComposer que lida com múltiplos inputs
  const DynamicActionComposer = () => {
      const [action, setAction] = React.useState('organize');
      const [directory, setDirectory] = React.useState('');
      const [goal, setGoal] = React.useState('');
      const [query, setQuery] = React.useState('');

      const handleSubmit = (e: React.FormEvent) => {
          e.preventDefault();
          handleComposer({ action, directory, goal, query });
      }

      return (
          <form onSubmit={handleSubmit} className="bg-gradient-to-r from-slate-800 to-slate-700 rounded-xl p-4 shadow-lg border border-slate-600 space-y-3">
              <select onChange={(e) => setAction(e.target.value)} value={action} className="rounded-lg bg-slate-700 border border-slate-600 px-3 py-2 text-sm text-white w-full">
                  <option value="organize">Organizar Arquivos</option>
                  <option value="index">Indexar Diretório</option>
                  <option value="query">Consultar Memória</option>
                  {/* Adicionar outras ações */}
              </select>

              {action === 'organize' && (
                  <>
                      <input placeholder="Caminho do diretório para organizar" value={directory} onChange={e => setDirectory(e.target.value)} className="w-full rounded-md border border-slate-600 bg-slate-700 px-3 py-2 text-sm text-white" />
                      <input placeholder="Objetivo (ex: por tipo, por projeto)" value={goal} onChange={e => setGoal(e.target.value)} className="w-full rounded-md border border-slate-600 bg-slate-700 px-3 py-2 text-sm text-white" />
                  </>
              )}
               {action === 'index' && (
                  <input placeholder="Caminho do diretório para indexar" value={directory} onChange={e => setDirectory(e.target.value)} className="w-full rounded-md border border-slate-600 bg-slate-700 px-3 py-2 text-sm text-white" />
              )}
               {action === 'query' && (
                  <input placeholder="Sua pergunta sobre os arquivos" value={query} onChange={e => setQuery(e.target.value)} className="w-full rounded-md border border-slate-600 bg-slate-700 px-3 py-2 text-sm text-white" />
              )}
              <button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">Executar</button>
          </form>
      )
  }

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
        {/* Mapeia as mensagens do WebSocket */}
        {messages.map((msg, i) => renderMessage(msg, i))}
        
        {/* A tabela do plano de ação pode ser preenchida por uma mensagem específica do backend no futuro */}
      </div>
      
      <div className="py-2">
        {/* Substituímos o ActionComposer estático pelo nosso novo componente dinâmico */}
        <DynamicActionComposer />
      </div>
    </div>
  );
}
