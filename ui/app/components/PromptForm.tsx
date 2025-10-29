"use client";

import { FormEvent, useMemo, useState } from "react";
import {
  ORCHESTRATION_PROXY_PATH,
  buildOrchestrationUrl,
} from "@/app/lib/orchestrationEndpoint";
import styles from "./PromptForm.module.css";

type PromptFormProps = {
  userId?: string;
  userName?: string | null;
};

type Option = {
  value: string;
  label: string;
  description: string;
};

type StrategyOption = {
  value: string | null;
  label: string;
  description: string;
};

const MODEL_OPTIONS: Option[] = [
  {
    value: "gpt-4-turbo",
    label: "GPT-4 Turbo (OpenAI)",
    description: "Elite reasoning speed, great for complex coding and synthesis.",
  },
  {
    value: "gpt-4",
    label: "GPT-4 Legacy (OpenAI)",
    description: "Time-tested depth for analysis-heavy or critical reasoning work.",
  },
  {
    value: "claude-3-opus",
    label: "Claude 3 Opus (Anthropic)",
    description: "Expansive context window and eloquent long-form writing talent.",
  },
  {
    value: "claude-3-sonnet",
    label: "Claude 3 Sonnet (Anthropic)",
    description: "Responsive collaborator tuned for narrative polish and UX copy.",
  },
];

const STRATEGY_OPTIONS: StrategyOption[] = [
  {
    value: null,
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
];

const RAW_API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const API_BASE = RAW_API_BASE.trim();
const DIRECT_ORCHESTRATION_URL = API_BASE
  ? buildOrchestrationUrl(API_BASE)
  : null;

export default function PromptForm({ userId, userName }: PromptFormProps) {
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [primaryModel, setPrimaryModel] = useState<string>(MODEL_OPTIONS[0]?.value ?? "");
  const [dreamTeam, setDreamTeam] = useState<string[]>(() =>
    MODEL_OPTIONS[0] ? [MODEL_OPTIONS[0].value] : []
  );
  const [strategy, setStrategy] = useState<string | null>(null);
  const [isTeamMenuOpen, setTeamMenuOpen] = useState(false);

  const orchestratorSummary = useMemo(() => {
    const summaryStrategy = STRATEGY_OPTIONS.find((option) => option.value === strategy);
    const selectedModels = MODEL_OPTIONS.filter((model) =>
      dreamTeam.includes(model.value)
    );

    return {
      strategyLabel: summaryStrategy?.label ?? "Adaptive hive intelligence",
      strategyDescription:
        summaryStrategy?.description ??
        "Planner will auto-select between fast synthesis, critique loops, and research expansions.",
      selectedModels,
    };
  }, [dreamTeam, strategy]);

  const normalizedTeam = useMemo(() => {
    const allModels = new Set<string>();
    if (primaryModel) {
      allModels.add(primaryModel);
    }
    dreamTeam.forEach((model) => allModels.add(model));
    return Array.from(allModels);
  }, [primaryModel, dreamTeam]);

  const toggleDreamTeamModel = (modelId: string) => {
    setDreamTeam((current) => {
      if (modelId === primaryModel) {
        return current.includes(modelId) ? current : [...current, modelId];
      }
      const exists = current.includes(modelId);
      if (exists) {
        const filtered = current.filter((item) => item !== modelId);
        // Ensure at least one model remains selected so the orchestrator always has guidance.
        if (filtered.length === 0 && primaryModel !== modelId) {
          return filtered;
        }
        return filtered.length === 0 ? [primaryModel] : filtered;
      }
      return [...current, modelId];
    });
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!prompt.trim()) {
      return;
    }

    setIsLoading(true);
    setError("");
    setResult("");
    setTeamMenuOpen(false);

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
            models: normalizedTeam,
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
          <h2>Command the Hive</h2>
          <p>
            Tailor your dream team of frontier models and thinking protocols. LLMHive will
            choreograph the rest.
          </p>
        </header>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.controlGrid}>
            <div className={styles.controlColumn}>
              <label className={styles.label} htmlFor="primary-model">
                Lead model
              </label>
              <div className={styles.selectWrapper}>
                <select
                  id="primary-model"
                  className={styles.select}
                  value={primaryModel}
                  disabled={isLoading}
                  onChange={(event) => {
                    const newModel = event.target.value;
                    setPrimaryModel(newModel);
                    setDreamTeam((current) =>
                      current.includes(newModel) ? current : [...current, newModel]
                    );
                  }}
                >
                  {MODEL_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              <ul className={styles.optionDetails}>
                {MODEL_OPTIONS.map((option) => (
                  <li key={`${option.value}-detail`}>
                    <strong>{option.label}:</strong> {option.description}
                  </li>
                ))}
              </ul>
            </div>

            <div className={styles.controlColumn}>
              <label className={styles.label}>Dream team</label>
              <div className={styles.dropdown}>
                <button
                  type="button"
                  className={styles.dropdownToggle}
                  onClick={() => setTeamMenuOpen((open) => !open)}
                  disabled={isLoading}
                  aria-expanded={isTeamMenuOpen}
                >
                  {normalizedTeam.length} model{normalizedTeam.length === 1 ? "" : "s"} selected
                </button>
                {isTeamMenuOpen && (
                  <div className={styles.dropdownMenu} role="menu">
                    {MODEL_OPTIONS.map((option) => {
                      const checked = normalizedTeam.includes(option.value);
                      return (
                        <label key={option.value} className={styles.dropdownOption}>
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleDreamTeamModel(option.value)}
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
                      Combine complementary experts—reasoning, research, creativity—for elite output.
                    </p>
                  </div>
                )}
              </div>
              <div className={styles.selectionChips}>
                {normalizedTeam.map((modelId) => {
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
              <label className={styles.label} htmlFor="strategy">
                Thinking strategy
              </label>
              <div className={styles.selectWrapper}>
                <select
                  id="strategy"
                  className={styles.select}
                  value={strategy ?? ""}
                  disabled={isLoading}
                  onChange={(event) => {
                    const value = event.target.value;
                    setStrategy(value === "" ? null : value);
                  }}
                >
                  {STRATEGY_OPTIONS.map((option) => (
                    <option key={option.label} value={option.value ?? ""}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              <p className={styles.strategyDescription}>
                {orchestratorSummary.strategyDescription}
              </p>
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
            placeholder="Act as the world's best software design engineer and AI expert..."
            required
            disabled={isLoading}
          />

          <div className={styles.formFooter}>
            <div className={styles.summaryPanel}>
              <span className={styles.summaryTitle}>Orchestration Blueprint</span>
              <ul className={styles.summaryList}>
                <li>
                  <strong>Lead:</strong> {MODEL_OPTIONS.find((option) => option.value === primaryModel)?.label ?? "Unassigned"}
                </li>
                <li>
                  <strong>Dream Team:</strong> {normalizedTeam.length > 0 ? normalizedTeam
                    .map((modelId) => MODEL_OPTIONS.find((option) => option.value === modelId)?.label ?? modelId)
                    .join(", ") : "--"}
                </li>
                <li>
                  <strong>Strategy:</strong> {orchestratorSummary.strategyLabel}
                </li>
              </ul>
            </div>
            <button type="submit" className={styles.button} disabled={isLoading}>
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
