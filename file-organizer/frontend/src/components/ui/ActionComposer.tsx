
import React, { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { List, BookOpen, Search, Cog, Send } from "lucide-react";

const actions = [
  { value: "organize", label: "Organize", icon: List },
  { value: "index", label: "Index", icon: BookOpen },
  { value: "query", label: "Query", icon: Search },
  { value: "maintenance", label: "Maintenance", icon: Cog }
];

export function ActionComposer({ onSubmit }: { onSubmit: (selection: any) => void }) {
  const [selected, setSelected] = useState(actions[0].value);
  const [input, setInput] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (input.trim()) {
      onSubmit({ action: selected, input });
      setInput("");
    }
  }

  const selectedAction = actions.find(a => a.value === selected);

  return (
    <form className="bg-gradient-to-r from-slate-800 to-slate-700 rounded-xl p-4 shadow-lg border border-slate-600" onSubmit={handleSubmit}>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <div className="p-2 bg-blue-600/20 rounded-lg">
            {selectedAction && <selectedAction.icon className="w-4 h-4 text-blue-300" />}
          </div>
          <select
            className="rounded-lg bg-slate-700 border border-slate-600 px-3 py-2 text-sm text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            value={selected}
            onChange={e => setSelected(e.target.value)}
          >
            {actions.map(a => (
              <option key={a.value} value={a.value}>{a.label}</option>
            ))}
          </select>
        </div>
        <Input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="For example: /downloads group by type"
          className="flex-1 bg-slate-700 border-slate-600 text-white placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <Button 
          type="submit" 
          className="px-6 bg-blue-600 hover:bg-blue-700 flex items-center gap-2"
          disabled={!input.trim()}
        >
          <Send className="w-4 h-4" />
          Start
        </Button>
      </div>
    </form>
  );
}
