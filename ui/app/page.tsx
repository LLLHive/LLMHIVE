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
        className="focus-ring rounded-button border border-border bg-panel px-4 py-2 text-sm font-semibold text-text transition-colors duration-150 ease-soft hover:bg-white"
      >
        Sign in with GitHub
      </button>
    </form>
  );
}

function SignOutButton({ user }: { user: User }) {
  return (
    <div className="flex flex-col items-start gap-3 text-sm text-textDim">
      <span className="rounded-card border border-border bg-panelAlt px-3 py-2">
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
          className="focus-ring rounded-button border border-border bg-panel px-4 py-2 text-sm font-semibold text-text transition-colors duration-150 ease-soft hover:bg-white"
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
      <div className="glass rounded-card border border-border bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-text">Orchestration Visualizer</h3>
          <span className="text-xs uppercase tracking-wide text-textDim">Beta</span>
        </div>
        <div className="mt-3 h-40 w-full rounded-card border border-border bg-panel" />
        <p className="mt-3 text-xs text-textDim">
          Visual sequencing of agent hand-offs and synchronization pulses will render here.
        </p>
      </div>
      <section className="glass rounded-card border border-border bg-white p-4 shadow-sm">
        <header className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-text">Context</h3>
          <button
            type="button"
            className="focus-ring rounded-button border border-border bg-panel px-3 py-1 text-xs text-textDim transition-colors duration-150 ease-soft hover:bg-white"
          >
            Add file
          </button>
        </header>
        <ul className="mt-3 space-y-2 text-xs text-textDim">
          <li>• Market research brief.pdf</li>
          <li>• EU compliance checklist.md</li>
          <li>• Persona targets.json</li>
        </ul>
      </section>
      <section className="glass rounded-card border border-border bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-text">Run Status</h3>
        <ul className="mt-3 space-y-2 text-xs text-textDim">
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
            <span className="text-textDim">Pending</span>
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
    <div className="flex flex-col items-center gap-4 text-xs text-textDim">
      {items.map((item) => (
        <div key={item.label} className="flex flex-col items-center gap-1">
          <span className="flex h-12 w-12 items-center justify-center rounded-card border border-border bg-panel text-lg text-text">
            {item.icon}
          </span>
          <span className="uppercase tracking-wide">{item.label}</span>
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
    status === "thinking"
      ? "bg-primary"
      : status === "queued"
      ? "bg-warning"
      : "bg-textDim";

  return (
    <article className="glass flex flex-col gap-2 rounded-card border border-border bg-white p-4 shadow-sm">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-card border border-border bg-panel text-lg">
            🤖
          </span>
          <div>
            <h4 className="text-sm font-semibold text-text">{name}</h4>
            <p className="text-xs text-textDim">{description}</p>
          </div>
        </div>
        <span className="inline-flex items-center gap-2 text-xs uppercase tracking-wide text-textDim">
          <span className={`h-2 w-2 rounded-full ${statusColor}`} aria-hidden />
          {statusLabel}
        </span>
      </header>
      <button
        type="button"
        className="focus-ring self-start rounded-button border border-border bg-panel px-3 py-1 text-xs text-textDim transition-colors duration-150 ease-soft hover:bg-white"
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
      displayName={user?.name ?? user?.email ?? null}
      rightPanel={<RightPanelContent />}
      rightPanelCollapsed={<CollapsedUtilities />}
    >
      <section className="glass rounded-card border border-border bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-4">
            <h1 className="text-3xl font-semibold text-text">Multi-LLM Orchestration HQ</h1>
            <p className="max-w-2xl text-base text-textDim">
              Command, monitor, and refine every agent in your hive from a bright, enterprise-grade cockpit. Launch orchestrations or revisit conversations with a single click.
            </p>
            <div className="flex flex-wrap gap-3">
              <button className="focus-ring rounded-button bg-primary px-5 py-3 text-sm font-semibold text-white transition-colors duration-150 ease-soft hover:bg-primaryLight" type="button">
                New Orchestration
              </button>
              <button className="focus-ring rounded-button border border-border bg-panel px-5 py-3 text-sm font-semibold text-text transition-colors duration-150 ease-soft hover:bg-white" type="button">
                Connect Provider
              </button>
              <button className="focus-ring rounded-button border border-border bg-panel px-5 py-3 text-sm font-semibold text-text transition-colors duration-150 ease-soft hover:bg-white" type="button">
                Import Dataset
              </button>
            </div>
          </div>
          <div className="flex flex-col items-start gap-3 text-sm text-textDim lg:items-end">
            <span className="rounded-card border border-border bg-panelAlt px-3 py-2">
              Status: <span className="font-semibold text-success">Online</span>
            </span>
            {authControls}
          </div>
        </div>
      </section>
      <ChatSurface />
      <Suspense fallback={<div className="glass rounded-card border border-border bg-white p-6 text-sm text-textDim shadow-sm">Loading orchestration cockpit…</div>}>
        <PromptForm userId={user?.email ?? user?.id ?? "guest"} />
      </Suspense>
    </AppShell>
  );
}
