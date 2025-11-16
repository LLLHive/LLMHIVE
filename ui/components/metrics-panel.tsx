"use client"

import { useEffect, useState } from "react"
import { AlertCircle, Gauge, Loader2 } from "lucide-react"
import { Card } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"

interface ModelMetricRow {
  total_tokens: number
  total_cost: number
  calls: number
  success_rate?: number
  avg_quality?: number
}

interface MetricsResponse {
  in_memory?: Record<string, ModelMetricRow>
  persisted?: Record<string, ModelMetricRow>
}

export function MetricsPanel() {
  const [data, setData] = useState<MetricsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch("/api/system/model-metrics", { cache: "no-store" })
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`)
        }
        const json = (await res.json()) as MetricsResponse
        if (!cancelled) setData(json)
      } catch (err) {
        if (!cancelled) setError("Unable to load metrics. Check backend health.")
        console.error("[LLMHive] MetricsPanel error:", err)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  const hasData =
    (data?.in_memory && Object.keys(data.in_memory).length > 0) ||
    (data?.persisted && Object.keys(data.persisted).length > 0)

  return (
    <Card className="mt-4 p-3 border border-border bg-card/80">
      <div className="flex items-center gap-2 mb-2">
        <Gauge className="h-4 w-4 text-[var(--bronze)]" />
        <h3 className="text-xs font-semibold tracking-wide uppercase text-muted-foreground">
          Orchestration Health
        </h3>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          Loading model metrics...
        </div>
      )}

      {!loading && error && (
        <div className="flex items-center gap-2 text-xs text-destructive">
          <AlertCircle className="h-3 w-3" />
          {error}
        </div>
      )}

      {!loading && !error && !hasData && (
        <p className="text-xs text-muted-foreground">
          No metrics yet. Run a few orchestrations to see model usage and quality.
        </p>
      )}

      {!loading && !error && hasData && (
        <ScrollArea className="mt-2 max-h-56">
          <div className="space-y-2">
            {renderSection("In-Memory (current session)", data?.in_memory)}
            {renderSection("Persisted (historical)", data?.persisted)}
          </div>
        </ScrollArea>
      )}
    </Card>
  )
}

function renderSection(
  label: string,
  metrics?: Record<string, ModelMetricRow>,
) {
  if (!metrics || Object.keys(metrics).length === 0) return null
  return (
    <div>
      <p className="text-[10px] font-medium text-muted-foreground mb-1">{label}</p>
      <div className="space-y-1">
        {Object.entries(metrics).map(([model, row]) => (
          <div
            key={model}
            className="flex items-center justify-between text-[10px] px-2 py-1 rounded bg-secondary/40 border border-border/60"
          >
            <div className="flex flex-col">
              <span className="font-mono text-[var(--bronze)]">{model}</span>
              <span className="text-[10px] text-muted-foreground">
                calls {row.calls} · tokens {row.total_tokens}
              </span>
            </div>
            <div className="text-right">
              {row.avg_quality !== undefined && (
                <div className="text-[10px]">
                  quality {(row.avg_quality * 100).toFixed(0)}%
                </div>
              )}
              {row.success_rate !== undefined && (
                <div className="text-[10px] text-muted-foreground">
                  success {(row.success_rate * 100).toFixed(0)}%
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}


