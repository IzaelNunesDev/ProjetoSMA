
import React from "react";

export function CardSection({ children, className = "" }: { children: React.ReactNode, className?: string }) {
  return (
    <div className={`bg-gradient-to-br from-slate-800/80 to-slate-900/80 backdrop-blur-sm rounded-xl shadow-lg p-6 ${className}`}>
      {children}
    </div>
  );
}
