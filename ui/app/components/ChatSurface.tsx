"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
};

type ChatSurfaceProps = {
  initialMessages?: ChatMessage[];
};

export default function ChatSurface({ initialMessages }: ChatSurfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(
    initialMessages ?? defaultMessages
  );
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const handleKeydown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
        event.preventDefault();
        textarea.form?.requestSubmit();
      }
    };

    textarea.addEventListener("keydown", handleKeydown);
    return () => textarea.removeEventListener("keydown", handleKeydown);
  }, []);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!input.trim()) return;

    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "user", content: input.trim() },
      {
        id: crypto.randomUUID(),
        role: "assistant",
        content:
          "Orchestrating the hive with contextual retrieval, ensembling GPT-4o and Claude 3. Expect a synthesized response shortly.",
      },
    ]);
    setInput("");
  };

  const focusQuickActions = useMemo(
    () => ["Load Template", "Import .json", "Open Recent"],
    []
  );

  return (
    <section className="flex flex-col gap-6">
      <div className="glass rounded-2xl border border-border/80 bg-panel/80 p-6 shadow-app1">
        <h2 className="text-xl font-semibold text-text">Welcome to LLMHive</h2>
        <p className="mt-2 text-sm text-textdim">
          Orchestrate multiple LLMs toward a single goal. Spin up a mission or load a template to get started.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {focusQuickActions.map((chip) => (
            <button
              key={chip}
              type="button"
              className="focus-ring rounded-full border border-border/70 bg-panel px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-textdim transition duration-app1 ease-[var(--ease)] hover:border-primary/60"
            >
              {chip}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-4">
        {messages.map((message) => (
          <ChatBubble key={message.id} message={message} />
        ))}
      </div>

      <form
        onSubmit={handleSubmit}
        className="sticky bottom-0 mt-auto border-t border-border/80 bg-gradient-to-t from-bg via-bg/90 to-transparent pt-4"
      >
        <div className="glass flex flex-col gap-3 rounded-2xl border border-border/80 bg-panel/80 p-3 shadow-app2">
          <div className="flex items-center justify-between px-2">
            <span className="text-xs uppercase tracking-[0.28em] text-textdim">
              Composer
            </span>
            <span className="text-xs text-textdim">Ctrl / Cmd + Enter to run</span>
          </div>
          <textarea
            ref={textareaRef}
            className="focus-ring scrollbar-thin max-h-48 w-full resize-none rounded-xl border border-border/70 bg-panel px-4 py-3 text-sm leading-relaxed text-text placeholder:text-textdim/60"
            rows={1}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Describe the mission for your hive..."
          />
          <div className="flex items-center justify-between gap-4 px-2">
            <div className="flex gap-2">
              <button
                type="button"
                className="focus-ring rounded-lg border border-border/70 px-3 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-textdim transition duration-app1 ease-[var(--ease)] hover:border-primary/60"
              >
                Attach
              </button>
              <button
                type="button"
                className="focus-ring rounded-lg border border-border/70 px-3 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-textdim transition duration-app1 ease-[var(--ease)] hover:border-primary/60"
              >
                Settings
              </button>
            </div>
            <button
              type="submit"
              className="focus-ring inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2 text-sm font-semibold text-black transition duration-app1 ease-[var(--ease)] hover:bg-primary2"
            >
              Run
            </button>
          </div>
        </div>
      </form>
    </section>
  );
}

function ChatBubble({ message }: { message: ChatMessage }) {
  const alignment = message.role === "user" ? "items-end" : "items-start";
  const label = message.role === "assistant" ? "LLMHive" : "You";
  const accent = message.role === "assistant" ? "border-primary/60" : "border-border/80";

  return (
    <div className={`flex ${alignment}`}>
      <div
        className={`glass w-full max-w-2xl rounded-2xl border ${accent} bg-panel/80 p-4 text-sm leading-relaxed text-text shadow-app1`}
      >
        <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-[0.28em] text-textdim">
          <span>{label}</span>
          <span>{message.role}</span>
        </div>
        <p className="whitespace-pre-wrap text-sm text-text">{message.content}</p>
      </div>
    </div>
  );
}

const defaultMessages: ChatMessage[] = [
  {
    id: "system-welcome",
    role: "assistant",
    content:
      "Hive orchestration ready. Deploying GPT-4o as strategist, Claude 3 as critic, and Gemini 2.5 for retrieval. Provide a mission brief to begin.",
  },
  {
    id: "user-request",
    role: "user",
    content: "Draft a market entry plan for a healthcare AI assistant in the EU.",
  },
  {
    id: "assistant-response",
    role: "assistant",
    content:
      "Initiating multi-agent workflow: 1) Research circle gathering regulations. 2) Strategy agent shaping GTM timeline. 3) Critic verifying compliance guardrails.",
  },
];
