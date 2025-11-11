'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

type AppShellProps = {
  title?: string;
  children: React.ReactNode;
};

const NAV = [
  { href: '/',           label: 'Chat' },
  { href: '/dashboard',  label: 'Dashboard' },
  { href: '/workflows',  label: 'Workflows' },
  { href: '/datasets',   label: 'Datasets' },
  { href: '/providers',  label: 'Providers' },
  { href: '/analytics',  label: 'Analytics' },
  { href: '/settings',   label: 'Settings' },
];

export default function AppShell({ title = 'Chat', children }: AppShellProps) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  // Optional: dynamic model list with safe fallback
  const [models, setModels] = useState<{value:string;label:string}[]>([
    { value: 'default', label: 'Default' }
  ]);
  const [selectedModel, setSelectedModel] = useState('default');

  useEffect(() => {
    let ignore = false;
    (async () => {
      try {
        const base = process.env.NEXT_PUBLIC_API_BASE_URL;
        const url = base
          ? base.replace(/\/+$/, '') + '/api/v1/orchestration/providers'
          : '/api/v1/orchestration/providers';
        const res = await fetch(url, { cache: 'no-store' });
        if (!res.ok) return;
        const data: any = await res.json();
        const prov = (data?.available_providers ?? Object.keys(data?.registry_summary ?? {})) as string[];
        const opts: {value:string;label:string}[] = [];
        if (prov?.includes('openai'))     opts.push({ value: 'openai',     label: 'OpenAI' });
        if (prov?.includes('anthropic'))  opts.push({ value: 'anthropic',  label: 'Claude' });
        if (prov?.includes('grok'))       opts.push({ value: 'grok',       label: 'Grok' });
        if (prov?.includes('gemini'))     opts.push({ value: 'gemini',     label: 'Gemini' });
        if (prov?.includes('deepseek'))   opts.push({ value: 'deepseek',   label: 'DeepSeek' });
        if (!ignore && opts.length) {
          setModels(opts);
          setSelectedModel(opts[0].value);
        }
      } catch (_) { /* silent fallback */ }
    })();
    return () => { ignore = true; };
  }, []);

  return (
    <div className="flex min-h-screen bg-bg text-text">
      {/* Sidebar */}
      <aside className={`bg-panel border-r border-border ${collapsed ? 'w-16' : 'w-64'} transition-[width] duration-150`}>
        <div className="h-16 flex items-center justify-between px-3">
          <Link href="/" className="font-semibold">LLMHive</Link>
          <button
            aria-label="Toggle sidebar"
            className="text-text-dim text-sm"
            onClick={() => setCollapsed((v) => !v)}
          >
            {collapsed ? '»' : '«'}
          </button>
        </div>
        <nav className="px-2 pb-4">
          <ul className="space-y-1">
            {NAV.map((item) => {
              const active = pathname === item.href;
              return (
                <li key={item.href}>
                  <Link
                    className={`block rounded-lg px-3 py-2 text-sm ${active ? 'bg-panel-alt text-text' : 'text-text-dim hover:bg-panel-alt/60'}`}
                    href={item.href}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col">
        <header className="h-16 bg-panel border-b border-border flex items-center justify-between px-4 gap-3 sticky top-0">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold">{title}</h1>
            <span className="text-text-dim text-sm hidden md:inline">Multi‑Agent Orchestration</span>
          </div>
          <div className="flex items-center gap-2">
            <select
              aria-label="Model"
              className="bg-panel-alt border border-border rounded-lg px-2 py-1 text-sm"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
            >
              {models.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
