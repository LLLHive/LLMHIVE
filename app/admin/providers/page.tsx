"use client"

import { useCallback, useEffect, useState } from "react"
import {
  AlertTriangle,
  Clock,
  Gauge,
  Server,
  TrendingDown,
  Wifi,
  WifiOff,
} from "lucide-react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { AdminShell } from "@/components/admin/admin-shell"
import { MetricCard } from "@/components/admin/metric-card"
import { ConnectionTypeBadge, StatusBadge } from "@/components/admin/status-badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import { formatCurrency, formatLatency, formatNumber, timeAgo } from "@/lib/admin/format"
import type { ProviderDashboard, ProviderMetric } from "@/lib/admin/types"

function ProviderRow({ provider }: { provider: ProviderMetric }) {
  const rpmPercent =
    provider.rpmLimit && provider.rpmUsed
      ? (provider.rpmUsed / provider.rpmLimit) * 100
      : 0

  return (
    <tr className="border-b border-border/30 hover:bg-muted/20 transition-colors">
      <td className="py-4 px-3">
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium">{provider.name}</span>
            <ConnectionTypeBadge type={provider.connectionType} />
          </div>
          <div className="flex items-center gap-1.5 flex-wrap">
            {provider.models.slice(0, 2).map((m) => (
              <span key={m} className="text-[10px] text-muted-foreground bg-muted/50 px-1.5 py-0.5 rounded">
                {m}
              </span>
            ))}
            {provider.models.length > 2 && (
              <span className="text-[10px] text-muted-foreground">+{provider.models.length - 2}</span>
            )}
          </div>
        </div>
      </td>
      <td className="py-4 px-3">
        <StatusBadge status={provider.status} />
      </td>
      <td className="py-4 px-3 text-right font-mono text-sm">{formatNumber(provider.requests24h)}</td>
      <td className="py-4 px-3 text-right">
        <div className="font-mono text-sm">{formatLatency(provider.avgLatencyMs)}</div>
        <div className="text-[10px] text-muted-foreground">p95 {formatLatency(provider.p95LatencyMs)}</div>
      </td>
      <td className="py-4 px-3 text-right">
        <span className={provider.successRate >= 99 ? "text-emerald-500" : provider.successRate >= 95 ? "text-amber-500" : "text-red-500"}>
          {provider.successRate.toFixed(1)}%
        </span>
      </td>
      <td className="py-4 px-3 text-right font-mono text-sm">{formatCurrency(provider.costUsd24h)}</td>
      <td className="py-4 px-3 text-right">
        <div className="flex flex-col items-end gap-1">
          <span className="text-sm font-medium">{provider.uptimePercent.toFixed(1)}%</span>
          {provider.downtimeMinutes24h > 0 && (
            <span className="text-[10px] text-red-400">{provider.downtimeMinutes24h}m down</span>
          )}
        </div>
      </td>
      <td className="py-4 px-3 min-w-[100px]">
        {provider.rpmLimit && provider.configured ? (
          <div>
            <div className="text-[10px] text-muted-foreground mb-1 text-right">
              {provider.rpmUsed}/{provider.rpmLimit} RPM
            </div>
            <Progress
              value={rpmPercent}
              className={`h-1.5 ${rpmPercent > 85 ? "[&>div]:bg-orange-500" : ""}`}
            />
            {provider.throttleEvents24h > 0 && (
              <div className="text-[10px] text-orange-400 mt-0.5 text-right">
                {provider.throttleEvents24h} throttled
              </div>
            )}
          </div>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )}
      </td>
    </tr>
  )
}

export default function AdminProvidersPage() {
  const [data, setData] = useState<ProviderDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<"all" | "direct" | "aggregator">("all")

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch("/api/admin/providers")
      if (!res.ok) {
        setError(res.status === 403 ? "Unauthorized" : "Failed to load providers")
        return
      }
      setData(await res.json())
    } catch {
      setError("Connection failed")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30_000)
    return () => clearInterval(interval)
  }, [fetchData])

  const filtered = data?.providers.filter((p) => {
    if (filter === "direct") return p.connectionType === "direct"
    if (filter === "aggregator") return p.connectionType === "aggregator"
    return true
  })

  const utilizationData = data?.providers
    .filter((p) => p.configured)
    .slice(0, 8)
    .map((p) => ({
      name: p.name.split(" ")[0],
      requests: p.requests24h,
      cost: p.costUsd24h,
      fill: p.status === "healthy" ? "var(--bronze)" : p.status === "down" ? "#ef4444" : "#f59e0b",
    }))

  return (
    <AdminShell
      title="Provider Operations"
      description="Monitor direct API connections and aggregators"
      onRefresh={fetchData}
      refreshing={loading}
    >
      {error ? (
        <Card className="max-w-md mx-auto mt-12">
          <CardContent className="pt-8 text-center">
            <WifiOff className="h-10 w-10 text-red-500 mx-auto mb-4" />
            <p className="font-medium">{error}</p>
          </CardContent>
        </Card>
      ) : loading && !data ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-28 rounded-xl" />
            ))}
          </div>
          <Skeleton className="h-96 rounded-xl" />
        </div>
      ) : data && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            <MetricCard title="Healthy" value={data.summary.healthy} icon={Wifi} variant="success" subtitle={`of ${data.summary.totalProviders}`} />
            <MetricCard title="Degraded" value={data.summary.degraded} icon={AlertTriangle} variant={data.summary.degraded > 0 ? "warning" : "default"} />
            <MetricCard title="Down" value={data.summary.down} icon={TrendingDown} variant={data.summary.down > 0 ? "danger" : "default"} />
            <MetricCard title="Requests (24h)" value={formatNumber(data.summary.totalRequests24h)} icon={Gauge} />
            <MetricCard title="Cost (24h)" value={formatCurrency(data.summary.totalCost24h)} icon={Server} variant="bronze" />
          </div>

          {data.incidentLog.length > 0 && (
            <Card className="border-amber-500/20 bg-amber-500/5">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2 text-amber-500">
                  <AlertTriangle className="h-4 w-4" />
                  Active Incidents
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {data.incidentLog.map((inc) => (
                    <div key={inc.id} className="flex items-start gap-3 text-sm rounded-lg bg-background/50 px-4 py-3">
                      <StatusBadge status={inc.type === "down" ? "down" : inc.type === "throttle" ? "throttled" : "degraded"} size="sm" />
                      <div className="flex-1">
                        <span className="font-medium">{inc.provider}</span>
                        <span className="text-muted-foreground"> — {inc.message}</span>
                      </div>
                      <span className="text-xs text-muted-foreground shrink-0">{timeAgo(inc.startedAt)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <div className="grid lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-2 bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle>Request Volume by Provider</CardTitle>
                <CardDescription>24-hour utilization across configured providers</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[280px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={utilizationData}>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip
                        contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }}
                        formatter={(v: number, name: string) => [name === "requests" ? formatNumber(v) : formatCurrency(v), name === "requests" ? "Requests" : "Cost"]}
                      />
                      <Bar dataKey="requests" radius={[4, 4, 0, 0]}>
                        {utilizationData?.map((entry, i) => (
                          <Cell key={i} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle>System Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Overall uptime</span>
                      <span className="font-semibold">{data.summary.overallUptime.toFixed(2)}%</span>
                    </div>
                    <Progress value={data.summary.overallUptime} className="h-2" />
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Avg latency</span>
                      <span className="font-semibold">{formatLatency(data.summary.avgLatencyMs)}</span>
                    </div>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Direct APIs</span>
                    <span>{data.providers.filter((p) => p.connectionType === "direct" && p.configured).length} active</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Aggregators</span>
                    <span>{data.providers.filter((p) => p.connectionType === "aggregator" && p.configured).length} active</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Unconfigured</span>
                    <span className="text-muted-foreground">{data.summary.unconfigured}</span>
                  </div>
                </div>
                <p className="text-[11px] text-muted-foreground flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Last updated {timeAgo(data.lastUpdated)}
                </p>
              </CardContent>
            </Card>
          </div>

          <Card className="bg-card/50 backdrop-blur-sm border-border/50 overflow-hidden">
            <CardHeader>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <CardTitle>Provider Registry</CardTitle>
                  <CardDescription>Connection status, speed, and utilization metrics</CardDescription>
                </div>
                <Tabs value={filter} onValueChange={(v) => setFilter(v as typeof filter)}>
                  <TabsList>
                    <TabsTrigger value="all">All</TabsTrigger>
                    <TabsTrigger value="direct">Direct</TabsTrigger>
                    <TabsTrigger value="aggregator">Aggregators</TabsTrigger>
                  </TabsList>
                </Tabs>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border/50 bg-muted/20">
                      <th className="text-left py-3 px-3 font-medium text-muted-foreground">Provider</th>
                      <th className="text-left py-3 px-3 font-medium text-muted-foreground">Status</th>
                      <th className="text-right py-3 px-3 font-medium text-muted-foreground">Requests</th>
                      <th className="text-right py-3 px-3 font-medium text-muted-foreground">Latency</th>
                      <th className="text-right py-3 px-3 font-medium text-muted-foreground">Success</th>
                      <th className="text-right py-3 px-3 font-medium text-muted-foreground">Cost</th>
                      <th className="text-right py-3 px-3 font-medium text-muted-foreground">Uptime</th>
                      <th className="text-right py-3 px-3 font-medium text-muted-foreground">RPM</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered?.map((p) => (
                      <ProviderRow key={p.id} provider={p} />
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </AdminShell>
  )
}
