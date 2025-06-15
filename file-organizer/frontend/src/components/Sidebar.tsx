
import { Home, MessageSquare, BookOpen, History, Cog } from "lucide-react";
import React from "react";
import clsx from "clsx";
import { Link } from "react-router-dom";

const navLinks = [
  { name: "Dashboard", icon: Home, href: "/" },
  { name: "Interaction Hub", icon: MessageSquare, href: "/interaction" },
  { name: "Hive Mind Explorer", icon: BookOpen, href: "/hive" },
  { name: "History", icon: History, href: "/history" },
  { name: "Settings", icon: Cog, href: "/settings" }
];

function SidebarLink({ name, icon: Icon, href, active }: { name: string, icon: any, href: string, active: boolean }) {
  return (
    <Link
      to={href}
      className={clsx(
        "flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 group",
        active
          ? "bg-blue-600/20 text-blue-300 font-semibold shadow-lg border border-blue-500/30"
          : "hover:bg-sidebar-accent/50 text-sidebar-foreground hover:text-white"
      )}
      aria-current={active ? "page" : undefined}
    >
      <Icon className={clsx("w-5 h-5 transition-colors", active ? "text-blue-400" : "group-hover:text-blue-300")} />
      <span className="font-medium">{name}</span>
    </Link>
  );
}

export function Sidebar({ activePath }: { activePath: string }) {
  return (
    <aside className="flex flex-col bg-gradient-to-b from-slate-800 to-slate-900 rounded-xl shadow-lg p-4 min-w-[250px] max-w-xs h-full font-medium select-none border-r border-slate-700">
      <div className="mb-6 flex flex-col gap-2 items-center">
        <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-blue-800 text-blue-100 rounded-xl flex items-center justify-center mb-2 shadow-lg">
          <BookOpen className="w-7 h-7" />
        </div>
        <div className="text-center">
          <h1 className="text-lg font-bold tracking-wide text-white">
            File Agent
          </h1>
          <p className="text-sm text-slate-400 font-normal">Control Center</p>
        </div>
      </div>
      <nav className="flex flex-col gap-2 flex-1">
        {navLinks.map(link => (
          <SidebarLink
            key={link.href}
            name={link.name}
            icon={link.icon}
            href={link.href}
            active={activePath === link.href}
          />
        ))}
      </nav>
      <div className="mt-auto pt-4 border-t border-slate-700">
        <div className="text-xs text-slate-500 text-center">
          AI Co-pilot Active
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
