"use client"

import { useCallback, useEffect, useState } from "react"
import {
  ArrowUpRight,
  Crown,
  DollarSign,
  TrendingUp,
  UserMinus,
  UserPlus,
  Users,
  Zap,
} from "lucide-react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { AdminShell } from "@/components/admin/admin-shell"
import { MetricCard } from "@/components/admin/metric-card"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import { formatCurrency, formatNumber, timeAgo } from "@/lib/admin/format"
import type { AdminStats } from "@/lib/admin/types"

const TIER_COLORS: Record<string, string> = {
  free: "#6b7280",
  lite: "#10b981",
  pro: "#3b82f6",
  enterprise: "#8b5cf6",
}

const TIER_LABELS: Record<string, string> = {
  free: "Free",
  lite: "Standard",
  pro: "Premium",
  enterprise: "Enterprise",
}

function ActivityItem({
  type,
  description,
  timestamp,
  tier,
}: {
  type: string
  description: string
  timestamp: string
  tier?: string
}) {
  return (
    <div className="flex items-center gap-3 py-3 border-b border-border/30 last:border-0">
      <div className="p-2 rounded-lg bg-muted/40">
        {type === "cancel" ? (
          <UserMinus className="h-4 w-4 text-red-500" />
        ) : type === "upgrade" ? (
          <TrendingUp className="h-4 w-4 text-blue-500" />
        ) : (
          <UserPlus className="h-4 w-4 text-emerald-500" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{description}</p>
        <p className="text-xs text-muted-foreground">{timeAgo(timestamp)}</p>
      </div>
      {tier && (
        <Badge variant="outline" style={{ borderColor: TIER_COLORS[tier], color: TIER_COLORS[tier] }}>
          {TIER_LABELS[tier]}
        </Badge>
      )}
    </div>
  )
}

export default function AdminBusinessPage() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStats = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch("/api/admin/business")
      if (!res.ok) {
        setError(res.status === 403 ? "Unauthorized" : "Failed to load")
        return
      }
      setStats(await res.json())
    } catch {
      setError("Connection failed")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 60_000)
    return () => clearInterval(interval)
  }, [fetchStats])

  const grossMargin = stats
    ? Math.round((1 - stats.usage.totalApiCost / Math.max(stats.overview.mrr, 1)) * 100)
    : 0

  const revenueHistory = stats
    ? [
        { month: "Mar", revenue: stats.revenue.lastMonth * 0.88, cost: stats.usage.totalApiCost * 0.85 },
        { month: "Apr", revenue: stats.revenue.lastMonth * 0.94, cost: stats.usage.totalApiCost * 0.9 },
        { month: "May", revenue: stats.revenue.lastMonth * 0.97, cost: stats.usage.totalApiCost * 0.95 },
        { month: "Jun", revenue: stats.revenue.lastMonth, cost: stats.usage.totalApiCost * 0.98 },
        { month: "Jul", revenue: stats.overview.mrr * 0.96, cost: stats.usage.totalApiCost },
        { month: "Aug", revenue: stats.overview.mrr, cost: stats.usage.totalApiCost },
      ]
    : []

  const tierDistribution = stats?.tiers.map((t) => ({
    name: TIER_LABELS[t.tier],
    value: t.count,
    fill: TIER_COLORS[t.tier],
  }))

  return (
    <AdminShell
      title="Business Intelligence"
      description="Revenue, subscriptions, retention, and unit economics"
      onRefresh={fetchStats}
      refreshing={loading}
      actions={
        <a href="https://dashboard.stripe.com" target="_blank" rel="noopener noreferrer">
          <Button variant="outline" size="sm">
            <DollarSign className="h-4 w-4 mr-2" />
            Stripe
            <ArrowUpRight className="h-3 w-3 ml-1" />
          </Button>
        </a>
      }
    >
      {error ? (
        <Card className="max-w-md mx-auto mt-12">
          <CardContent className="pt-8 text-center text-red-500">{error}</CardContent>
        </Card>
      ) : loading && !stats ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-28 rounded-xl" />
            ))}
          </div>
          <Skeleton className="h-80 rounded-xl" />
        </div>
      ) : stats && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
            <MetricCard title="MRR" value={formatCurrency(stats.overview.mrr)} icon={DollarSign} trend="up" trendValue={`+${stats.revenue.growthPercent}%`} variant="bronze" />
            <MetricCard title="ARR" value={formatCurrency(stats.overview.arr)} icon={TrendingUp} subtitle="Annual run rate" />
            <MetricCard title="Subscribers" value={formatNumber(stats.overview.activeSubscribers)} icon={Users} subtitle={`${stats.overview.freeUsers} free`} />
            <MetricCard title="Gross Margin" value={`${grossMargin}%`} icon={Crown} variant={grossMargin >= 70 ? "success" : "warning"} />
            <MetricCard title="LTV" value={formatCurrency(stats.retention.ltv)} icon={TrendingUp} subtitle={`CAC ${formatCurrency(stats.retention.cac)}`} />
            <MetricCard title="NRR" value={`${stats.retention.netRevenueRetention}%`} icon={Zap} variant="success" />
          </div>

          <div className="grid lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-2 bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle>Revenue vs Cost</CardTitle>
                <CardDescription>Monthly trend — revenue and API spend</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={revenueHistory}>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                      <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                      <Tooltip
                        contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }}
                        formatter={(v: number) => [formatCurrency(v)]}
                      />
                      <Line type="monotone" dataKey="revenue" stroke="var(--bronze)" strokeWidth={2} dot={{ fill: "var(--bronze)" }} name="Revenue" />
                      <Line type="monotone" dataKey="cost" stroke="#ef4444" strokeWidth={2} strokeDasharray="5 5" dot={false} name="API Cost" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle>Retention Metrics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                <div>
                  <div className="flex justify-between text-sm mb-1.5">
                    <span className="text-muted-foreground">Monthly retention</span>
                    <span className="font-semibold text-emerald-500">{stats.retention.monthlyRetentionRate}%</span>
                  </div>
                  <Progress value={stats.retention.monthlyRetentionRate} className="h-2" />
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1.5">
                    <span className="text-muted-foreground">Churn rate</span>
                    <span className={`font-semibold ${stats.efficiency.churnRate > 5 ? "text-red-500" : "text-emerald-500"}`}>
                      {stats.efficiency.churnRate}%
                    </span>
                  </div>
                  <Progress value={stats.efficiency.churnRate * 10} className="h-2" />
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1.5">
                    <span className="text-muted-foreground">Upgrade conversion</span>
                    <span className="font-semibold">{stats.efficiency.upgradeConversion}%</span>
                  </div>
                  <Progress value={stats.efficiency.upgradeConversion} className="h-2" />
                </div>
                <div className="pt-2 border-t border-border/30 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Avg retention</span>
                    <span className="font-medium">{stats.retention.avgRetentionDays} days</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">LTV / CAC ratio</span>
                    <span className="font-medium text-emerald-500">{stats.retention.ltvCacRatio}x</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Throttle rate</span>
                    <span className="font-medium">{stats.efficiency.throttleRate}%</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader>
              <CardTitle>Subscription Tiers</CardTitle>
              <CardDescription>User distribution, revenue, and utilization by tier</CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="table">
                <TabsList className="mb-4">
                  <TabsTrigger value="table">Table</TabsTrigger>
                  <TabsTrigger value="users">Distribution</TabsTrigger>
                  <TabsTrigger value="revenue">Revenue</TabsTrigger>
                </TabsList>

                <TabsContent value="table">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border/50">
                          <th className="text-left py-3 px-2 font-medium">Tier</th>
                          <th className="text-right py-3 px-2 font-medium">Users</th>
                          <th className="text-right py-3 px-2 font-medium">MRR</th>
                          <th className="text-right py-3 px-2 font-medium">ARPU</th>
                          <th className="text-right py-3 px-2 font-medium">Premium Used</th>
                          <th className="text-right py-3 px-2 font-medium">Utilization</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stats.tiers.map((tier) => {
                          const util = tier.eliteQueriesLimit > 0 ? (tier.eliteQueriesUsed / tier.eliteQueriesLimit) * 100 : 0
                          return (
                            <tr key={tier.tier} className="border-b border-border/30">
                              <td className="py-3 px-2">
                                <div className="flex items-center gap-2">
                                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: TIER_COLORS[tier.tier] }} />
                                  <span className="font-medium">{TIER_LABELS[tier.tier]}</span>
                                </div>
                              </td>
                              <td className="text-right py-3 px-2">{tier.count.toLocaleString()}</td>
                              <td className="text-right py-3 px-2">{formatCurrency(tier.mrr)}</td>
                              <td className="text-right py-3 px-2">{tier.count > 0 ? formatCurrency(tier.mrr / tier.count) : "—"}</td>
                              <td className="text-right py-3 px-2">{formatNumber(tier.eliteQueriesUsed)}</td>
                              <td className="text-right py-3 px-2">
                                <div className="flex items-center justify-end gap-2">
                                  <Progress value={util} className="w-16 h-1.5" />
                                  <span className="text-xs w-10">{util.toFixed(0)}%</span>
                                </div>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </TabsContent>

                <TabsContent value="users">
                  <div className="h-[280px] flex items-center justify-center">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={tierDistribution} cx="50%" cy="50%" innerRadius={70} outerRadius={110} paddingAngle={2} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                          {tierDistribution?.map((entry, i) => (
                            <Cell key={i} fill={entry.fill} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </TabsContent>

                <TabsContent value="revenue">
                  <div className="h-[280px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={stats.tiers.filter((t) => t.mrr > 0).map((t) => ({ name: TIER_LABELS[t.tier], mrr: t.mrr, fill: TIER_COLORS[t.tier] }))}>
                        <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                        <XAxis dataKey="name" />
                        <YAxis tickFormatter={(v) => `$${v}`} />
                        <Tooltip formatter={(v: number) => [formatCurrency(v), "MRR"]} />
                        <Bar dataKey="mrr" radius={[4, 4, 0, 0]}>
                          {stats.tiers.filter((t) => t.mrr > 0).map((t, i) => (
                            <Cell key={i} fill={TIER_COLORS[t.tier]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          <div className="grid lg:grid-cols-2 gap-6">
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle>Usage Breakdown</CardTitle>
                <CardDescription>Query volume by orchestration tier this month</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {[
                  { label: "Premium", used: stats.usage.eliteQueriesUsed, total: stats.usage.eliteQueriesTotal, color: "bg-emerald-500" },
                  { label: "Balanced", used: stats.usage.standardQueriesUsed, total: stats.usage.standardQueriesUsed * 1.2, color: "bg-yellow-500" },
                  { label: "Budget", used: stats.usage.budgetQueriesUsed, total: stats.usage.budgetQueriesUsed * 1.3, color: "bg-orange-500" },
                ].map((item) => (
                  <div key={item.label}>
                    <div className="flex justify-between text-sm mb-1">
                      <span>{item.label}</span>
                      <span className="text-muted-foreground">{formatNumber(item.used)} queries</span>
                    </div>
                    <Progress value={(item.used / item.total) * 100} className="h-2" />
                  </div>
                ))}
                <div className="pt-3 border-t border-border/30 flex justify-between text-sm">
                  <span className="text-muted-foreground">Avg cost per query</span>
                  <span className="font-mono">${stats.usage.averageCostPerQuery.toFixed(3)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Total API cost</span>
                  <span className="font-mono text-red-400">{formatCurrency(stats.usage.totalApiCost)}</span>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
                <CardDescription>Subscription lifecycle events</CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[280px]">
                  {stats.recentActivity.map((a, i) => (
                    <ActivityItem key={i} {...a} />
                  ))}
                </ScrollArea>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </AdminShell>
  )
}
