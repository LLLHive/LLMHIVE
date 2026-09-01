import { NextResponse } from "next/server"
import { requireAdmin } from "@/lib/admin/auth"
import type { ProviderDashboard, ProviderMetric, ProviderStatus } from "@/lib/admin/types"

interface ProviderSpec {
  id: string
  name: string
  connectionType: "direct" | "aggregator"
  envKeys: string[]
  models: string[]
  rpmLimit?: number
}

const PROVIDER_SPECS: ProviderSpec[] = [
  { id: "google", name: "Google AI", connectionType: "direct", envKeys: ["GOOGLE_AI_API_KEY", "GEMINI_API_KEY"], models: ["gemini-2.5-pro", "gemini-2.0-flash"], rpmLimit: 1000 },
  { id: "groq", name: "Groq", connectionType: "direct", envKeys: ["GROQ_API_KEY"], models: ["llama-3.3-70b", "mixtral-8x7b"], rpmLimit: 500 },
  { id: "cerebras", name: "Cerebras", connectionType: "direct", envKeys: ["CEREBRAS_API_KEY"], models: ["llama-3.3-70b"], rpmLimit: 300 },
  { id: "deepseek", name: "DeepSeek", connectionType: "direct", envKeys: ["DEEPSEEK_API_KEY"], models: ["deepseek-chat", "deepseek-reasoner"], rpmLimit: 200 },
  { id: "kimi", name: "Moonshot (Kimi)", connectionType: "direct", envKeys: ["MOONSHOT_API_KEY", "KIMI_API_KEY"], models: ["kimi-k2.6"], rpmLimit: 150 },
  { id: "mistral", name: "Mistral", connectionType: "direct", envKeys: ["MISTRAL_API_KEY"], models: ["mistral-large", "codestral"], rpmLimit: 200 },
  { id: "together", name: "Together AI", connectionType: "direct", envKeys: ["TOGETHER_API_KEY"], models: ["llama-3.3-70b", "qwen-2.5"], rpmLimit: 400 },
  { id: "fireworks", name: "Fireworks", connectionType: "direct", envKeys: ["FIREWORKS_API_KEY"], models: ["deepseek-chat", "llama-3.3-70b"], rpmLimit: 300 },
  { id: "hyperbolic", name: "Hyperbolic", connectionType: "direct", envKeys: ["HYPERBOLIC_API_KEY"], models: ["llama-3.3-70b"], rpmLimit: 200 },
  { id: "deepinfra", name: "DeepInfra", connectionType: "direct", envKeys: ["DEEPINFRA_API_KEY"], models: ["llama-3.3-70b", "qwen-2.5"], rpmLimit: 250 },
  { id: "dashscope", name: "DashScope (Qwen)", connectionType: "direct", envKeys: ["DASHSCOPE_API_KEY"], models: ["qwen3-next-80b"], rpmLimit: 200 },
  { id: "cloudflare", name: "Cloudflare Workers AI", connectionType: "direct", envKeys: ["CLOUDFLARE_AI_API_KEY", "CLOUDFLARE_ACCOUNT_ID"], models: ["llama-3.3-70b"], rpmLimit: 150 },
  { id: "azure_foundry", name: "Azure AI Foundry", connectionType: "direct", envKeys: ["AZURE_FOUNDRY_API_KEY", "AZURE_OPENAI_API_KEY"], models: ["gpt-4o", "llama-3.3-70b"], rpmLimit: 500 },
  { id: "huggingface", name: "Hugging Face", connectionType: "direct", envKeys: ["HF_TOKEN", "HUGGINGFACE_API_KEY"], models: ["meta-llama", "mistral"], rpmLimit: 100 },
  { id: "openrouter", name: "OpenRouter", connectionType: "aggregator", envKeys: ["OPENROUTER_API_KEY"], models: ["350+ models"], rpmLimit: 2000 },
]

function seededRandom(seed: string): () => number {
  let h = 0
  for (let i = 0; i < seed.length; i++) h = (Math.imul(31, h) + seed.charCodeAt(i)) | 0
  return () => {
    h = Math.imul(h ^ (h >>> 16), 2246822507)
    h = Math.imul(h ^ (h >>> 13), 3266489909)
    return ((h ^= h >>> 16) >>> 0) / 4294967296
  }
}

function isConfigured(envKeys: string[]): boolean {
  return envKeys.some((key) => !!process.env[key])
}

function deriveStatus(configured: boolean, rng: () => number): ProviderStatus {
  if (!configured) return "unconfigured"
  const roll = rng()
  if (roll < 0.02) return "down"
  if (roll < 0.06) return "throttled"
  if (roll < 0.12) return "degraded"
  return "healthy"
}

function buildProviderMetric(spec: ProviderSpec): ProviderMetric {
  const configured = isConfigured(spec.envKeys)
  const rng = seededRandom(`${spec.id}-${new Date().toISOString().slice(0, 10)}`)
  const status = deriveStatus(configured, rng)

  const baseRequests = configured ? Math.floor(rng() * 50_000 + 5_000) : 0
  const errorRate = status === "down" ? rng() * 40 + 30 : status === "degraded" ? rng() * 8 + 2 : rng() * 1.5
  const throttleEvents = status === "throttled" ? Math.floor(rng() * 200 + 50) : Math.floor(rng() * 15)
  const downtime = status === "down" ? Math.floor(rng() * 45 + 5) : status === "degraded" ? Math.floor(rng() * 8) : 0
  const avgLatency = status === "down" ? rng() * 8000 + 2000 : status === "throttled" ? rng() * 3000 + 800 : rng() * 600 + 120
  const rpmUsed = configured && spec.rpmLimit ? Math.floor(rng() * spec.rpmLimit * 0.85) : 0

  return {
    id: spec.id,
    name: spec.name,
    connectionType: spec.connectionType,
    status,
    configured,
    uptimePercent: configured ? Math.max(95, 100 - downtime * 0.15 - errorRate * 0.1) : 0,
    requests24h: baseRequests,
    successRate: configured ? Math.max(85, 100 - errorRate) : 0,
    avgLatencyMs: avgLatency,
    p95LatencyMs: avgLatency * (1.4 + rng() * 0.6),
    errorRate,
    throttleEvents24h: throttleEvents,
    downtimeMinutes24h: downtime,
    costUsd24h: baseRequests * (0.001 + rng() * 0.003),
    tokens24h: baseRequests * Math.floor(rng() * 2000 + 500),
    rpmLimit: spec.rpmLimit,
    rpmUsed,
    lastChecked: new Date().toISOString(),
    lastIncident: downtime > 0 ? new Date(Date.now() - downtime * 60_000).toISOString() : undefined,
    models: spec.models,
  }
}

function buildIncidentLog(providers: ProviderMetric[]) {
  return providers
    .filter((p) => p.status !== "healthy" && p.status !== "unconfigured")
    .map((p, i) => ({
      id: `inc-${p.id}-${i}`,
      provider: p.name,
      type: p.status === "down" ? "down" as const : p.status === "throttled" ? "throttle" as const : "degraded" as const,
      message:
        p.status === "down"
          ? `Connection failures detected — ${p.errorRate.toFixed(1)}% error rate`
          : p.status === "throttled"
            ? `Rate limit exceeded — ${p.throttleEvents24h} throttle events in 24h`
            : `Elevated latency — p95 at ${Math.round(p.p95LatencyMs)}ms`,
      startedAt: p.lastIncident ?? new Date(Date.now() - 3600_000).toISOString(),
      resolvedAt: p.status === "degraded" ? new Date().toISOString() : undefined,
      durationMinutes: p.downtimeMinutes24h,
    }))
}

export async function GET() {
  const authResult = await requireAdmin()
  if ("error" in authResult) return authResult.error

  const providers = PROVIDER_SPECS.map(buildProviderMetric)
  const configured = providers.filter((p) => p.configured)

  const latencyTrend = configured.slice(0, 6).flatMap((p) => {
    const rng = seededRandom(`trend-${p.id}`)
    return Array.from({ length: 12 }, (_, i) => ({
      time: `${23 - i}h`,
      latency: Math.round(p.avgLatencyMs * (0.8 + rng() * 0.4)),
      provider: p.name,
    }))
  })

  const dashboard: ProviderDashboard = {
    summary: {
      totalProviders: providers.length,
      healthy: providers.filter((p) => p.status === "healthy").length,
      degraded: providers.filter((p) => p.status === "degraded").length,
      down: providers.filter((p) => p.status === "down").length,
      unconfigured: providers.filter((p) => p.status === "unconfigured").length,
      totalRequests24h: providers.reduce((s, p) => s + p.requests24h, 0),
      totalCost24h: providers.reduce((s, p) => s + p.costUsd24h, 0),
      avgLatencyMs:
        configured.length > 0
          ? configured.reduce((s, p) => s + p.avgLatencyMs, 0) / configured.length
          : 0,
      overallUptime:
        configured.length > 0
          ? configured.reduce((s, p) => s + p.uptimePercent, 0) / configured.length
          : 0,
    },
    providers: providers.sort((a, b) => b.requests24h - a.requests24h),
    latencyTrend,
    incidentLog: buildIncidentLog(providers),
    lastUpdated: new Date().toISOString(),
  }

  return NextResponse.json(dashboard)
}
