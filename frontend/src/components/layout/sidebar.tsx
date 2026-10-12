import * as React from "react"
import { NavLink } from "react-router-dom"
import {
  Building2,
  ChevronLeft,
  ChevronRight,
  Database,
  LayoutDashboard,
  Settings,
  Sparkles,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

const navItems = [
  { to: "/", label: "Visão geral", icon: LayoutDashboard, end: true },
  { to: "/clients", label: "Clientes", icon: Building2, end: false },
  { to: "/knowledge-bases", label: "Bases de conhecimento", icon: Database, end: false },
  { to: "/settings", label: "Configurações", icon: Settings, end: false },
]

const STORAGE_KEY = "sidebar-collapsed"

export function Sidebar() {
  const [collapsed, setCollapsed] = React.useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === "1"
    } catch {
      return false
    }
  })

  React.useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0")
    } catch {
      // ignore
    }
  }, [collapsed])

  return (
    <aside
      className={cn(
        "relative hidden shrink-0 flex-col border-r border-border bg-surface/60 py-6 transition-[width] duration-200 md:flex",
        collapsed ? "w-16 px-2" : "w-64 px-4",
      )}
    >
      <button
        type="button"
        onClick={() => setCollapsed((v) => !v)}
        aria-label={collapsed ? "Expandir painel administrativo" : "Recolher painel administrativo"}
        className="absolute -right-3 top-8 z-20 flex size-6 items-center justify-center rounded-full border border-border bg-surface-2 text-muted shadow-sm transition-colors hover:text-foreground hover:bg-surface"
      >
        {collapsed ? <ChevronRight className="size-3.5" /> : <ChevronLeft className="size-3.5" />}
      </button>

      <div className={cn("mb-8 flex items-center gap-2 px-2", collapsed && "justify-center px-0")}>
        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-purple-500 to-electric-500 shadow-glow-purple">
          <Sparkles className="size-5 text-white" />
        </div>
        {!collapsed && (
          <div>
            <p className="text-sm font-semibold leading-tight text-foreground">RAG LGPD</p>
            <p className="text-xs text-muted">Painel administrativo</p>
          </div>
        )}
      </div>

      <nav className="flex flex-1 flex-col gap-1">
        {navItems.map((item) =>
          collapsed ? (
            <Tooltip key={item.to} delayDuration={200}>
              <TooltipTrigger asChild>
                <NavLink
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center justify-center rounded-lg px-3 py-2 text-sm font-medium text-muted transition-colors hover:bg-surface-2 hover:text-foreground",
                      isActive &&
                        "bg-purple-500/15 text-purple-300 shadow-[inset_0_0_0_1px_rgba(139,61,255,0.35)]",
                    )
                  }
                >
                  <item.icon className="size-4" />
                </NavLink>
              </TooltipTrigger>
              <TooltipContent side="right">{item.label}</TooltipContent>
            </Tooltip>
          ) : (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted transition-colors hover:bg-surface-2 hover:text-foreground",
                  isActive &&
                    "bg-purple-500/15 text-purple-300 shadow-[inset_0_0_0_1px_rgba(139,61,255,0.35)]",
                )
              }
            >
              <item.icon className="size-4" />
              {item.label}
            </NavLink>
          ),
        )}
      </nav>
    </aside>
  )
}
