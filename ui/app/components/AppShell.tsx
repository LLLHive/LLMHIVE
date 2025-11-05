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

const quickActions = [
  "New Orchestration",
  "Import Dataset",
  "Connect Provider",
];

type AppShellProps = {
  children: React.ReactNode;
  rightPanel: React.ReactNode;
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
  const [navExpanded, setNavExpanded] = useState(true);
  const [rightExpanded, setRightExpanded] = useState(true);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      if (width < 1024) {
        setRightExpanded(false);
      }
      if (width < 768) {
        setNavExpanded(false);
      } else {
        setNavExpanded(true);
      }
    };

    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandPaletteOpen((open) => !open);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const navWidth = navExpanded ? 280 : 80;

  return (
    <div className="flex min-h-screen w-full flex-col bg-bg text-text">
      <header className="flex items-center justify-between border-b border-border/70 bg-panel/80 px-4 py-3 shadow-app1 md:hidden">
        <button
          className="focus-ring rounded-lg border border-border/80 bg-panel px-3 py-2 text-sm"
          onClick={() => setMobileNavOpen(true)}
          aria-label="Open navigation"
        >
          ☰
        </button>
        <Link href="#" className="flex items-center gap-2">
          <Image
            src="/llmhive-logo.svg"
            alt="LLMHive"
            width={36}
            height={36}
            className="h-9 w-auto"
            priority
          />
          <span className="text-sm font-semibold tracking-wide">LLMHive</span>
        </Link>
        <div className="text-xs text-textdim">{displayName ?? "Guest"}</div>
      </header>

      <div className="relative flex flex-1 overflow-hidden">
        <aside
          className="relative hidden h-full flex-col border-r border-border/60 bg-panel/80 pb-6 shadow-app1 transition-all duration-app2 ease-[var(--ease)] md:flex"
          style={{ width: `${navWidth}px` }}
        >
          <div className="flex h-14 items-center gap-3 border-b border-border/60 px-3">
            <Link href="#" className="flex items-center gap-3 focus-ring">
              <Image
                src="/llmhive-logo.svg"
                alt="LLMHive"
                width={navExpanded ? 40 : 32}
                height={navExpanded ? 40 : 32}
                className={navExpanded ? "h-10 w-auto" : "h-8 w-auto mx-auto"}
                priority
              />
              {navExpanded && (
                <span className="text-sm font-semibold tracking-wide">LLMHive</span>
              )}
            </Link>
          </div>

          <nav className="flex-1 space-y-2 px-3 py-4">
            {navItems.map((item) => (
              <Link
                key={item.label}
                href={item.href}
                className="glass flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-text transition duration-app1 ease-[var(--ease)] hover:bg-panel2/80"
              >
                <span aria-hidden className="text-lg">
                  {item.icon}
                </span>
                {navExpanded && <span>{item.label}</span>}
              </Link>
            ))}
          </nav>

          <div className="mt-auto space-y-3 px-3">
            <div className="rounded-xl border border-border/80 bg-panel/80 px-3 py-2 text-xs text-textdim">
              {displayName ? `Workspace • ${displayName}` : "Workspace • Guest"}
            </div>
            <button
              onClick={() => setNavExpanded((open) => !open)}
              className="focus-ring glass flex w-full items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold text-text"
            >
              {navExpanded ? "Collapse" : "Expand"}
            </button>
          </div>
        </aside>

        <main className="flex-1 overflow-y-auto bg-bg">
          <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-6 px-6 py-8 lg:px-10">
            <section className="glass rounded-2xl border border-border/80 bg-panel/80 p-6 shadow-app1">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h1 className="text-3xl font-semibold text-text">
                    Multi-LLM Orchestration HQ
                  </h1>
                  <p className="mt-2 text-sm text-textdim">
                    Command, monitor, and refine every agent in your hive from a single glass-metal cockpit.
                  </p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {quickActions.map((action) => (
                      <button
                        key={action}
                        className="focus-ring rounded-full border border-border/70 bg-panel px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-textdim transition duration-app1 ease-[var(--ease)] hover:border-primary/60"
                        type="button"
                      >
                        {action}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex flex-col items-start gap-3 text-sm text-textdim lg:items-end">
                  <span className="rounded-xl border border-border/60 bg-panel/70 px-3 py-2">
                    Status: <span className="font-semibold text-success">Online</span>
                  </span>
                  {authSlot}
                </div>
              </div>
            </section>
            {children}
          </div>
        </main>

        <aside
          className={`hidden h-full border-l border-border/60 bg-panel/80 shadow-app1 transition-all duration-app2 ease-[var(--ease)] lg:flex ${rightExpanded ? "w-[360px]" : "w-[84px]"}`}
        >
          {rightExpanded ? (
            <div className="flex w-full flex-1 flex-col">
              <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
                <span className="text-sm font-semibold uppercase tracking-[0.28em] text-textdim">
                  Agents • Run
                </span>
                <button
                  className="focus-ring rounded-lg border border-border/70 bg-panel px-3 py-1 text-xs"
                  onClick={() => setRightExpanded(false)}
                  aria-label="Collapse utilities"
                >
                  Hide
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-4 scrollbar-thin">{rightPanel}</div>
            </div>
          ) : (
            <div className="flex h-full w-full flex-col items-center gap-4 px-3 py-6">
              <button
                className="focus-ring glass flex h-12 w-12 items-center justify-center rounded-2xl text-lg text-text"
                onClick={() => setRightExpanded(true)}
                aria-label="Expand utilities"
              >
                ☰
              </button>
              {rightPanelCollapsed}
            </div>
          )}
        </aside>
      </div>

      <button
        className="fixed bottom-6 right-6 z-30 rounded-full border border-border/70 bg-panel/90 px-3 py-2 text-xs uppercase tracking-[0.3em] text-textdim shadow-app1 backdrop-blur-sm lg:hidden"
        onClick={() => setRightExpanded((open) => !open)}
      >
        {rightExpanded ? "Hide Panel" : "Show Panel"}
      </button>

      {mobileNavOpen && (
        <div className="fixed inset-0 z-40 bg-black/70 md:hidden">
          <aside className="absolute left-0 top-0 flex h-full w-64 flex-col gap-3 border-r border-border/60 bg-panel/95 p-4">
            <div className="flex items-center justify-between">
              <Image src="/llmhive-logo.svg" alt="LLMHive" width={36} height={36} className="h-9 w-auto" />
              <button
                className="focus-ring rounded-lg border border-border/70 px-2 py-1 text-sm"
                onClick={() => setMobileNavOpen(false)}
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
                  className="glass flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-text"
                >
                  <span aria-hidden>{item.icon}</span>
                  <span>{item.label}</span>
                </Link>
              ))}
            </nav>
            <div className="rounded-xl border border-border/70 bg-panel/80 px-3 py-2 text-xs text-textdim">
              {displayName ? `Workspace • ${displayName}` : "Workspace • Guest"}
            </div>
          </aside>
        </div>
      )}

      {commandPaletteOpen && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
        >
          <div className="glass w-full max-w-xl rounded-2xl border border-border/80 bg-panel/95 p-6 shadow-app2">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-text">Command Palette</h2>
              <button
                className="focus-ring rounded-lg border border-border/70 px-2 py-1 text-sm"
                onClick={() => setCommandPaletteOpen(false)}
              >
                Close
              </button>
            </div>
            <p className="mt-3 text-sm text-textdim">
              Quick actions coming soon. Press Esc to exit.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
