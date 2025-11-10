#!/usr/bin/env bash
set -euo pipefail

# Ensure we are inside the repo root
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "Not inside a git repo. cd into /Users/camilodiaz/LLMHIVE first."; exit 1; }

# Make sure we’re on the feature branch
BRANCH="feat/new-shell"
git branch --show-current | grep -q "$BRANCH" || git checkout -B "$BRANCH"

# --- Tailwind tokens (dark theme) ---
mkdir -p ui
cat > ui/tailwind.config.ts <<'EOF'
import type { Config } from 'tailwindcss'

const config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: '#0b0f16',
        panel: '#111827',
        'panel-alt': '#131e33',
        text: '#e6e9ef',
        'text-dim': '#9aa3b2',
        border: '#22324a',
        gold: '#ffb31a',
        'gold-light': '#ffc74d',
        metal: '#c9d2e0',
      },
      borderRadius: {
        xl: '12px',
        '2xl': '16px',
      },
      boxShadow: {
        glass: '0 8px 24px rgba(0,0,0,0.35)',
      },
      fontFamily: {
        sans: [
          'Inter','ui-sans-serif','system-ui','Segoe UI','Roboto',
          'Helvetica','Arial','Apple Color Emoji','Segoe UI Emoji'
        ],
      },
    },
  },
  plugins: [],
} satisfies Config

export default config
EOF

# --- globals.css (dark base + smoked-glass + safe overrides) ---
mkdir -p ui/app
cat > ui/app/globals.css <<'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --glass-fill: rgba(17, 24, 39, 0.80);
  --glass-border: #22324a;
  --glass-shadow: 0 8px 24px rgba(0,0,0,0.35);
}

html, body { background-color: #0b0f16; color: #e6e9ef; }

.glass {
  background-color: var(--glass-fill);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  box-shadow: var(--glass-shadow);
}

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background-color: #22324a; border-radius: 8px; }
::-webkit-scrollbar-track { background: transparent; }

.bg-white,.bg-gray-50,.bg-slate-50,.bg-neutral-50 { background-color: #111827 !important; }
.bg-gray-100,.bg-slate-100,.bg-neutral-100 { background-color: #131e33 !important; }

.text-black,.text-gray-900,.text-slate-900,.text-neutral-900 { color: #e6e9ef !important; }
.text-gray-600,.text-gray-500,.text-slate-600,.text-slate-500,.text-neutral-500 { color: #9aa3b2 !important; }

.border-gray-200,.border-gray-300,.border-slate-200,.border-slate-300,.border-neutral-200,.border-neutral-300 { border-color: #22324a !important; }

.hover\:bg-gray-50:hover,.hover\:bg-slate-50:hover,.hover\:bg-neutral-50:hover { background-color: #131e33 !important; }

.bg-blue-500,.bg-indigo-500 { background-color: #ffb31a !important; }
.hover\:bg-blue-600:hover,.hover\:bg-indigo-600:hover { background-color: #ffc74d !important; }
.text-blue-500,.text-indigo-500 { color: #ffb31a !important; }
.ring-blue-500,.focus\:ring-blue-500:focus { --tw-ring-color: #ffb31a !important; }
EOF

# --- App Shell (sidebar + top bar) ---
mkdir -p ui/app/components
cat > ui/app/components/AppShell.tsx <<'EOF'
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';

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
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-bg text-text flex">
      <aside className={`${collapsed ? 'w-[72px]' : 'w-[280px]'} border-r border-border bg-panel flex flex-col transition-all duration-200`}>
        <div className="flex items-center gap-2 px-4 h-16 border-b border-border">
          <button aria-label="Toggle sidebar" className="rounded-lg border border-border px-2 py-1 hover:bg-panel-alt" onClick={() => setCollapsed(v => !v)} title={collapsed ? 'Expand' : 'Collapse'}>☰</button>
          {!collapsed && (
            <div className="flex items-center gap-2">
              <img src="/assets/logo_letters_bronze_overlay.png" alt="LLMHive logo" className="h-6 w-auto" />
              <span className="font-semibold">LLMHive</span>
            </div>
          )}
        </div>

        <div className="p-3">
          <Link href="/chat" className={`${collapsed ? 'text-gold' : 'bg-gold text-bg hover:bg-gold-light'} block w-full text-center rounded-lg px-3 py-2 font-medium transition-colors`} title="New Chat">
            {collapsed ? '＋' : '＋ New Chat'}
          </Link>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 py-1 space-y-1">
          {NAV.map((item) => {
            const active = item.href === '/' ? pathname === '/' : pathname?.startsWith(item.href);
            return (
              <Link key={item.href} href={item.href} className={`flex items-center gap-3 rounded-lg px-3 py-2 border transition-colors ${active ? 'border-gold bg-panel-alt' : 'border-border hover:bg-panel-alt'}`}>
                <span className="w-5 text-center">{item.emoji}</span>
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>
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
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-4">{children}</main>
      </section>
    </div>
  );
}
EOF

# --- Route-group layout so all new pages share AppShell ---
mkdir -p 'ui/app/(app)'
cat > 'ui/app/(app)/layout.tsx' <<'EOF'
import type { ReactNode } from "react";
import AppShell from "../components/AppShell";

export default function AppLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
EOF

# --- Pages ---
mkdir -p 'ui/app/(app)/chat'
cat > 'ui/app/(app)/chat/page.tsx' <<'EOF'
import dynamic from "next/dynamic";
const ChatSurface = dynamic(() => import("../../components/ChatSurface"), { ssr: false });

export default function ChatPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Chat</h1>
      <div className="rounded-xl border border-border bg-panel p-4">
        <ChatSurface />
      </div>
    </div>
  );
}
EOF

mkdir -p 'ui/app/(app)/workflows'
cat > 'ui/app/(app)/workflows/page.tsx' <<'EOF'
export default function WorkflowsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Workflows</h1>
      <p className="text-text-dim">Your saved workflows will appear here. Run, edit, duplicate, or delete them.</p>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1,2,3,4,5,6].map((i) => (
          <div key={i} className="rounded-xl border border-border bg-panel p-4">
            <div className="text-sm text-text-dim">Workflow #{i}</div>
            <div className="mt-2 flex gap-2">
              <button className="bg-gold text-bg rounded-xl px-4 py-2">Run</button>
              <button className="bg-panel-alt text-text rounded-xl px-4 py-2 border border-border">Edit</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
EOF

mkdir -p 'ui/app/(app)/datasets'
cat > 'ui/app/(app)/datasets/page.tsx' <<'EOF'
export default function DatasetsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Datasets</h1>
      <div className="rounded-xl border border-border bg-panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-panel-alt text-text-dim">
            <tr>
              <th className="text-left px-4 py-2">Name</th>
              <th className="text-left px-4 py-2">Type</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="text-left px-4 py-2">Size</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {[1,2,3].map((i) => (
              <tr key={i} className="border-t border-border">
                <td className="px-4 py-2">Dataset {i}</td>
                <td className="px-4 py-2 text-text-dim">Documents</td>
                <td className="px-4 py-2 text-text-dim">Indexed</td>
                <td className="px-4 py-2 text-text-dim">1.2 GB</td>
                <td className="px-4 py-2 text-right">
                  <button className="bg-panel-alt text-text rounded-xl px-3 py-1 border border-border">Re-index</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button className="bg-gold text-bg rounded-xl px-4 py-2">Add Data Source</button>
    </div>
  );
}
EOF

mkdir -p 'ui/app/(app)/providers'
cat > 'ui/app/(app)/providers/page.tsx' <<'EOF'
export default function ProvidersPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Providers</h1>
      <div className="rounded-xl border border-border bg-panel p-4 space-y-3">
        {["OpenAI","Anthropic","Google","OpenRouter"].map((p) => (
          <div key={p} className="flex items-center justify-between border border-border rounded-lg p-3 bg-panel-alt/50">
            <div>
              <div className="font-medium">{p}</div>
              <div className="text-sm text-text-dim">Configure API key and enable models</div>
            </div>
            <div className="flex gap-2">
              <button className="bg-panel-alt text-text rounded-xl px-3 py-1 border border-border">Configure</button>
              <button className="bg-gold text-bg rounded-xl px-3 py-1">Enable</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
EOF

mkdir -p 'ui/app/(app)/team'
cat > 'ui/app/(app)/team/page.tsx' <<'EOF'
export default function TeamPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Team</h1>
      <div className="rounded-xl border border-border bg-panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-panel-alt text-text-dim">
            <tr>
              <th className="text-left px-4 py-2">User</th>
              <th className="text-left px-4 py-2">Role</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {["Avery","Sam","Casey"].map((name, i) => (
              <tr key={i} className="border-t border-border">
                <td className="px-4 py-2">{name}</td>
                <td className="px-4 py-2"><span className="rounded-full bg-panel-alt px-2 py-1 text-xs">Admin</span></td>
                <td className="px-4 py-2 text-text-dim">Active</td>
                <td className="px-4 py-2 text-right"><button className="bg-panel-alt text-text rounded-xl px-3 py-1 border border-border">Edit</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button className="bg-gold text-bg rounded-xl px-4 py-2">Invite User</button>
    </div>
  );
}
EOF

mkdir -p 'ui/app/(app)/analytics'
cat > 'ui/app/(app)/analytics/page.tsx' <<'EOF'
export default function AnalyticsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Analytics</h1>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {label: "Prompts (24h)", value: "1,284"},
          {label: "Tokens (24h)", value: "3.2M"},
          {label: "Cost (24h)", value: "$42.18"},
          {label: "Avg Latency", value: "1.8s"},
        ].map((c) => (
          <div key={c.label} className="rounded-xl border border-border bg-panel p-4">
            <div className="text-sm text-text-dim">{c.label}</div>
            <div className="text-2xl font-semibold mt-1">{c.value}</div>
          </div>
        ))}
      </div>
      <div className="grid lg:grid-cols-2 gap-4">
        <div className="rounded-xl border border-border bg-panel p-4">
          <div className="font-semibold">Usage Trend</div>
          <div className="text-sm text-text-dim mt-2">Connect charts later; placeholder.</div>
          <div className="h-48 bg-panel-alt/50 rounded-lg mt-3" />
        </div>
        <div className="rounded-xl border border-border bg-panel p-4">
          <div className="font-semibold">Cost by Provider</div>
          <div className="text-sm text-text-dim mt-2">Placeholder.</div>
          <div className="h-48 bg-panel-alt/50 rounded-lg mt-3" />
        </div>
      </div>
    </div>
  );
}
EOF

mkdir -p 'ui/app/(app)/settings'
cat > 'ui/app/(app)/settings/page.tsx' <<'EOF'
export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Settings</h1>
      <section className="rounded-xl border border-border bg-panel p-4">
        <div className="font-semibold">Profile</div>
        <div className="grid sm:grid-cols-2 gap-3 mt-3">
          <input className="bg-panel-alt border border-border rounded-xl px-3 py-2" placeholder="Full name" />
          <input className="bg-panel-alt border border-border rounded-xl px-3 py-2" placeholder="Email" />
        </div>
        <div className="mt-3"><button className="bg-gold text-bg rounded-xl px-4 py-2">Save Profile</button></div>
      </section>
      <section className="rounded-xl border border-border bg-panel p-4">
        <div className="font-semibold">Appearance</div>
        <div className="mt-3 text-text-dim text-sm">Dark mode enforced by tokens.</div>
      </section>
    </div>
  );
}
EOF

mkdir -p 'ui/app/(app)/compare'
cat > 'ui/app/(app)/compare/page.tsx' <<'EOF'
'use client';
import { useState } from "react";

export default function ComparePage() {
  const [prompt, setPrompt] = useState("");
  const models = ["GPT-5 Pro", "Claude 3.5", "Gemini 1.5"];
  const [selected, setSelected] = useState<string[]>([models[0], models[1]]);
  const toggle = (m: string) => setSelected((s) => (s.includes(m) ? s.filter((x) => x !== m) : [...s, m]));
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Model Comparison</h1>
      <div className="rounded-xl border border-border bg-panel p-4 space-y-3">
        <textarea className="w-full bg-panel-alt border border-border rounded-xl p-3 outline-none min-h-[90px]" placeholder="Enter a test prompt…" value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        <div className="flex flex-wrap gap-2">
          {models.map((m) => (
            <button key={m} type="button" onClick={() => toggle(m)} className={`rounded-full px-3 py-1 text-sm border ${selected.includes(m) ? "bg-gold text-bg border-gold" : "bg-panel-alt text-text border-border"}`}>{m}</button>
          ))}
        </div>
        <div><button className="bg-gold text-bg rounded-xl px-4 py-2" disabled={!prompt.trim()}>Compare</button></div>
      </div>
      {selected.length > 0 && (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {selected.map((m) => (
            <div key={m} className="rounded-xl border border-border bg-panel p-4">
              <div className="text-sm text-text-dim">{m}</div>
              <div className="mt-2 text-sm">(Connect real outputs later; placeholder now.)</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
EOF

# --- Root route redirects to /chat (optional) ---
cat > ui/app/page.tsx <<'EOF'
import { redirect } from "next/navigation";
export default function Page() { redirect("/chat"); }
EOF

# Commit & push
git add -A
git commit -m "feat(ui): new shell + pages + dark theme" || true
git push -u origin "$BRANCH"

echo
echo "Done. Open GitHub → 'Compare & pull request' for '$BRANCH' → Create PR → Merge. Vercel will deploy."

