"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

const navItems = [
  { label: "Orchestrations", href: "#", icon: "🧠" },
  { label: "Conversations", href: "#", icon: "💬" },
  { label: "Datasets", href: "#", icon: "📚" },
  { label: "Providers", href: "#", icon: "🔌" },
];

type AppShellProps = {
  children: React.ReactNode;
  rightPanel?: React.ReactNode;
  rightPanelCollapsed?: React.ReactNode;
  authSlot?: React.ReactNode;
  displayName?: string | null;
};

export default function AppShell({
  children,
  rightPanel,
  rightPanelCollapsed,
  authSlot,
  displayName,
}: AppShellProps) {
  const [sidebarExpanded, setSidebarExpanded] = useState(true);
  const [isDesktop, setIsDesktop] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      setIsDesktop(width >= 1024);
      if (width <= 1024) {
        setRightPanelOpen(false);
      }
      if (width <= 768) {
        setSidebarExpanded(false);
      } else {
        setSidebarExpanded(true);
      }
    };

    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const sidebarWidth = sidebarExpanded ? 280 : 80;
  const rightRailWidth = isDesktop ? (rightPanelOpen ? 360 : 80) : 0;
  const templateColumns = isDesktop
    ? `${sidebarWidth}px 1fr ${rightRailWidth}px`
    : `${sidebarWidth}px 1fr`;

  return (
    <div className="h-screen bg-bg text-text">
      <header className="flex items-center justify-between border-b border-border bg-panel px-4 py-3 shadow-sm md:hidden">
        <button
          type="button"
          className="focus-ring rounded-card border border-border bg-panelAlt px-3 py-2 text-lg"
          onClick={() => setMobileSidebarOpen(true)}
          aria-label="Open navigation"
        >
          ☰
        </button>
        <Link href="/" className="flex items-center gap-3">
          <Image
            src="/llmhive-logo-light.svg"
            alt="LLMHive"
            width={36}
            height={36}
            className="h-9 w-auto"
            priority
          />
          <span className="text-base font-semibold">LLMHive</span>
        </Link>
        <button
          type="button"
          className="focus-ring rounded-card border border-border bg-panelAlt px-3 py-2 text-sm text-textDim"
          onClick={() => setRightPanelOpen((open) => !open)}
        >
          {rightPanelOpen ? "Hide" : "Agents"}
        </button>
      </header>

      <div
        className="hidden h-full md:grid"
        style={{ gridTemplateColumns: templateColumns }}
      >
        <aside className="flex h-full flex-col border-r border-border bg-panel transition-all duration-200 ease-soft">
          <div className="flex h-16 items-center gap-3 border-b border-border px-4">
            <Link href="/" className="flex items-center gap-3">
              <Image
                src="/llmhive-logo-light.svg"
                alt="LLMHive"
                width={sidebarExpanded ? 40 : 32}
                height={sidebarExpanded ? 40 : 32}
                className={sidebarExpanded ? "h-10 w-auto" : "mx-auto h-8 w-auto"}
                priority
              />
              {sidebarExpanded && (
                <span className="text-lg font-semibold">LLMHive</span>
              )}
            </Link>
          </div>
          <nav className="flex-1 space-y-1 px-3 py-4">
            {navItems.map((item) => (
              <Link
                key={item.label}
                href={item.href}
                className="flex items-center gap-3 rounded-card px-3 py-2 text-sm text-text transition-colors duration-150 ease-soft hover:bg-panelAlt"
              >
                <span aria-hidden className="text-lg">
                  {item.icon}
                </span>
                {sidebarExpanded && <span>{item.label}</span>}
              </Link>
            ))}
          </nav>
          <div className="mt-auto space-y-3 px-3 pb-4">
            <div className="rounded-card border border-border bg-panelAlt px-3 py-2 text-xs text-textDim">
              {displayName ? `Workspace • ${displayName}` : "Workspace • Guest"}
            </div>
            <button
              type="button"
              onClick={() => setSidebarExpanded((expanded) => !expanded)}
              className="focus-ring flex w-full items-center justify-center gap-2 rounded-card border border-border bg-panelAlt px-3 py-2 text-sm font-semibold text-text transition-colors duration-150 ease-soft hover:bg-white"
            >
              {sidebarExpanded ? "Collapse" : "Expand"}
            </button>
            {authSlot}
          </div>
        </aside>

        <main className="overflow-y-auto bg-bg">
          <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-6 px-6 py-8 lg:px-10">
            {children}
          </div>
        </main>

        <aside className="hidden h-full border-l border-border bg-panel transition-all duration-200 ease-soft lg:flex" style={{ width: rightRailWidth }}>
          {rightPanelOpen ? (
            <div className="flex w-full flex-1 flex-col">
              <div className="flex items-center justify-between border-b border-border px-4 py-4">
                <span className="text-sm font-semibold text-text">Run • Agents</span>
                <button
                  type="button"
                  className="focus-ring rounded-card border border-border bg-panelAlt px-3 py-1 text-xs text-textDim"
                  onClick={() => setRightPanelOpen(false)}
                >
                  Collapse
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-4 scrollbar-thin">
                {rightPanel}
              </div>
            </div>
          ) : (
            <div className="flex h-full w-full flex-col items-center gap-4 px-3 py-6">
              <button
                type="button"
                className="focus-ring glass flex h-12 w-12 items-center justify-center rounded-card text-lg"
                onClick={() => setRightPanelOpen(true)}
                aria-label="Expand agents panel"
              >
                ☰
              </button>
              {rightPanelCollapsed}
            </div>
          )}
        </aside>
      </div>

      <main className="flex flex-1 overflow-y-auto md:hidden">
        <div className="mx-auto flex w-full max-w-[800px] flex-col gap-6 px-5 py-6">
          {children}
        </div>
      </main>

      <button
        type="button"
        className="fixed bottom-6 right-6 z-30 rounded-card border border-border bg-primary px-4 py-2 text-sm font-semibold text-white shadow-lg transition duration-150 ease-soft hover:bg-primaryLight md:hidden"
        onClick={() => setRightPanelOpen((open) => !open)}
      >
        {rightPanelOpen ? "Close Agents" : "Run • Agents"}
      </button>

      {mobileSidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/40 md:hidden">
          <aside className="absolute left-0 top-0 flex h-full w-[280px] flex-col gap-4 border-r border-border bg-panel p-4 shadow-lg">
            <div className="flex items-center justify-between">
              <Link href="/" className="flex items-center gap-3">
                <Image src="/llmhive-logo-light.svg" alt="LLMHive" width={32} height={32} className="h-8 w-auto" />
                <span className="text-base font-semibold">LLMHive</span>
              </Link>
              <button
                type="button"
                className="focus-ring rounded-card border border-border bg-panelAlt px-2 py-1 text-sm"
                onClick={() => setMobileSidebarOpen(false)}
                aria-label="Close navigation"
              >
                ✕
              </button>
            </div>
            <nav className="flex-1 space-y-2">
              {navItems.map((item) => (
                <Link
                  key={item.label}
                  href={item.href}
                  className="flex items-center gap-3 rounded-card px-3 py-2 text-sm text-text transition-colors duration-150 ease-soft hover:bg-panelAlt"
                >
                  <span aria-hidden>{item.icon}</span>
                  <span>{item.label}</span>
                </Link>
              ))}
            </nav>
            <div className="rounded-card border border-border bg-panelAlt px-3 py-2 text-xs text-textDim">
              {displayName ? `Workspace • ${displayName}` : "Workspace • Guest"}
            </div>
          </aside>
        </div>
      )}

      {rightPanelOpen && rightPanel && (
        <div className="fixed inset-0 z-40 flex items-end bg-black/30 px-4 pb-8 md:hidden" role="dialog" aria-modal="true">
          <aside className="glass w-full max-w-md rounded-card border border-border bg-panel p-5 shadow-lg">
            <div className="mb-4 flex items-center justify-between">
              <span className="text-base font-semibold text-text">Run • Agents</span>
              <button
                type="button"
                className="focus-ring rounded-card border border-border bg-panelAlt px-3 py-1 text-xs text-textDim"
                onClick={() => setRightPanelOpen(false)}
              >
                Close
              </button>
            </div>
            <div className="max-h-[60vh] overflow-y-auto pr-1 scrollbar-thin">{rightPanel}</div>
          </aside>
        </div>
      )}
    </div>
  );
}
