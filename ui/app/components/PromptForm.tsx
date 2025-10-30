"use client";

import { FormEvent, useMemo, useState } from "react";
import {
  ORCHESTRATION_PROXY_PATH,
  buildOrchestrationUrl,
} from "@/app/lib/orchestrationEndpoint";
import styles from "./PromptForm.module.css";

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
    value: "gemini-1.5-pro",
    label: "Gemini 1.5 Pro (Google)",
    description: "Multimodal powerhouse with research-grade recall.",
  },
  {
    value: "grok-beta",
    label: "Grok Beta (xAI)",
    description: "Edgy reasoning with real-time awareness of the wider world.",
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

      if (!response) {
        try {
          triedProxyFallback = true;
          response = await invokeOrchestrator(ORCHESTRATION_PROXY_PATH);
        } catch (err) {
          throw err;
        }
      }

      if (!response.ok) {
        const contentType = response.headers.get("content-type") ?? "";
        if (contentType.includes("application/json")) {
          const errorPayload = await response.json();
          const message =
            (typeof errorPayload.error === "string" && errorPayload.error) ||
            (typeof errorPayload.detail === "string" && errorPayload.detail) ||
            JSON.stringify(errorPayload, null, 2);
          throw new Error(message);
        }

        const fallbackText = await response.text();
        const message = fallbackText || response.statusText || "Unexpected API error";
        throw new Error(message);
      }

      const payload = await response.json();
      const { final_response: finalResponse, plan, evaluation, supporting_notes: supportingNotes } =
        payload;

      const formattedSections: string[] = [];

      if (finalResponse) {
        formattedSections.push(`Final Response\n---------------\n${finalResponse}`);
      }

      if (plan) {
        const planSummary = [
          plan.strategy ? `Strategy: ${plan.strategy}` : null,
          plan.confidence ? `Confidence: ${plan.confidence}` : null,
          Array.isArray(plan.focus_areas) && plan.focus_areas.length
            ? `Focus Areas: ${plan.focus_areas.join(", ")}`
            : null,
        ]
          .filter(Boolean)
          .join("\n");
        if (planSummary) {
          formattedSections.push(`Orchestration Plan\n------------------\n${planSummary}`);
        }
      }

      if (Array.isArray(supportingNotes) && supportingNotes.length > 0) {
        formattedSections.push(
          `Supporting Notes\n----------------\n${supportingNotes.map((note: string) => `• ${note}`).join("\n")}`
        );
      }

      if (evaluation) {
        formattedSections.push(`Evaluation\n----------\n${evaluation}`);
      }

      if (formattedSections.length === 0) {
        formattedSections.push(JSON.stringify(payload, null, 2));
      }

      setResult(formattedSections.join("\n\n"));
    } catch (err) {
      let message = err instanceof Error ? err.message : "An unknown error occurred";
      if (message === "Failed to fetch") {
        message =
          "Failed to reach the orchestration service. Verify the backend URL configuration or try again.";
      } else if (
        message === "NetworkError when attempting to fetch resource." &&
        DIRECT_ORCHESTRATION_URL
      ) {
        if (directNetworkError && triedProxyFallback) {
          message =
            "Direct orchestration request failed due to a network error. Falling back to the internal proxy also failed. Double-check NEXT_PUBLIC_API_BASE_URL or clear it to use the proxy.";
        } else {
          message =
            "Direct orchestration request failed due to a network error. The internal proxy was not attempted. Verify NEXT_PUBLIC_API_BASE_URL or remove it to use the proxy.";
        }
      }
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <section className={styles.commanderPanel}>
        <header className={styles.sectionHeader}>
          <h2>Orchestrate your collective</h2>
          <p>
            Select the frontier models and reasoning patterns to rally for your next synthesis.
          </p>
        </header>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.controlGrid}>
            <div className={styles.controlColumn}>
              <label className={styles.label}>LLM models</label>
              <div className={styles.dropdown}>
                <button
                  type="button"
                  className={styles.dropdownToggle}
                  onClick={() => setModelMenuOpen((open) => !open)}
                  disabled={isLoading}
                  aria-expanded={isModelMenuOpen}
                >
                  {selectedModels.length} model{selectedModels.length === 1 ? "" : "s"} enlisted
                </button>
                {isModelMenuOpen && (
                  <div className={styles.dropdownMenu} role="menu">
                    {MODEL_OPTIONS.map((option) => {
                      const checked = selectedModels.includes(option.value);
                      return (
                        <label key={option.value} className={styles.dropdownOption}>
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleModelSelection(option.value)}
                          />
                          <span>
                            <span className={styles.dropdownOptionLabel}>{option.label}</span>
                            <span className={styles.dropdownOptionDescription}>
                              {option.description}
                            </span>
                          </span>
                        </label>
                      );
                    })}
                    <p className={styles.dropdownHint}>
                      Activate at least one model to kick off the hive intelligence.
                    </p>
                  </div>
                )}
              </div>
              <div className={styles.selectionChips}>
                {selectedModels.map((modelId) => {
                  const model = MODEL_OPTIONS.find((option) => option.value === modelId);
                  return (
                    <span key={modelId} className={styles.chip}>
                      {model?.label ?? modelId}
                    </span>
                  );
                })}
              </div>
            </div>

            <div className={styles.controlColumn}>
              <label className={styles.label}>Advanced reasoning strategies</label>
              <div className={styles.dropdown}>
                <button
                  type="button"
                  className={styles.dropdownToggle}
                  onClick={() => setStrategyMenuOpen((open) => !open)}
                  disabled={isLoading}
                  aria-expanded={isStrategyMenuOpen}
                >
                  {selectedStrategies.length} strateg{selectedStrategies.length === 1 ? "y" : "ies"} engaged
                </button>
                {isStrategyMenuOpen && (
                  <div className={styles.dropdownMenu} role="menu">
                    {STRATEGY_OPTIONS.map((option) => {
                      const checked = selectedStrategies.includes(option.value);
                      return (
                        <label key={option.value} className={styles.dropdownOption}>
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleStrategySelection(option.value)}
                          />
                          <span>
                            <span className={styles.dropdownOptionLabel}>{option.label}</span>
                            <span className={styles.dropdownOptionDescription}>
                              {option.description}
                            </span>
                          </span>
                        </label>
                      );
                    })}
                    <p className={styles.dropdownHint}>
                      Auto Orchestration will deselect other modes to let the system decide.
                    </p>
                  </div>
                )}
              </div>
              <p className={styles.strategyDescription}>{orchestratorSummary.strategyDescription}</p>
            </div>
          </div>

          <label className={styles.label} htmlFor="prompt">
            Prompt the hive
          </label>
          <textarea
            id="prompt"
            className={styles.textarea}
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Design a multi-agent evaluation loop that critiques product requirement documents."
            required
            disabled={isLoading}
          />

          <div className={styles.formFooter}>
            <div className={styles.summaryPanel}>
              <span className={styles.summaryTitle}>Orchestration Blueprint</span>
              <ul className={styles.summaryList}>
                <li>
                  <strong>Models:</strong> {orchestratorSummary.selectedModels.length > 0
                    ? orchestratorSummary.selectedModels.map((model) => model.label).join(", ")
                    : "--"}
                </li>
                <li>
                  <strong>Strategies:</strong> {selectedStrategies.length > 0
                    ? selectedStrategies
                        .map((strategy) =>
                          STRATEGY_OPTIONS.find((option) => option.value === strategy)?.label ?? strategy
                        )
                        .join(", ")
                    : "--"}
                </li>
              </ul>
            </div>
            <button type="submit" className={styles.button} disabled={isLoading || selectedModels.length === 0}>
              {isLoading ? "Orchestrating..." : "Launch orchestration"}
            </button>
          </div>
        </form>
      </section>

      {error && <div className={styles.error}>Error: {error}</div>}

      <section className={styles.resultSection}>
        <header className={styles.sectionHeader}>
          <h3>Hive Response</h3>
          <p>
            {isLoading
              ? "Agents are collaborating in real-time. Streaming response incoming..."
              : "The final synthesis from your curated collective appears below."}
          </p>
        </header>
        <div className={styles.resultContainer}>
          {isLoading && <div className={styles.loadingBar} aria-hidden="true" />}
          <pre className={styles.resultPre}>
            <code>{result}</code>
          </pre>
        </div>
      </section>
    </div>
  );
}
