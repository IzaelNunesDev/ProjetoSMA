
import React, { useState, useEffect } from "react";
import { CardSection } from "@/components/ui/CardSection";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Folder, FileText, Search, Trash2, Calendar, Info } from "lucide-react";
import { useWebSocket } from "@/hooks/useWebSocket";

interface HistoryItem {
  id: string;
  action: string;
  path: string;
  timestamp: string;
  status: string;
  details: string;
  agent: string;
}

export default function History() {
  const { messages } = useWebSocket();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedFilter, setSelectedFilter] = useState("all");

  useEffect(() => {
    const processedHistory = messages
      .filter(msg => msg.type === 'result' || msg.type === 'log')
      .map((msg, index) => {
        const timestamp = new Date(msg.timestamp).toLocaleString('pt-BR');
        let item: HistoryItem | null = null;

        if (msg.type === 'result') {
          item = {
            id: `msg-result-${msg.timestamp}-${index}`,
            action: msg.data.action || 'Task Result',
            path: msg.data.path || 'Not specified',
            timestamp,
            status: msg.data.status || 'Completed',
            details: msg.data.details || JSON.stringify(msg.data),
            agent: msg.data.agent || 'System',
          };
        } else if (msg.type === 'log' && msg.data.message) {
          item = {
            id: `msg-log-${msg.timestamp}-${index}`,
            action: `Log: ${msg.data.agent || 'System'}`,
            path: 'Operation Step',
            timestamp,
            status: 'Info',
            details: msg.data.message,
            agent: msg.data.agent || 'System',
          };
        }
        return item;
      })
      .filter((item): item is HistoryItem => item !== null)
      .reverse(); // Show newest first

    setHistory(processedHistory);
  }, [messages]);

  const filteredHistory = history.filter(item => {
    const matchesSearch = item.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         item.path.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         item.details.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesFilter = selectedFilter === "all" || 
                         (selectedFilter === "completed" && item.status === "Completed") ||
                         (selectedFilter === "failed" && item.status === "Failed") ||
                         (selectedFilter === "info" && item.status === "Info");
    
    return matchesSearch && matchesFilter;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Completed": return "bg-green-600/20 text-green-300";
      case "Failed": return "bg-red-600/20 text-red-300";
      case "Info": return "bg-sky-600/20 text-sky-300";
      default: return "bg-slate-600/20 text-slate-300";
    }
  };

  const getActionIcon = (action: string) => {
    const lowerCaseAction = action.toLowerCase();
    if (lowerCaseAction.includes("organize")) return <Folder className="w-4 h-4" />;
    if (lowerCaseAction.includes("index")) return <FileText className="w-4 h-4" />;
    if (lowerCaseAction.includes("query")) return <Search className="w-4 h-4" />;
    if (lowerCaseAction.includes("log")) return <Info className="w-4 h-4" />;
    return <Calendar className="w-4 h-4" />;
  };

  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-2">Operation History</h1>
        <p className="text-slate-400">Complete log of all file management operations</p>
      </div>

      {/* Search and Filter Controls */}
      <CardSection>
        <div className="flex gap-4 items-center">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
              <Input
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search operations..."
                className="pl-10 bg-slate-700 border-slate-600"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant={selectedFilter === "all" ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedFilter("all")}
              className="bg-slate-700 border-slate-600"
            >
              All
            </Button>
            <Button
              variant={selectedFilter === "completed" ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedFilter("completed")}
              className="bg-slate-700 border-slate-600"
            >
              Completed
            </Button>
            <Button
              variant={selectedFilter === "failed" ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedFilter("failed")}
              className="bg-slate-700 border-slate-600"
            >
              Failed
            </Button>
             <Button
              variant={selectedFilter === "info" ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedFilter("info")}
              className="bg-slate-700 border-slate-600"
            >
              Info
            </Button>
          </div>
        </div>
      </CardSection>

      {/* History List */}
      <CardSection>
        <div className="space-y-3">
          {filteredHistory.map((item) => (
            <div key={item.id} className="bg-slate-700/50 border border-slate-600 rounded-lg p-4 hover:bg-slate-600/50 transition-colors">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3 flex-1">
                  <div className="p-2 bg-blue-600/20 rounded-lg mt-1">
                    {getActionIcon(item.action)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-semibold text-white">{item.action}</h3>
                      <span className={`px-2 py-1 rounded text-xs ${getStatusColor(item.status)}`}>
                        {item.status}
                      </span>
                    </div>
                    <p className="text-sm text-slate-300 mb-1">{item.path}</p>
                    <p className="text-sm text-slate-400">{item.details}</p>
                    <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                      <span>Agent: {item.agent}</span>
                      <span>{item.timestamp}</span>
                    </div>
                  </div>
                </div>
                <Button variant="ghost" size="sm" className="text-slate-400 hover:text-red-400">
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>

        {filteredHistory.length === 0 && (
          <div className="text-center py-8 text-slate-400">
            <Search className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No operations found matching your criteria</p>
          </div>
        )}
      </CardSection>
    </div>
  );
}
