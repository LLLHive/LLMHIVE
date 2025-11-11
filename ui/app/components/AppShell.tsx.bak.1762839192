'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
<<<<<<< HEAD

const NAV = [
  { href: '/chat', label: 'Chat', emoji: '💬' },
  { href: '/workflows', label: 'Workflows', emoji: '🔧' },
  { href: '/datasets', label: 'Datasets', emoji: '��️' },
  { href: '/providers', label: 'Providers', emoji: '🔌' },
  { href: '/team', label: 'Team', emoji: '👥' },
  { href: '/analytics', label: 'Analytics', emoji: '📈' },
  { href: '/settings', label: 'Settings', emoji: '⚙️' },
  { href: '/compare', label: 'Compare Models', emoji: '🧪' },
];

export default function AppShell({ title, children }: { title?: string; children: React.ReactNode }) {
=======

type AppShellProps = {
  title?: string;
  children: React.ReactNode;
};

const NAV = [
  { href: '/', label: 'Chat', emoji: '💬' },
  { href: '/dashboard', label: 'Dashboard', emoji: '🏠' },
  { href: '/workflows', label: 'Workflows', emoji: '⚙️' },
  { href: '/datasets', label: 'Datasets', emoji: '🗂️' },
  { href: '/providers', label: 'Providers', emoji: '🔌' },
  { href: '/analytics', label: 'Analytics', emoji: '📈' },
  { href: '/settings', label: 'Settings', emoji: '⚙︎' },
  { href: '/model-comparison', label: 'Model Comparison', emoji: '🔬' },
];

export default function AppShell({ title = 'Chat', children }: AppShellProps) {
>>>>>>> origin/main
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-bg text-text flex">
<<<<<<< HEAD
      <aside className={`${collapsed ? 'w-[72px]' : 'w-[280px]'} border-r border-border bg-panel flex flex-col transition-all duration-200`}>
        <div className="flex items-center gap-2 px-4 h-16 border-b border-border">
          <button aria-label="Toggle sidebar" className="rounded-lg border border-border px-2 py-1 hover:bg-panel-alt" onClick={() => setCollapsed(v => !v)} title={collapsed ? 'Expand' : 'Collapse'}>☰</button>
          {!collapsed && (
            <div className="flex items-center gap-2">
              <img src="/assets/logo_letters_bronze_overlay.png" alt="LLMHive logo" className="h-6 w-auto" />
=======
      {/* Sidebar */}
      <aside
        className={`${
          collapsed ? 'w-[72px]' : 'w-[280px]'
        } border-r border-border bg-panel flex flex-col transition-all duration-200`}
      >
        <div className="flex items-center gap-2 px-4 h-16 border-b border-border">
          <button
            aria-label="Toggle sidebar"
            className="rounded-lg border border-border px-2 py-1 hover:bg-panel-alt"
            onClick={() => setCollapsed((v) => !v)}
            title={collapsed ? 'Expand' : 'Collapse'}
          >
            ☰
          </button>
          {!collapsed && (
            <div className="flex items-center gap-2">
              <img
                src="/assets/logo_letters_bronze_overlay.png"
                alt="LLMHive logo"
                className="h-6 w-auto"
              />
>>>>>>> origin/main
              <span className="font-semibold">LLMHive</span>
            </div>
          )}
        </div>

        <div className="p-3">
<<<<<<< HEAD
          <Link href="/chat" className={`${collapsed ? 'text-gold' : 'bg-gold text-bg hover:bg-gold-light'} block w-full text-center rounded-lg px-3 py-2 font-medium transition-colors`} title="New Chat">
=======
          <Link
            href="/"
            className={`block w-full text-center rounded-lg px-3 py-2 font-medium transition-colors ${
              collapsed
                ? 'text-gold'
                : 'bg-gold text-bg hover:bg-gold-light'
            }`}
            title="New Chat"
          >
>>>>>>> origin/main
            {collapsed ? '＋' : '＋ New Chat'}
          </Link>
        </div>

<<<<<<< HEAD
        <nav className="flex-1 overflow-y-auto px-2 py-1 space-y-1">
          {NAV.map((item) => {
            const active = item.href === '/' ? pathname === '/' : pathname?.startsWith(item.href);
            return (
              <Link key={item.href} href={item.href} className={`flex items-center gap-3 rounded-lg px-3 py-2 border transition-colors ${active ? 'border-gold bg-panel-alt' : 'border-border hover:bg-panel-alt'}`}>
=======
        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-2 py-1 space-y-1">
          {NAV.map((item) => {
            const active =
              item.href === '/'
                ? pathname === '/'
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 border transition-colors ${
                  active
                    ? 'border-gold bg-panel-alt'
                    : 'border-border hover:bg-panel-alt'
                }`}
              >
>>>>>>> origin/main
                <span className="w-5 text-center">{item.emoji}</span>
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>
<<<<<<< HEAD
      </aside>

      <section className="flex-1 flex flex-col">
        <header className="h-16 bg-panel border-b border-border flex items-center justify-between px-4 gap-3 sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold">{title ?? 'LLMHive'}</h1>
            <span className="text-text-dim text-sm hidden md:inline">Multi‑Agent Orchestration</span>
          </div>
          <div className="flex items-center gap-2">
            <select aria-label="Model" className="bg-panel-alt border border-border rounded-lg px-2 py-1 text-sm" defaultValue="gpt5">
              <option value="gpt5">GPT‑5 Pro</option>
              <option value="claude">Claude 3.5 Sonnet</option>
              <option value="gemini">Gemini 1.5 Pro</option>
            </select>
            <select aria-label="Orchestration" className="bg-panel-alt border border-border rounded-lg px-2 py-1 text-sm" defaultValue="balanced">
              <option value="balanced">Balanced</option>
              <option value="creative">Creative</option>
              <option value="precise">Precise</option>
            </select>
            <div className="hidden md:flex items-center gap-2">
              <label className="text-xs text-text-dim">Temp</label>
              <input type="range" min={0} max={2} step={0.1} defaultValue={0.7} className="accent-gold" />
            </div>
            <div className="hidden md:flex items-center gap-2">
              <label className="text-xs text-text-dim">Agents</label>
              <input type="number" min={1} max={8} defaultValue={3} className="bg-panel-alt border border-border rounded-md w-16 px-2 py-1 text-sm" />
=======

        {!collapsed && (
          <div className="p-3 text-xs text-text-dim border-t border-border">
            <div className="mb-2">Tasks (coming soon)</div>
            <div className="space-y-1">
              <div className="rounded-lg border border-border px-3 py-2">
                Daily summary – 8:00 AM
              </div>
              <div className="rounded-lg border border-border px-3 py-2">
                Retrain embeddings – Sun
              </div>
            </div>
          </div>
        )}
      </aside>

      {/* Main */}
      <section className="flex-1 flex flex-col">
        {/* Top bar */}
        <header className="h-16 bg-panel border-b border-border flex items-center justify-between px-4 gap-3 sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold">{title}</h1>
            <span className="text-text-dim text-sm hidden md:inline">
              Multi‑Agent Orchestration
            </span>
          </div>
          <div className="flex items-center gap-2">
            {/* Model */}
            <select
              aria-label="Model"
              className="bg-panel-alt border border-border rounded-lg px-2 py-1 text-sm"
              defaultValue="gpt5"
            >
              <option value="gpt5">GPT‑5 Pro</option>
              <option value="claude">Claude 3.5 Sonnet</option>
              <option value="gemini">Gemini 1.5 Pro</option>
            </select>
            {/* Strategy */}
            <select
              aria-label="Orchestration"
              className="bg-panel-alt border border-border rounded-lg px-2 py-1 text-sm"
              defaultValue="balanced"
            >
              <option value="balanced">Balanced</option>
              <option value="creative">Creative</option>
              <option value="precise">Precise</option>
            </select>
            {/* Temperature */}
            <div className="hidden md:flex items-center gap-2">
              <label className="text-xs text-text-dim">Temp</label>
              <input
                type="range"
                min={0}
                max={2}
                step={0.1}
                defaultValue={0.7}
                className="accent-gold"
              />
            </div>
            {/* Agents */}
            <div className="hidden md:flex items-center gap-2">
              <label className="text-xs text-text-dim">Agents</label>
              <input
                type="number"
                min={1}
                max={8}
                defaultValue={3}
                className="bg-panel-alt border border-border rounded-md w-16 px-2 py-1 text-sm"
              />
>>>>>>> origin/main
            </div>
          </div>
        </header>

<<<<<<< HEAD
=======
        {/* Content */}
>>>>>>> origin/main
        <main className="flex-1 overflow-auto p-4">{children}</main>
      </section>
    </div>
  );
}
