"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  Activity,
  BarChart3,
  Boxes,
  ChevronRight,
  DollarSign,
  LayoutDashboard,
  Menu,
  RefreshCw,
  Server,
  Shield,
  Sparkles,
  Zap,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { ScrollArea } from "@/components/ui/scroll-area"

const NAV_ITEMS = [
  {
    href: "/admin/dashboard",
    label: "Overview",
    icon: LayoutDashboard,
    description: "System health & KPIs",
  },
  {
    href: "/admin/providers",
    label: "Providers",
    icon: Server,
    description: "Connections & utilization",
  },
  {
    href: "/admin/models",
    label: "Model Intelligence",
    icon: Sparkles,
    description: "Rankings & new models",
  },
  {
    href: "/admin/business",
    label: "Business",
    icon: DollarSign,
    description: "Revenue & subscriptions",
  },
  {
    href: "/admin/benchmarks",
    label: "Benchmarks",
    icon: Zap,
    description: "Quality testing",
  },
  {
    href: "/admin/support",
    label: "Support",
    icon: Activity,
    description: "Tickets & incidents",
  },
]

function NavLink({
  href,
  label,
  icon: Icon,
  description,
  active,
  onClick,
}: {
  href: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  description: string
  active: boolean
  onClick?: () => void
}) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className={cn(
        "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all",
        active
          ? "bg-[var(--bronze)]/10 text-[var(--bronze)] border border-[var(--bronze)]/20 shadow-sm"
          : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
      )}
    >
      <div
        className={cn(
          "flex h-8 w-8 items-center justify-center rounded-md transition-colors",
          active ? "bg-[var(--bronze)]/15" : "bg-muted/50 group-hover:bg-muted"
        )}
      >
        <Icon className={cn("h-4 w-4", active && "text-[var(--bronze)]")} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-medium truncate">{label}</div>
        <div className="text-[11px] text-muted-foreground truncate">{description}</div>
      </div>
      {active && <ChevronRight className="h-4 w-4 shrink-0 opacity-60" />}
    </Link>
  )
}

function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname()

  return (
    <nav className="space-y-1 px-3 py-2">
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.href}
          {...item}
          active={pathname === item.href || pathname.startsWith(`${item.href}/`)}
          onClick={onNavigate}
        />
      ))}
    </nav>
  )
}

export function AdminShell({
  children,
  title,
  description,
  onRefresh,
  refreshing,
  actions,
}: {
  children: React.ReactNode
  title: string
  description?: string
  onRefresh?: () => void
  refreshing?: boolean
  actions?: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-background admin-console">
      {/* Ambient background */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -right-40 h-96 w-96 rounded-full bg-[var(--bronze)]/5 blur-3xl" />
        <div className="absolute top-1/2 -left-40 h-80 w-80 rounded-full bg-[var(--gold)]/5 blur-3xl" />
        <div
          className="absolute inset-0 opacity-[0.015] dark:opacity-[0.03]"
          style={{
            backgroundImage: `linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px)`,
            backgroundSize: "64px 64px",
          }}
        />
      </div>

      <div className="relative flex min-h-screen">
        {/* Desktop sidebar */}
        <aside className="hidden lg:flex w-64 flex-col border-r border-border/50 bg-card/30 backdrop-blur-xl">
          <div className="flex h-16 items-center gap-3 border-b border-border/50 px-4">
            <Link href="/" className="flex items-center gap-2.5">
              <img src="/logo.png" alt="LLMHive" className="h-8 w-8" />
              <div>
                <span className="font-display text-base font-bold text-[var(--bronze)]">LLMHive</span>
                <div className="text-[10px] uppercase tracking-widest text-muted-foreground">Command Center</div>
              </div>
            </Link>
          </div>

          <ScrollArea className="flex-1 py-4">
            <SidebarNav />
          </ScrollArea>

          <div className="border-t border-border/50 p-4">
            <div className="flex items-center gap-2 rounded-lg bg-muted/30 px-3 py-2">
              <Shield className="h-4 w-4 text-[var(--bronze)]" />
              <div className="text-xs">
                <div className="font-medium">Admin Console</div>
                <div className="text-muted-foreground">Enterprise access</div>
              </div>
            </div>
          </div>
        </aside>

        {/* Main content */}
        <div className="flex-1 flex flex-col min-w-0">
          <header className="sticky top-0 z-40 border-b border-border/50 bg-background/80 backdrop-blur-xl">
            <div className="flex h-16 items-center justify-between gap-4 px-4 lg:px-8">
              <div className="flex items-center gap-3 min-w-0">
                <Sheet>
                  <SheetTrigger asChild>
                    <Button variant="ghost" size="icon" className="lg:hidden shrink-0">
                      <Menu className="h-5 w-5" />
                    </Button>
                  </SheetTrigger>
                  <SheetContent side="left" className="w-72 p-0">
                    <SheetHeader className="border-b border-border/50 px-4 py-4">
                      <SheetTitle className="flex items-center gap-2">
                        <img src="/logo.png" alt="" className="h-6 w-6" />
                        <span className="font-display text-[var(--bronze)]">LLMHive Admin</span>
                      </SheetTitle>
                    </SheetHeader>
                    <SidebarNav />
                  </SheetContent>
                </Sheet>

                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h1 className="font-display text-xl font-bold truncate">{title}</h1>
                    <Badge variant="outline" className="hidden sm:flex text-[var(--bronze)] border-[var(--bronze)]/40 shrink-0">
                      <Boxes className="h-3 w-3 mr-1" />
                      Live
                    </Badge>
                  </div>
                  {description && (
                    <p className="text-sm text-muted-foreground truncate">{description}</p>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {actions}
                {onRefresh && (
                  <Button variant="outline" size="sm" onClick={onRefresh} disabled={refreshing}>
                    <RefreshCw className={cn("h-4 w-4 mr-2", refreshing && "animate-spin")} />
                    <span className="hidden sm:inline">Refresh</span>
                  </Button>
                )}
                <Button variant="ghost" size="sm" asChild className="hidden md:flex">
                  <Link href="/analytics">
                    <BarChart3 className="h-4 w-4 mr-2" />
                    Analytics
                  </Link>
                </Button>
              </div>
            </div>
          </header>

          <main className="flex-1 px-4 lg:px-8 py-6 lg:py-8">{children}</main>
        </div>
      </div>
    </div>
  )
}
