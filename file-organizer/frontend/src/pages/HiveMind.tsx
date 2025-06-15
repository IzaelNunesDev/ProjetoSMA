
import React, { useState } from "react";
import { CardSection } from "@/components/ui/CardSection";
import { Tabs } from "@/components/ui/tabs";
import { PieChart, BarChart2, LineChart } from "lucide-react";
import { Card } from "@/components/ui/card";

// Tab simulation
const tabs = [
  { id: "feed", icon: <BarChart2 />, label: "Memory Feed" },
  { id: "analytics", icon: <PieChart />, label: "Analytics" },
  { id: "agent", icon: <LineChart />, label: "Connection Chart" }
];

export default function HiveMind() {
  const [tab, setTab] = useState("feed");

  return (
    <div>
      <div className="flex gap-2 mb-5">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-5 py-2 rounded-lg text-white bg-background/70 hover:bg-background/90 transition font-medium 
              ${tab === t.id ? "bg-blue-800 text-blue-100 shadow" : ""}`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>
      {tab === "feed" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2, 3].map(i => (
            <Card key={i} className="p-5 bg-sidebar-accent">
              <div className="text-md font-bold text-white mb-1">Memory {i}</div>
              <div className="text-xs text-gray-300">agent_source: suggest_agent</div>
              <div className="text-xs text-gray-400 mt-2">"Detected a pattern in files..."</div>
            </Card>
          ))}
        </div>
      )}
      {tab === "analytics" && (
        <CardSection>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <Card className="bg-background p-4">
              <div className="font-bold text-blue-200 mb-1">Actions by Agent</div>
              {/* Placeholder: Use Recharts or similar in next iteration */}
              <div className="h-28 flex items-center justify-center text-blue-400">[Pie Chart]</div>
            </Card>
            <Card className="bg-background p-4">
              <div className="font-bold text-blue-200 mb-1">Top Tags</div>
              <div className="h-28 flex items-center justify-center text-blue-400">[Bar Chart]</div>
            </Card>
            <Card className="bg-background p-4">
              <div className="font-bold text-blue-200 mb-1">Memory Growth</div>
              <div className="h-28 flex items-center justify-center text-blue-400">[Line Chart]</div>
            </Card>
          </div>
        </CardSection>
      )}
      {tab === "agent" && (
        <CardSection>
          <div className="h-60 flex items-center justify-center text-blue-300">
            [Agent Network Visualization Placeholder]
          </div>
        </CardSection>
      )}
    </div>
  );
}
