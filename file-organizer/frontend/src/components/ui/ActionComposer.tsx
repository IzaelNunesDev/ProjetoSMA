
import React, { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { List, BookOpen, Search, Send, Folder, Target, HelpCircle } from "lucide-react";

// Define a estrutura para cada campo de input
interface ActionField {
  name: 'directory' | 'goal' | 'query';
  label: string;
  placeholder: string;
  icon: React.ElementType;
}

// Define a estrutura para cada ação
interface Action {
  value: string;
  label: string;
  icon: React.ElementType;
  fields: ActionField[];
}

const actions: Action[] = [
  {
    value: "organize",
    label: "Organize Directory",
    icon: List,
    fields: [
      { name: "directory", label: "Directory Path", placeholder: "e.g., C:\\Users\\YourUser\\Downloads", icon: Folder },
      { name: "goal", label: "Organization Goal", placeholder: "e.g., Group files by extension", icon: Target },
    ]
  },
  {
    value: "index",
    label: "Index Directory",
    icon: BookOpen,
    fields: [
      { name: "directory", label: "Directory to Index", placeholder: "e.g., C:\\Users\\YourUser\\Documents", icon: Folder },
    ]
  },
  {
    value: "query",
    label: "Query Memory",
    icon: Search,
    fields: [
      { name: "query", label: "Search Query", placeholder: "e.g., Find all reports from last month", icon: HelpCircle },
    ]
  },
];

// Define as props do componente
interface ActionComposerProps {
  onSubmit: (data: { action: string; payload: Record<string, string> }) => void;
}

export function ActionComposer({ onSubmit }: ActionComposerProps) {
  const [selectedActionValue, setSelectedActionValue] = useState(actions[0].value);
  const [formState, setFormState] = useState<Record<string, string>>({});

  const selectedAction = actions.find(a => a.value === selectedActionValue);

  // Limpa o formulário quando a ação muda
  useEffect(() => {
    setFormState({});
  }, [selectedActionValue]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormState(prevState => ({
      ...prevState,
      [name]: value
    }));
  };

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (selectedAction) {
      const payload = selectedAction.fields.reduce((acc, field) => {
        acc[field.name] = formState[field.name];
        return acc;
      }, {} as Record<string, string>);

      onSubmit({ action: selectedAction.value, payload });
      setFormState({}); // Limpa o formulário após o envio
    }
  }

  const isSubmitDisabled = !selectedAction || selectedAction.fields.some(field => !formState[field.name]?.trim());

  return (
    <form className="bg-gradient-to-r from-slate-800 to-slate-700 rounded-xl p-4 shadow-lg border border-slate-600 space-y-4" onSubmit={handleSubmit}>
      {/* Seletor de Ação */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-600/20 rounded-lg">
          {selectedAction && <selectedAction.icon className="w-5 h-5 text-blue-300" />}
        </div>
        <select
          className="w-full rounded-lg bg-slate-700 border border-slate-600 px-3 py-2 text-sm text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          value={selectedActionValue}
          onChange={e => setSelectedActionValue(e.target.value)}
        >
          {actions.map(a => (
            <option key={a.value} value={a.value}>{a.label}</option>
          ))}
        </select>
      </div>

      {/* Campos de Input Dinâmicos */}
      <div className="space-y-4">
        {selectedAction?.fields.map(field => (
          <div key={field.name} className="space-y-2">
            <Label htmlFor={field.name} className="text-sm font-medium text-slate-300 flex items-center gap-2">
              <field.icon className="w-4 h-4" />
              {field.label}
            </Label>
            <Input
              id={field.name}
              name={field.name}
              value={formState[field.name] || ""}
              onChange={handleInputChange}
              placeholder={field.placeholder}
              className="w-full bg-slate-700 border-slate-600 text-white placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        ))}
      </div>

      {/* Botão de Envio */}
      <div className="pt-2">
        <Button 
          type="submit" 
          className="w-full px-6 bg-blue-600 hover:bg-blue-700 flex items-center justify-center gap-2 disabled:bg-slate-600 disabled:cursor-not-allowed"
          disabled={isSubmitDisabled}
        >
          <Send className="w-4 h-4" />
          <span>Execute {selectedAction?.label}</span>
        </Button>
      </div>
    </form>
  );
}
