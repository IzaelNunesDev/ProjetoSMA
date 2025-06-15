
import React from "react";
import clsx from "clsx";

export function ChatBubble({
  side,
  avatarUrl,
  name,
  children,
  type = "normal"
}: {
  side: "left" | "right",
  avatarUrl?: string,
  name?: string,
  children: React.ReactNode,
  type?: "normal" | "info" | "warning" | "error"
}) {
  let bubbleColor = "bg-slate-700 text-white border border-slate-600";
  if (type === "info") bubbleColor = "bg-blue-900/70 text-blue-100 border border-blue-700";
  if (type === "warning") bubbleColor = "bg-yellow-900/70 text-yellow-100 border border-yellow-700";
  if (type === "error") bubbleColor = "bg-red-900/70 text-red-100 border border-red-700";

  return (
    <div className={clsx("flex my-3", side === "left" ? "justify-start" : "justify-end")}>
      {side === "left" && (
        avatarUrl
          ? <img src={avatarUrl} className="w-9 h-9 rounded-full mr-3 border-2 border-slate-600" alt={name || "Agent"} />
          : <div className="w-9 h-9 bg-gradient-to-br from-blue-600 to-blue-800 rounded-full mr-3 flex items-center justify-center text-sm font-bold border-2 border-blue-500">A</div>
      )}
      <div className="max-w-md">
        {name && <div className="text-xs mb-1 px-2 text-slate-400 font-medium">{name}</div>}
        <div className={clsx(
          "px-4 py-3 rounded-2xl text-sm shadow-lg",
          bubbleColor,
          side === "right" ? "rounded-br-md" : "rounded-bl-md"
        )}>
          {children}
        </div>
      </div>
      {side === "right" && (
        avatarUrl
          ? <img src={avatarUrl} className="w-9 h-9 rounded-full ml-3 border-2 border-slate-600" alt={name || "User"} />
          : <div className="w-9 h-9 bg-gradient-to-br from-slate-600 to-slate-800 rounded-full ml-3 flex items-center justify-center text-sm font-bold border-2 border-slate-500">U</div>
      )}
    </div>
  );
}
