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
      <div className="glass rounded-xl border border-border bg-panel p-8 text-center shadow-sm">
        <h2 className="text-3xl font-semibold text-text">Welcome to LLMHive</h2>
        <p className="mt-2 text-base text-text-dim">
          Orchestrate multiple LLMs toward a single goal. Spin up a mission or load a template to get started.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          {focusQuickActions.map((chip) => (
            <button
              key={chip}
              type="button"
              className="focus-ring rounded-lg border border-border bg-panel px-4 py-2 text-xs font-semibold uppercase tracking-wide text-text-dim transition-colors duration-150 ease-soft hover:bg-panel"
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
        className="sticky bottom-0 mt-auto border-t border-transparent bg-gradient-to-t from-bg via-bg/90 to-transparent pt-4"
      >
        <div className="glass flex flex-col gap-3 rounded-xl border border-border bg-panel p-4 shadow-lg">
          <div className="flex items-center justify-between px-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-text-dim">
              Composer
            </span>
            <span className="text-xs text-text-dim">Ctrl / Cmd + Enter to run</span>
          </div>
          <textarea
            ref={textareaRef}
            className="focus-ring scrollbar-thin max-h-48 w-full resize-none rounded-xl border border-border bg-panel px-4 py-3 text-sm leading-relaxed text-text placeholder:text-text-dim/70"
            rows={1}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Describe the mission for your hive..."
          />
          <div className="flex flex-wrap items-center justify-between gap-3 px-2">
            <div className="flex gap-2">
              <button
                type="button"
                className="focus-ring rounded-lg border border-border bg-panel px-3 py-2 text-xs font-semibold uppercase tracking-wide text-text-dim transition-colors duration-150 ease-soft hover:bg-panel"
              >
                Attach
              </button>
              <button
                type="button"
                className="focus-ring rounded-lg border border-border bg-panel px-3 py-2 text-xs font-semibold uppercase tracking-wide text-text-dim transition-colors duration-150 ease-soft hover:bg-panel"
              >
                Settings
              </button>
            </div>
            <button
              type="submit"
              className="focus-ring inline-flex items-center gap-2 rounded-lg bg-gold px-5 py-2 text-sm font-semibold text-white transition-colors duration-150 ease-soft hover:bg-goldLight"
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
  const alignment = message.role === "user" ? "justify-end" : "justify-start";
  const label = message.role === "assistant" ? "LLMHive" : "You";
  const accentBorder =
    message.role === "assistant" ? "border-gold" : "border-border";

  return (
    <div className={`flex ${alignment}`}>
      <div
        className={`glass max-w-[75%] rounded-xl border ${accentBorder} bg-panel px-5 py-4 text-sm leading-relaxed text-text shadow-sm`}
      >
        <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-wide text-text-dim">
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
