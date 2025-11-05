import { Suspense } from "react";
import type { User } from "next-auth";
import { auth, signIn, signOut } from "@/auth";
import AppShell from "./components/AppShell";
import ChatSurface from "./components/ChatSurface";
import PromptForm from "./components/PromptForm";

function SignInButton() {
  return (
    <form
      action={async () => {
        "use server";
        await signIn("github");
      }}
    >
      <button
        type="submit"
        className="focus-ring rounded-xl border border-border/70 bg-panel px-4 py-2 text-sm font-semibold text-text transition duration-app1 ease-[var(--ease)] hover:border-primary/60"
      >
        Sign in with GitHub
      </button>
    </form>
  );
}

function SignOutButton({ user }: { user: User }) {
  return (
    <div className="flex flex-col items-start gap-3 text-sm text-textdim">
      <span className="rounded-xl border border-border/70 bg-panel/70 px-3 py-2">
        Signed in as {user?.name ?? user?.email ?? "Innovator"}
      </span>
      <form
        action={async () => {
          "use server";
          await signOut();
        }}
      >
        <button
          type="submit"
          className="focus-ring rounded-xl border border-border/70 bg-panel px-4 py-2 text-sm font-semibold text-text transition duration-app1 ease-[var(--ease)] hover:border-primary/60"
        >
          Sign out
        </button>
      </form>
    </div>
  );
}

function RightPanelContent() {
  const agents: { name: string; status: "thinking" | "idle" | "queued"; description: string }[] = [
    {
      name: "GPT-4o Strategist",
      status: "thinking",
      description: "Synthesizing cross-model insights.",
    },
    {
      name: "Claude 3 Critic",
      status: "idle",
      description: "Standing by for refinement loop.",
    },
    {
      name: "Gemini 2.5 Scout",
      status: "queued",
      description: "Preparing retrieval sweep.",
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="space-y-3">
        {agents.map((agent) => (
          <AgentCard key={agent.name} {...agent} />
        ))}
      </div>
      <div className="glass rounded-2xl border border-border/70 bg-panel/80 p-4 shadow-app1">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-text">Orchestration Visualizer</h3>
          <span className="text-xs uppercase tracking-[0.28em] text-textdim">Beta</span>
        </div>
        <div
          id="orc-graph"
          className="mt-3 h-40 w-full rounded-xl border border-border/60 bg-panel/60"
        />
        <p className="mt-3 text-xs text-textdim">
          Visual sequencing of agent hand-offs and synchronization pulses will render here.
        </p>
      </div>
      <section className="glass rounded-2xl border border-border/70 bg-panel/80 p-4 shadow-app1">
        <header className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-text">Context</h3>
          <button
            type="button"
            className="focus-ring rounded-lg border border-border/70 px-3 py-1 text-xs text-textdim transition duration-app1 ease-[var(--ease)] hover:border-primary/60"
          >
            Add file
          </button>
        </header>
        <ul className="mt-3 space-y-2 text-xs text-textdim">
          <li>• Market research brief.pdf</li>
          <li>• EU compliance checklist.md</li>
          <li>• Persona targets.json</li>
        </ul>
      </section>
      <section className="glass rounded-2xl border border-border/70 bg-panel/80 p-4 shadow-app1">
        <h3 className="text-sm font-semibold text-text">Run Status</h3>
        <ul className="mt-3 space-y-2 text-xs text-textdim">
          <li className="flex items-center justify-between">
            <span>01 • Ingestion</span>
            <span className="text-success">Complete</span>
          </li>
          <li className="flex items-center justify-between">
            <span>02 • Reasoning</span>
            <span className="text-warning">In flight</span>
          </li>
          <li className="flex items-center justify-between">
            <span>03 • Critique</span>
            <span className="text-textdim">Pending</span>
          </li>
        </ul>
      </section>
    </div>
  );
}

function CollapsedUtilities() {
  const items = [
    { label: "Agents", icon: "🤖" },
    { label: "Run", icon: "⚡" },
    { label: "Context", icon: "🗂" },
    { label: "Files", icon: "📁" },
  ];
  return (
    <div className="flex flex-col items-center gap-4 text-xs text-textdim">
      {items.map((item) => (
        <div key={item.label} className="flex flex-col items-center gap-1">
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl border border-border/70 bg-panel/80 text-lg text-text">
            {item.icon}
          </span>
          <span className="uppercase tracking-[0.28em]">{item.label}</span>
        </div>
      ))}
    </div>
  );
}

function AgentCard({
  name,
  status,
  description,
}: {
  name: string;
  status: "thinking" | "idle" | "queued";
  description: string;
}) {
  const statusLabel =
    status === "thinking" ? "Thinking" : status === "queued" ? "Queued" : "Idle";
  const statusColor =
    status === "thinking" ? "bg-primary" : status === "queued" ? "bg-warning" : "bg-textdim";

  return (
    <article className="glass flex flex-col gap-2 rounded-2xl border border-border/70 bg-panel/80 p-4 shadow-app1">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-border/70 bg-panel/80 text-lg">
            🤖
          </span>
          <div>
            <h4 className="text-sm font-semibold text-text">{name}</h4>
            <p className="text-xs text-textdim">{description}</p>
          </div>
        </div>
        <span className={`inline-flex items-center gap-2 text-xs uppercase tracking-[0.28em] text-textdim`}>
          <span className={`h-2 w-2 rounded-full ${statusColor}`} aria-hidden />
          {statusLabel}
        </span>
      </header>
      <button
        type="button"
        className="focus-ring self-start rounded-lg border border-border/70 px-3 py-1 text-xs text-textdim transition duration-app1 ease-[var(--ease)] hover:border-primary/60"
      >
        Optimize Prompt
      </button>
    </article>
  );
}

export default async function Home() {
  const session = await auth();
  const user = session?.user ?? null;

  const authControls = user ? <SignOutButton user={user} /> : <SignInButton />;

  return (
    <AppShell
      authSlot={authControls}
      displayName={user?.name ?? user?.email ?? null}
      rightPanel={<RightPanelContent />}
      rightPanelCollapsed={<CollapsedUtilities />}
    >
      <ChatSurface />
      <Suspense fallback={<div className="glass rounded-2xl border border-border/80 bg-panel/80 p-6 text-sm text-textdim">Loading orchestration cockpit…</div>}>
        <PromptForm userId={user?.email ?? user?.id ?? "guest"} />
      </Suspense>
    </AppShell>
  );
}
