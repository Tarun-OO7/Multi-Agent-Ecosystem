import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import {
  LayoutDashboard, UploadCloud, ShieldCheck, FileSearch, Users, LogOut, Activity, ScrollText,
} from "lucide-react";

const NAV = [
  { to: "/dashboard", label: "Command Center", icon: LayoutDashboard, role: "viewer" },
  { to: "/upload", label: "Ingest Data", icon: UploadCloud, role: "auditor" },
  { to: "/audits", label: "Audits", icon: FileSearch, role: "viewer" },
  { to: "/agents", label: "Agent Roster", icon: Activity, role: "viewer" },
  { to: "/admin/users", label: "User Management", icon: Users, role: "admin" },
  { to: "/admin/logs", label: "Audit Trail", icon: ScrollText, role: "admin" },
];

const ROLE_RANK = { admin: 3, auditor: 2, viewer: 1 };

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  const handleLogout = () => {
    logout();
    nav("/login");
  };

  const allowed = (role) => (user ? ROLE_RANK[user.role] >= ROLE_RANK[role] : false);

  return (
    <div className="min-h-screen bg-background flex" data-testid="app-layout">
      {/* Sidebar */}
      <aside
        className="w-64 shrink-0 bg-[#0A0A0A] text-white flex flex-col border-r border-black"
        data-testid="sidebar"
      >
        <div className="px-6 pt-8 pb-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-primary flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-white" strokeWidth={2.5} />
            </div>
            <div>
              <div className="font-heading font-black text-lg leading-none">SentinelAI</div>
              <div className="text-[10px] tracking-overline uppercase text-white/50 mt-1">
                Audit Intelligence
              </div>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-6 space-y-1">
          {NAV.filter((n) => allowed(n.role)).map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                data-testid={`nav-${item.to.replace(/\//g, "-")}`}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-primary text-white"
                      : "text-white/70 hover:text-white hover:bg-white/5"
                  }`
                }
              >
                <Icon className="w-4 h-4" strokeWidth={2} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="px-4 py-4 border-t border-white/10">
          <div className="text-[10px] tracking-overline uppercase text-white/40 mb-2">
            Logged in as
          </div>
          <div className="flex items-center justify-between gap-2" data-testid="user-info">
            <div className="min-w-0">
              <div className="text-sm font-semibold truncate">{user?.full_name}</div>
              <div className="text-[11px] text-white/50 truncate font-mono">{user?.email}</div>
              <div className="text-[10px] uppercase tracking-overline mt-1 text-primary font-semibold">
                {user?.role}
              </div>
            </div>
            <button
              onClick={handleLogout}
              data-testid="logout-btn"
              className="p-2 hover:bg-white/10 transition-colors"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-x-hidden">
        <div className="px-10 py-8 max-w-[1500px]">{children}</div>
      </main>
    </div>
  );
}
