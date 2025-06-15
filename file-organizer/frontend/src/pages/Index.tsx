
import React from "react";
import Sidebar from "@/components/Sidebar";
import { Outlet, useLocation } from "react-router-dom";

export default function Index() {
  const location = useLocation();

  return (
    <div className="min-h-screen min-w-full flex bg-gradient-to-br from-slate-900 to-slate-800 items-center justify-center p-4">
      <div className="bg-sidebar rounded-3xl shadow-2xl p-0 flex w-[1200px] min-h-[700px] max-h-[90vh] overflow-hidden border border-slate-700">
        <Sidebar activePath={location.pathname} />
        <main className="w-full bg-gradient-to-br from-slate-900/95 to-slate-800/95 p-8 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
