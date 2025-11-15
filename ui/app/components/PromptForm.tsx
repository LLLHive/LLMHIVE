"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  ORCHESTRATION_PATH,
  buildOrchestrationUrl,
} from "@/app/lib/orchestrationEndpoint";

type PromptFormProps = {
  userId?: string;
};

type Option = {
  value: string;
  label: string;
  description: string;
};

type StrategyOption = {
  value: string;
  label: string;
  description: string;
};

const MODEL_OPTIONS: Option[] = [
  {
    value: "gpt-4o",
    label: "GPT-4o (OpenAI)",
    description: "Elite reasoning speed, great for complex coding and synthesis.",
  },
  {
    value: "gpt-4.1",
    label: "GPT-4.1 (OpenAI)",
    description: "Time-tested depth for analysis-heavy or critical reasoning work.",
  },
  {
    value: "claude-3-opus-20240229",
    label: "Claude 3 Opus (Anthropic)",
    description: "Expansive context window and eloquent long-form writing talent.",
  },
  {
    value: "claude-3-sonnet-20240229",
    label: "Claude 3 Sonnet (Anthropic)",
    description: "Responsive collaborator tuned for narrative polish and UX copy.",
  },
  {
    value: "gemini-2.5-flash",
    label: "Gemini 2.5 Flash (Google)",
    description: "Latest multimodal model with fast reasoning and updated knowledge.",
  },
  {
    value: "grok-3-mini",
    label: "Grok 3 Mini (xAI)",
    description: "Compact reasoning model with real-time awareness and faster responses.",
  },
  {
    value: "llmhive-ensemble",
    label: "LLMHive Ensemble",
    description: "Balanced collective that routes prompts to the best-fit model automatically.",
  },
];

const STRATEGY_OPTIONS: StrategyOption[] = [
  {
    value: "auto",
    label: "Auto Orchestration",
    description: "Let LLMHive analyze the brief and assemble the optimal reasoning flow.",
  },
  {
    value: "simple",
    label: "Lightning Synthesis",
    description: "Single maestro agent delivers a direct, high-clarity response.",
  },
  {
    value: "critique_and_improve",
    label: "Critique & Elevate",
    description: "Drafting squad + critic refine the answer through iterative deep thinking.",
  },
  {
    value: "research_circle",
    label: "Research Circle",
    description: "Parallel agents scour sources before converging on the answer.",
  },
];

const RAW_API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const API_BASE = RAW_API_BASE.trim();
const DIRECT_ORCHESTRATION_URL = API_BASE
  ? buildOrchestrationUrl(API_BASE)
  : null;

export default function PromptForm({ userId }: PromptFormProps) {
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedModels, setSelectedModels] = useState<string[]>(() =>
    MODEL_OPTIONS.length > 0 ? [MODEL_OPTIONS[0].value] : []
  );
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([
    STRATEGY_OPTIONS[0]?.value ?? "auto",
  ]);
  const [isModelMenuOpen, setModelMenuOpen] = useState(false);
  const [isStrategyMenuOpen, setStrategyMenuOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const handler = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
        event.preventDefault();
        textarea.form?.requestSubmit();
      }
    };

    textarea.addEventListener("keydown", handler);
    return () => {
      textarea.removeEventListener("keydown", handler);
    };
  }, []);

  const orchestratorSummary = useMemo(() => {
    const models = MODEL_OPTIONS.filter((model) =>
      selectedModels.includes(model.value)
    );
    const strategies = STRATEGY_OPTIONS.filter((option) =>
      selectedStrategies.includes(option.value)
    );

    const strategyLabel = strategies.length
      ? strategies.map((strategy) => strategy.label).join(", ")
      : "Adaptive hive intelligence";

    const strategyDescription = strategies.length
      ? strategies.map((strategy) => strategy.description).join(" ")
      : "Planner will auto-select between fast synthesis, critique loops, and research expansions.";

    return {
      selectedModels: models,
      strategyLabel,
      strategyDescription,
    };
  }, [selectedModels, selectedStrategies]);

  const toggleModelSelection = (modelId: string) => {
    setSelectedModels((current) => {
      const exists = current.includes(modelId);
      if (exists) {
        const filtered = current.filter((value) => value !== modelId);
        return filtered.length === 0 ? current : filtered;
      }
      return [...current, modelId];
    });
  };

  const toggleStrategySelection = (strategyId: string) => {
    setSelectedStrategies((current) => {
      const exists = current.includes(strategyId);
      if (exists) {
        const filtered = current.filter((value) => value !== strategyId);
        return filtered.length === 0 ? [STRATEGY_OPTIONS[0].value] : filtered;
      }
      if (strategyId === STRATEGY_OPTIONS[0].value) {
        return [strategyId];
      }
      const withoutAuto = current.filter(
        (value) => value !== STRATEGY_OPTIONS[0].value
      );
      return [...withoutAuto, strategyId];
    });
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!prompt.trim() || selectedModels.length === 0) {
      return;
    }

    setIsLoading(true);
    setError("");
    setResult("");
    setModelMenuOpen(false);
    setStrategyMenuOpen(false);

    let response: Response | undefined;
    let directNetworkError = false;
    let triedProxyFallback = false;

    try {
      const invokeOrchestrator = (endpoint: string) =>
        fetch(endpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            user_id: userId ?? "guest",
            prompt,
            models: selectedModels,
            reasoning_strategies: selectedStrategies,
            enable_memory: true,
          }),
        });

      if (DIRECT_ORCHESTRATION_URL) {
        try {
          response = await invokeOrchestrator(DIRECT_ORCHESTRATION_URL);
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          const isNetworkError =
            message === "Failed to fetch" ||
            message === "NetworkError when attempting to fetch resource.";
          if (!isNetworkError) {
            throw err;
          }
          directNetworkError = true;
        }
      }

      if (!response && !directNetworkError) {
        response = await invokeOrchestrator(ORCHESTRATION_PATH);
      }

      if (!response && directNetworkError) {
        response = await invokeOrchestrator(ORCHESTRATION_PATH);
        triedProxyFallback = true;
      }

      if (!response) {
        throw new Error("No response from orchestrator");
      }

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        const message =
          typeof payload?.detail === "string"
            ? payload.detail
            : "Failed to orchestrate the request.";
        throw new Error(message);
      }

      const payload = await response.json();
      const text = payload?.final_response ?? JSON.stringify(payload, null, 2);
      setResult(text);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(
        triedProxyFallback
          ? `${message} (after proxy fallback)`
          : message
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="space-y-6">
      <header className="glass rounded-2xl border border-border bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.32em] text-text-dim">Commander</p>
            <h2 className="text-2xl font-semibold text-text">Orchestration Console</h2>
            <p className="max-w-2xl text-sm text-text-dim">
              Select the models and reasoning strategies to deploy for this mission. LLMHive will route insight across the hive and return a fused response.
            </p>
          </div>
          <div className="flex gap-2">
            <div className="rounded-full border border-border px-3 py-1 text-xs uppercase tracking-widest text-text-dim">Ctrl / Cmd + Enter to run</div>
          </div>
        </div>
      </header>

      <form
        className="glass rounded-2xl border border-border bg-white p-6 shadow-lg"
        onSubmit={handleSubmit}
      >
        <div className="grid gap-6 lg:grid-cols-2">
          <fieldset className="flex flex-col gap-4">
            <legend className="text-xs font-semibold uppercase tracking-[0.28em] text-text-dim">
              Model Collective
            </legend>
            <div className="relative">
              <button
                type="button"
                className="focus-ring flex w-full items-center justify-between rounded-xl border border-border bg-panel px-4 py-3 text-left text-sm font-medium text-text shadow-inner transition duration-150 ease-soft hover:border-gold/70"
                onClick={() => setModelMenuOpen((open) => !open)}
                aria-expanded={isModelMenuOpen}
              >
                <span>
                  {selectedModels.length} selected
                </span>
                <span className="text-text-dim">▼</span>
              </button>
              {isModelMenuOpen && (
                <div className="scrollbar-thin absolute z-30 mt-3 w-full max-h-80 overflow-y-auto rounded-2xl border border-border bg-panel-alt p-3 shadow-lg">
                  {MODEL_OPTIONS.map((model) => (
                    <label
                      key={model.value}
                      className="flex cursor-pointer gap-3 rounded-xl p-3 transition duration-150 ease-soft hover:bg-gold/10"
                    >
                      <input
                        type="checkbox"
                        className="accent-gold"
                        checked={selectedModels.includes(model.value)}
                        onChange={() => toggleModelSelection(model.value)}
                      />
                      <span>
                        <span className="block text-sm font-semibold text-text">{model.label}</span>
                        <span className="mt-1 block text-xs text-text-dim">{model.description}</span>
                      </span>
                    </label>
                  ))}
                  <p className="mt-4 border-t border-border pt-3 text-xs text-text-dim">
                    At least one model must remain active to deploy the hive.
                  </p>
                </div>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {selectedModels.map((modelId) => {
                const model = MODEL_OPTIONS.find((item) => item.value === modelId);
                if (!model) return null;
                return (
                  <span
                    key={modelId}
                    className="rounded-full border border-border bg-panel px-3 py-1 text-xs text-text"
                  >
                    {model.label}
                  </span>
                );
              })}
            </div>
          </fieldset>

          <fieldset className="flex flex-col gap-4">
            <legend className="text-xs font-semibold uppercase tracking-[0.28em] text-text-dim">
              Reasoning Strategy
            </legend>
            <div className="relative">
              <button
                type="button"
                className="focus-ring flex w-full items-center justify-between rounded-xl border border-border bg-panel px-4 py-3 text-left text-sm font-medium text-text shadow-inner transition duration-150 ease-soft hover:border-gold/70"
                onClick={() => setStrategyMenuOpen((open) => !open)}
                aria-expanded={isStrategyMenuOpen}
              >
                <span>
                  {selectedStrategies.length} active
                </span>
                <span className="text-text-dim">▼</span>
              </button>
              {isStrategyMenuOpen && (
                <div className="scrollbar-thin absolute z-30 mt-3 w-full max-h-80 overflow-y-auto rounded-2xl border border-border bg-panel-alt p-3 shadow-lg">
                  {STRATEGY_OPTIONS.map((strategy) => (
                    <label
                      key={strategy.value}
                      className="flex cursor-pointer gap-3 rounded-xl p-3 transition duration-150 ease-soft hover:bg-gold/10"
                    >
                      <input
                        type="checkbox"
                        className="accent-gold"
                        checked={selectedStrategies.includes(strategy.value)}
                        onChange={() => toggleStrategySelection(strategy.value)}
                      />
                      <span>
                        <span className="block text-sm font-semibold text-text">{strategy.label}</span>
                        <span className="mt-1 block text-xs text-text-dim">{strategy.description}</span>
                      </span>
                    </label>
                  ))}
                  <p className="mt-4 border-t border-border pt-3 text-xs text-text-dim">
                    Selecting Auto Orchestration deselects other strategies.
                  </p>
                </div>
              )}
            </div>
            <p className="text-sm text-text-dim">{orchestratorSummary.strategyDescription}</p>
          </fieldset>
        </div>

        <div className="mt-8 space-y-4">
          <label className="flex flex-col gap-2 text-sm text-text">
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-text-dim">Mission Brief</span>
            <textarea
              ref={textareaRef}
              className="focus-ring scrollbar-thin min-h-[220px] w-full resize-y rounded-2xl border border-border bg-panel px-4 py-4 text-sm leading-relaxed text-text placeholder:text-text-dim/60"
              placeholder="Describe the outcome you want the hive to pursue..."
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
            />
          </label>
          <div className="grid gap-4 rounded-2xl border border-border bg-panel p-4 sm:grid-cols-2">
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-[0.28em] text-text-dim">Ensemble</h4>
              <ul className="mt-2 space-y-1 text-sm text-text-dim">
                {orchestratorSummary.selectedModels.map((model) => (
                  <li key={model.value}>{model.label}</li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-[0.28em] text-text-dim">Strategy</h4>
              <p className="mt-2 text-sm text-text-dim">
                {orchestratorSummary.strategyLabel}
              </p>
            </div>
          </div>
        </div>

        <div className="mt-8 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3 text-sm text-text-dim">
            <span className="inline-flex h-3 w-3 rounded-full bg-gold" aria-hidden />
            <span>Hive memory enabled for this run.</span>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="reset"
              className="focus-ring rounded-lg border border-border bg-panel px-4 py-2 text-sm font-semibold text-text transition-colors duration-150 ease-soft hover:bg-white"
              onClick={() => {
                setPrompt("");
                setResult("");
                setError("");
                setSelectedModels([MODEL_OPTIONS[0].value]);
                setSelectedStrategies([STRATEGY_OPTIONS[0].value]);
              }}
            >
              Reset
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="focus-ring inline-flex items-center justify-center gap-2 rounded-lg bg-gold px-5 py-2 text-sm font-semibold text-white transition-colors duration-150 ease-soft hover:bg-goldLight disabled:cursor-not-allowed disabled:opacity-70"
            >
              {isLoading ? "Deploying hive..." : "Run orchestration"}
            </button>
          </div>
        </div>
      </form>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="glass rounded-2xl border border-border bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-text">Orchestration Output</h3>
          <p className="mt-2 text-sm text-text-dim">
            Responses are synthesized across the active agents and appear here with trace metadata.
          </p>
          <div className="scrollbar-thin mt-4 max-h-72 overflow-y-auto rounded-xl border border-border bg-panel p-4 text-sm leading-relaxed text-text">
            {error && (
              <p className="text-danger">{error}</p>
            )}
            {!error && (result || isLoading) && (
              <pre className="whitespace-pre-wrap text-text">{result || "Awaiting hive response..."}</pre>
            )}
            {!error && !result && !isLoading && (
              <p className="text-text-dim">
                Launch a mission to view the orchestrated answer.
              </p>
            )}
          </div>
        </div>
        <div className="glass rounded-2xl border border-border bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-text">Execution Log</h3>
          <p className="mt-2 text-sm text-text-dim">
            Track which agents engaged, their status, and any follow-up actions required.
          </p>
          <ul className="mt-4 space-y-3 text-sm text-text-dim">
            <li className="flex items-center justify-between rounded-xl border border-border bg-white px-4 py-3">
              <span>Router Agent</span>
              <span className="text-xs font-semibold text-success">Complete</span>
            </li>
            <li className="flex items-center justify-between rounded-xl border border-border bg-white px-4 py-3">
              <span>Critic Squad</span>
              <span className="text-xs font-semibold text-warning">Reviewing</span>
            </li>
            <li className="flex items-center justify-between rounded-xl border border-border bg-white px-4 py-3">
              <span>Research Circle</span>
              <span className="text-xs font-semibold text-text-dim">Queued</span>
            </li>
          </ul>
        </div>
      </div>
    </section>
  );
}
