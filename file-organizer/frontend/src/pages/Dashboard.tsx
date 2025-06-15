
import React from "react";
import { CardSection } from "@/components/ui/CardSection";
import { Folder, Search, Activity, BookOpen, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useWebSocket } from "@/hooks/useWebSocket"; // <-- Importar

export default function Dashboard() {
  const { suggestions, approveSuggestion, declineSuggestion } = useWebSocket(); // <-- Usar o contexto

  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
        <p className="text-slate-400">Overview of your AI file management system</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* System Status */}
        <CardSection className="border border-slate-600">
          <div className="flex items-center gap-3 mb-4">
            <Activity className="w-6 h-6 text-green-400" />
            <h2 className="text-xl font-bold text-white">System Status</h2>
          </div>
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-green-300 font-semibold">Active & Monitoring</span>
            </div>
            <div className="text-sm text-slate-300">
              <span className="font-medium">Watching:</span> Downloads, Projects, Documents
            </div>
            <div className="text-xs text-slate-400">
              Last scan: 30 seconds ago
            </div>
          </div>
        </CardSection>

        {/* Quick Actions */}
        <CardSection className="border border-slate-600">
          <h2 className="text-xl font-bold mb-4 text-white">Quick Actions</h2>
          <div className="grid grid-cols-2 gap-3">
            <Button variant="outline" className="flex flex-col items-center gap-2 h-auto py-4 bg-slate-700/50 border-slate-600 hover:bg-slate-600">
              <Folder className="w-6 h-6" />
              <span className="text-sm">Organize</span>
            </Button>
            <Button variant="outline" className="flex flex-col items-center gap-2 h-auto py-4 bg-slate-700/50 border-slate-600 hover:bg-slate-600">
              <BookOpen className="w-6 h-6" />
              <span className="text-sm">Index</span>
            </Button>
            <Button variant="outline" className="flex flex-col items-center gap-2 h-auto py-4 bg-slate-700/50 border-slate-600 hover:bg-slate-600">
              <Search className="w-6 h-6" />
              <span className="text-sm">Query</span>
            </Button>
            <Button variant="outline" className="flex flex-col items-center gap-2 h-auto py-4 bg-slate-700/50 border-slate-600 hover:bg-slate-600">
              <MessageSquare className="w-6 h-6" />
              <span className="text-sm">Chat</span>
            </Button>
          </div>
        </CardSection>
      </div>

      {/* Proactive Suggestions (AGORA DINÂMICO) */}
      <CardSection className="border border-slate-600">
        <h2 className="text-xl font-bold mb-4 text-white">Proactive Suggestions</h2>
        <div className="space-y-3">
          {suggestions.length === 0 && (
            <p className="text-sm text-slate-400 text-center py-4">Nenhuma sugestão no momento. Monitore um diretório para começar!</p>
          )}
          {suggestions.map((s, idx) => (
            <div key={idx} className="rounded-lg bg-slate-700/50 border border-slate-600 flex items-center px-4 py-3">
              <div className="mr-4 p-2 bg-blue-600/20 rounded-lg">
                <Folder className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <div className="font-semibold text-blue-200 text-sm">File Organization</div>
                <div className="text-xs text-slate-400 mt-1">{s.reason}</div>
              </div>
              <div className="flex gap-2">
                <Button onClick={() => approveSuggestion(s)} size="sm" className="bg-green-600 hover:bg-green-700">Aprovar</Button>
                <Button onClick={() => declineSuggestion(s)} variant="outline" size="sm">Recusar</Button>
              </div>
            </div>
          ))}
        </div>
      </CardSection>

      {/* ... (Seção de Atividade Recente - pode ser populada pelo log de mensagens também) ... */}
    </div>
  );
}
