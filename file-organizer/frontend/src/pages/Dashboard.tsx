
import React from "react";
import { CardSection } from "@/components/ui/CardSection";
import { Folder, Activity, Terminal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useWebSocket } from "@/hooks/useWebSocket";
import { ActionComposer } from "@/components/ui/ActionComposer";

export default function Dashboard() {
  const { suggestions, approveSuggestion, declineSuggestion, sendMessage } = useWebSocket();

  const handleCommandSubmit = (data: { action: string; payload: Record<string, string> }) => {
    console.log("Sending command from Dashboard:", data);
    const command = {
      action: data.action,
      ...data.payload,
    };
    sendMessage(command);
  };

  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
        <p className="text-slate-400">Overview of your AI file management system</p>
      </div>

      {/* Command Center */}
      <CardSection className="border border-blue-500/50">
        <div className="flex items-center gap-3 mb-4">
          <Terminal className="w-6 h-6 text-blue-300" />
          <h2 className="text-xl font-bold text-white">Command Center</h2>
        </div>
        <ActionComposer onSubmit={handleCommandSubmit} />
      </CardSection>

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

        {/* Proactive Suggestions */}
        <CardSection className="border border-slate-600">
          <h2 className="text-xl font-bold mb-4 text-white">Proactive Suggestions</h2>
          <div className="space-y-3 max-h-48 overflow-y-auto pr-2">
            {suggestions.length === 0 && (
              <p className="text-sm text-slate-400 text-center py-4">No suggestions at the moment. Watch a directory to get started!</p>
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
                  <Button onClick={() => approveSuggestion(s)} size="sm" className="bg-green-600 hover:bg-green-700">Approve</Button>
                  <Button onClick={() => declineSuggestion(s)} variant="outline" size="sm">Decline</Button>
                </div>
              </div>
            ))}
          </div>
        </CardSection>
      </div>
    </div>
  );
}
