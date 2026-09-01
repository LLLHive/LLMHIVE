"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  DollarSign,
  Server,
  Sparkles,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react"
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { AdminShell } from "@/components/admin/admin-shell"
import { AdminAccessGate } from "@/components/admin/admin-access-gate"
import { MetricCard } from "@/components/admin/metric-card"
import { StatusBadge } from "@/components/admin/status-badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { formatCurrency, formatNumber, formatLatency, timeAgo } from "@/lib/admin/format"
import type { AdminStats } from "@/lib/admin/types"
import type { ProviderDashboard } from "@/lib/admin/types"
import type { ModelRankingsDashboard } from "@/lib/admin/types"

export default function AdminOverviewPage() {
  const [business, setBusiness] = useState<AdminStats | null>(null)
  const [providers, setProviders] = useState<ProviderDashboard | null>(null)
  const [models, setModels] = useState<ModelRankingsDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchAll = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [bizRes, provRes, modRes] = await Promise.all([
        fetch("/api/admin/business"),
        fetch("/api/admin/providers"),
        fetch("/api/admin/models"),
      ])

      if (!bizRes.ok) {
        setError(bizRes.status === 403 ? "Unauthorized — admin access required" : "Failed to load dashboard")
        return
      }

      const [biz, prov, mod] = await Promise.all([
        bizRes.json() as Promise<AdminStats>,
        provRes.ok ? (provRes.json() as Promise<ProviderDashboard>) : null,
        modRes.ok ? (modRes.json() as Promise<ModelRankingsDashboard>) : null,
      ])

      setBusiness(biz)
      setProviders(prov)
      setModels(mod)
    } catch {
      setError("Failed to connect to server")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 60_000)
    return () => clearInterval(interval)
  }, [fetchAll])

  if (error) {
    return (
      <AdminShell title="Overview" description="System health & key metrics">
        <AdminAccessGate message={error} />
      </AdminShell>
    )
  }

  const grossMargin = business
    ? Math.round((1 - business.usage.totalApiCost / Math.max(business.overview.mrr, 1)) * 100)
    : 0

  return (
    <AdminShell
      title="Overview"
      description="Real-time command center for LLMHive operations"
      onRefresh={fetchAll}
      refreshing={loading}
    >
      {loading && !business ? (
        <div className="space-y-6">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-28 rounded-xl" />
            ))}
          </div>
          <Skeleton className="h-80 rounded-xl" />
        </div>
      ) : business && (
        <div className="space-y-8">
          {/* System status banner */}
          {providers && (
            <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border/50 bg-card/50 backdrop-blur-sm px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
                </span>
                <span className="text-sm font-medium">
                  {providers.summary.healthy}/{providers.summary.totalProviders} providers healthy
                </span>
              </div>
              <div className="h-4 w-px bg-border hidden sm:block" />
              <span className="text-sm text-muted-foreground">
                {formatNumber(providers.summary.totalRequests24h)} requests · {formatLatency(providers.summary.avgLatencyMs)} avg latency
              </span>
              {(providers.summary.down > 0 || providers.summary.degraded > 0) && (
                <Badge variant="outline" className="border-amber-500/30 text-amber-500 ml-auto">
                  {providers.summary.down + providers.summary.degraded} incident{providers.summary.down + providers.summary.degraded !== 1 ? "s" : ""}
                </Badge>
              )}
            </div>
          )}

          {/* KPI row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="Monthly Revenue"
              value={formatCurrency(business.overview.mrr)}
              icon={DollarSign}
              trend="up"
              trendValue={`+${business.revenue.growthPercent}%`}
              variant="bronze"
            />
            <MetricCard
              title="Active Subscribers"
              value={formatNumber(business.overview.activeSubscribers)}
              subtitle={`${formatNumber(business.overview.totalUsers)} total users`}
              icon={Users}
            />
            <MetricCard
              title="Provider Uptime"
              value={providers ? `${providers.summary.overallUptime.toFixed(1)}%` : "—"}
              subtitle={providers ? `${providers.summary.healthy} healthy` : undefined}
              icon={Server}
              variant={providers && providers.summary.down > 0 ? "warning" : "success"}
            />
            <MetricCard
              title="New Top Models"
              value={models?.summary.newModelsCount ?? "—"}
              subtitle={`${models?.summary.freeInTop10 ?? 0} free · ${models?.summary.paidInTop10 ?? 0} paid`}
              icon={Sparkles}
              variant="bronze"
            />
          </div>

          <div className="grid lg:grid-cols-3 gap-6">
            {/* Provider health snapshot */}
            <Card className="lg:col-span-2 bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Server className="h-5 w-5 text-[var(--bronze)]" />
                    Provider Health
                  </CardTitle>
                  <CardDescription>Direct connections & aggregators</CardDescription>
                </div>
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/admin/providers">
                    View all <ArrowRight className="h-4 w-4 ml-1" />
                  </Link>
                </Button>
              </CardHeader>
              <CardContent>
                {providers ? (
                  <div className="space-y-3">
                    {providers.providers.slice(0, 8).map((p) => (
                      <div
                        key={p.id}
                        className="flex items-center gap-4 rounded-lg border border-border/30 bg-muted/20 px-4 py-3"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-medium text-sm">{p.name}</span>
                            <StatusBadge status={p.status} size="sm" />
                          </div>
                          <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                            <span>{formatNumber(p.requests24h)} req</span>
                            <span>{formatLatency(p.avgLatencyMs)}</span>
                            <span>{p.successRate.toFixed(1)}% success</span>
                          </div>
                        </div>
                        {p.rpmLimit && p.configured && (
                          <div className="w-24 hidden sm:block">
                            <div className="text-[10px] text-muted-foreground mb-1 text-right">
                              RPM {Math.round(((p.rpmUsed ?? 0) / p.rpmLimit) * 100)}%
                            </div>
                            <Progress value={((p.rpmUsed ?? 0) / p.rpmLimit) * 100} className="h-1.5" />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <Skeleton className="h-48" />
                )}
              </CardContent>
            </Card>

            {/* Business snapshot */}
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-[var(--bronze)]" />
                  Business
                </CardTitle>
                <CardDescription>Revenue & retention</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Gross margin</span>
                    <span className="font-semibold text-emerald-500">{grossMargin}%</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Monthly retention</span>
                    <span className="font-semibold">{business.retention.monthlyRetentionRate}%</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Avg retention</span>
                    <span className="font-semibold">{business.retention.avgRetentionDays} days</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">LTV / CAC</span>
                    <span className="font-semibold">{business.retention.ltvCacRatio}x</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">NRR</span>
                    <span className="font-semibold text-emerald-500">{business.retention.netRevenueRetention}%</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Churn rate</span>
                    <span className={`font-semibold ${business.efficiency.churnRate > 5 ? "text-red-500" : "text-emerald-500"}`}>
                      {business.efficiency.churnRate}%
                    </span>
                  </div>
                </div>
                <Button variant="outline" className="w-full" asChild>
                  <Link href="/admin/business">
                    Full business dashboard <ArrowRight className="h-4 w-4 ml-2" />
                  </Link>
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* New models + activity */}
          <div className="grid lg:grid-cols-2 gap-6">
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-[var(--bronze)]" />
                    New Models in Top 10
                  </CardTitle>
                  <CardDescription>Across all category rankings</CardDescription>
                </div>
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/admin/models">View all</Link>
                </Button>
              </CardHeader>
              <CardContent>
                {models && models.newModels.length > 0 ? (
                  <div className="space-y-2">
                    {models.newModels.slice(0, 6).map((m) => (
                      <div key={m.modelId} className="flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-muted/30">
                        <Badge variant="outline" className="text-[10px] shrink-0 w-8 justify-center">#{m.rank}</Badge>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium truncate">{m.modelName}</div>
                          <div className="text-xs text-muted-foreground">{m.categoryLabel} · {m.author}</div>
                        </div>
                        <Badge className={m.isFree ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" : "bg-blue-500/10 text-blue-400 border-blue-500/20"}>
                          {m.isFree ? "Free" : "Paid"}
                        </Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-8">No new models detected</p>
                )}
              </CardContent>
            </Card>

            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5 text-[var(--bronze)]" />
                  Recent Activity
                </CardTitle>
                <CardDescription>Subscription & billing events</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-1">
                  {business.recentActivity.slice(0, 6).map((a, i) => (
                    <div key={i} className="flex items-center gap-3 py-2.5 border-b border-border/30 last:border-0">
                      {a.type === "subscription" || a.type === "upgrade" ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                      ) : (
                        <AlertTriangle className="h-4 w-4 text-red-500 shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm truncate">{a.description}</p>
                        <p className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" /> {timeAgo(a.timestamp)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Usage trend */}
          {providers && providers.latencyTrend.length > 0 && (
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5 text-[var(--bronze)]" />
                  Provider Latency Trend (24h)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[220px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={providers.latencyTrend.slice(0, 12)}>
                      <defs>
                        <linearGradient id="latencyGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="var(--bronze)" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="var(--bronze)" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                      <XAxis dataKey="time" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                      <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} unit="ms" />
                      <Tooltip
                        contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }}
                        formatter={(v: number) => [`${v}ms`, "Latency"]}
                      />
                      <Area type="monotone" dataKey="latency" stroke="var(--bronze)" fill="url(#latencyGrad)" strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </AdminShell>
  )
}
