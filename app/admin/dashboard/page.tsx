"use client"

import { useState, useEffect, useCallback } from "react"
import Link from "next/link"
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Users,
  DollarSign,
  Zap,
  TrendingUp,
  TrendingDown,
  Activity,
  Crown,
  RefreshCw,
  ArrowUpRight,
  ArrowDownRight,
  BarChart3,
  Settings,
  Shield,
  Clock,
  AlertCircle,
  CheckCircle,
  UserPlus,
  UserMinus,
} from "lucide-react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  Legend,
} from "recharts"

interface TierStats {
  tier: string;
  count: number;
  mrr: number;
  eliteQueriesUsed: number;
  eliteQueriesLimit: number;
}

interface AdminStats {
  overview: {
    totalUsers: number;
    activeSubscribers: number;
    freeUsers: number;
    mrr: number;
    arr: number;
    totalQueriesThisMonth: number;
    averageQueriesPerUser: number;
  };
  tiers: TierStats[];
  revenue: {
    thisMonth: number;
    lastMonth: number;
    growthPercent: number;
    projectedArr: number;
  };
  usage: {
    eliteQueriesUsed: number;
    eliteQueriesTotal: number;
    standardQueriesUsed: number;
    budgetQueriesUsed: number;
    averageCostPerQuery: number;
    totalApiCost: number;
  };
  efficiency: {
    eliteUtilization: number;
    throttleRate: number;
    upgradeConversion: number;
    churnRate: number;
  };
  recentActivity: Array<{
    type: string;
    description: string;
    timestamp: string;
    tier?: string;
  }>;
}

const TIER_COLORS: Record<string, string> = {
  free: "#6b7280",
  lite: "#10b981",
  pro: "#3b82f6",
  enterprise: "#8b5cf6",
  maximum: "#f59e0b",
}

const TIER_LABELS: Record<string, string> = {
  free: "Free Trial",
  lite: "Lite",
  pro: "Pro",
  enterprise: "Enterprise",
  maximum: "Maximum",
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`
  }
  return num.toString()
}

function StatCard({ 
  title, 
  value, 
  description, 
  icon: Icon, 
  trend,
  trendValue,
  color = "bronze"
}: { 
  title: string
  value: string | number
  description?: string
  icon: React.ComponentType<{ className?: string }>
  trend?: "up" | "down" | "neutral"
  trendValue?: string
  color?: string
}) {
  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className={`h-4 w-4 text-${color === "bronze" ? "[var(--bronze)]" : color}`} />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {(description || trendValue) && (
          <div className="flex items-center gap-2 mt-1">
            {trend && (
              <span className={`flex items-center text-xs ${
                trend === "up" ? "text-green-500" : 
                trend === "down" ? "text-red-500" : "text-muted-foreground"
              }`}>
                {trend === "up" ? <ArrowUpRight className="h-3 w-3" /> : 
                 trend === "down" ? <ArrowDownRight className="h-3 w-3" /> : null}
                {trendValue}
              </span>
            )}
            {description && (
              <span className="text-xs text-muted-foreground">{description}</span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function ActivityItem({ 
  type, 
  description, 
  timestamp, 
  tier 
}: { 
  type: string
  description: string
  timestamp: string
  tier?: string
}) {
  const getIcon = () => {
    switch (type) {
      case "subscription": return <UserPlus className="h-4 w-4 text-green-500" />
      case "upgrade": return <TrendingUp className="h-4 w-4 text-blue-500" />
      case "cancel": return <UserMinus className="h-4 w-4 text-red-500" />
      default: return <Activity className="h-4 w-4 text-muted-foreground" />
    }
  }

  const timeAgo = () => {
    const diff = Date.now() - new Date(timestamp).getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    if (minutes < 60) return `${minutes}m ago`
    if (hours < 24) return `${hours}h ago`
    return new Date(timestamp).toLocaleDateString()
  }

  return (
    <div className="flex items-center gap-3 py-3 border-b border-border/50 last:border-0">
      <div className="p-2 rounded-lg bg-muted/50">
        {getIcon()}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{description}</p>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">{timeAgo()}</span>
          {tier && (
            <Badge 
              variant="outline" 
              className="text-xs"
              style={{ borderColor: TIER_COLORS[tier], color: TIER_COLORS[tier] }}
            >
              {TIER_LABELS[tier]}
            </Badge>
          )}
        </div>
      </div>
    </div>
  )
}

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStats = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch("/api/admin/stats")
      if (!response.ok) {
        if (response.status === 403) {
          setError("Unauthorized - Admin access required")
        } else {
          setError("Failed to load dashboard data")
        }
        return
      }
      const data = await response.json()
      setStats(data)
    } catch (err) {
      setError("Failed to connect to server")
      console.error("Error fetching admin stats:", err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStats()
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchStats, 30000)
    return () => clearInterval(interval)
  }, [fetchStats])

  if (loading && !stats) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <RefreshCw className="h-8 w-8 animate-spin text-[var(--bronze)]" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center gap-4">
              <Shield className="h-12 w-12 text-red-500" />
              <h2 className="text-xl font-bold">{error}</h2>
              <p className="text-muted-foreground text-center">
                You need admin privileges to access this dashboard.
              </p>
              <Link href="/">
                <Button>Return to Home</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!stats) return null

  // Prepare chart data
  const tierDistributionData = stats.tiers.map(t => ({
    name: TIER_LABELS[t.tier],
    value: t.count,
    fill: TIER_COLORS[t.tier],
  }))

  const revenueByTierData = stats.tiers.filter(t => t.mrr > 0).map(t => ({
    name: TIER_LABELS[t.tier],
    mrr: t.mrr,
    fill: TIER_COLORS[t.tier],
  }))

  const usageData = [
    { name: "ELITE", used: stats.usage.eliteQueriesUsed, fill: "#10b981" },
    { name: "STANDARD", used: stats.usage.standardQueriesUsed, fill: "#eab308" },
    { name: "BUDGET", used: stats.usage.budgetQueriesUsed, fill: "#f97316" },
  ]

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2">
              <img src="/logo.png" alt="LLMHive" className="h-8 w-8" />
              <span className="font-display text-xl font-bold text-[var(--bronze)]">LLMHive</span>
            </Link>
            <Badge variant="outline" className="text-[var(--bronze)] border-[var(--bronze)]">
              <Shield className="h-3 w-3 mr-1" />
              Admin
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={fetchStats}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Link href="/admin/analytics">
              <Button variant="outline" size="sm">
                <BarChart3 className="h-4 w-4 mr-2" />
                Analytics
              </Button>
            </Link>
            <Link href="/settings">
              <Button variant="ghost" size="icon">
                <Settings className="h-5 w-5" />
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 space-y-8">
        {/* Page Title */}
        <div>
          <h1 className="text-3xl font-display font-bold">Business Dashboard</h1>
          <p className="text-muted-foreground">
            Real-time metrics for LLMHive operations
          </p>
        </div>

        {/* Overview Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <StatCard
            title="Monthly Revenue"
            value={formatCurrency(stats.overview.mrr)}
            icon={DollarSign}
            trend="up"
            trendValue={`${stats.revenue.growthPercent}%`}
            color="green-500"
          />
          <StatCard
            title="Annual Run Rate"
            value={formatCurrency(stats.overview.arr)}
            icon={TrendingUp}
            description="Projected"
            color="blue-500"
          />
          <StatCard
            title="Total Users"
            value={formatNumber(stats.overview.totalUsers)}
            icon={Users}
            description={`${stats.overview.activeSubscribers} paid`}
          />
          <StatCard
            title="Queries/Month"
            value={formatNumber(stats.overview.totalQueriesThisMonth)}
            icon={Zap}
            description={`${stats.overview.averageQueriesPerUser}/user avg`}
            color="yellow-500"
          />
          <StatCard
            title="API Costs"
            value={formatCurrency(stats.usage.totalApiCost)}
            icon={Activity}
            description={`$${stats.usage.averageCostPerQuery.toFixed(3)}/query`}
            color="red-500"
          />
          <StatCard
            title="Gross Margin"
            value={`${Math.round((1 - stats.usage.totalApiCost / stats.overview.mrr) * 100)}%`}
            icon={Crown}
            trend={(1 - stats.usage.totalApiCost / stats.overview.mrr) > 0.7 ? "up" : "down"}
            trendValue="Target: 70%+"
            color="[var(--bronze)]"
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left Column - Charts */}
          <div className="lg:col-span-2 space-y-6">
            {/* Tier Breakdown */}
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  Subscription Tiers
                </CardTitle>
                <CardDescription>
                  User distribution and revenue by tier
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="users">
                  <TabsList className="mb-4">
                    <TabsTrigger value="users">Users</TabsTrigger>
                    <TabsTrigger value="revenue">Revenue</TabsTrigger>
                    <TabsTrigger value="usage">ELITE Usage</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="users">
                    <div className="h-[300px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={tierDistributionData}
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={100}
                            paddingAngle={2}
                            dataKey="value"
                            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                          >
                            {tierDistributionData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.fill} />
                            ))}
                          </Pie>
                          <Tooltip />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="revenue">
                    <div className="h-[300px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={revenueByTierData}>
                          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                          <XAxis dataKey="name" tick={{ fill: "hsl(var(--muted-foreground))" }} />
                          <YAxis tick={{ fill: "hsl(var(--muted-foreground))" }} />
                          <Tooltip 
                            formatter={(value: number) => formatCurrency(value)}
                            contentStyle={{ 
                              background: "hsl(var(--card))", 
                              border: "1px solid hsl(var(--border))" 
                            }}
                          />
                          <Bar dataKey="mrr" name="MRR" radius={[4, 4, 0, 0]}>
                            {revenueByTierData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.fill} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="usage">
                    <div className="h-[300px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={usageData} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                          <XAxis type="number" tick={{ fill: "hsl(var(--muted-foreground))" }} />
                          <YAxis dataKey="name" type="category" tick={{ fill: "hsl(var(--muted-foreground))" }} />
                          <Tooltip 
                            formatter={(value: number) => formatNumber(value)}
                            contentStyle={{ 
                              background: "hsl(var(--card))", 
                              border: "1px solid hsl(var(--border))" 
                            }}
                          />
                          <Bar dataKey="used" name="Queries" radius={[0, 4, 4, 0]}>
                            {usageData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.fill} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>

            {/* Tier Details Table */}
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle>Tier Performance</CardTitle>
                <CardDescription>Detailed breakdown by subscription tier</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border/50">
                        <th className="text-left py-3 px-2 font-medium">Tier</th>
                        <th className="text-right py-3 px-2 font-medium">Users</th>
                        <th className="text-right py-3 px-2 font-medium">MRR</th>
                        <th className="text-right py-3 px-2 font-medium">ARPU</th>
                        <th className="text-right py-3 px-2 font-medium">ELITE Used</th>
                        <th className="text-right py-3 px-2 font-medium">Utilization</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.tiers.map((tier) => {
                        const utilization = tier.eliteQueriesLimit > 0 
                          ? (tier.eliteQueriesUsed / tier.eliteQueriesLimit) * 100 
                          : 0
                        return (
                          <tr key={tier.tier} className="border-b border-border/50 last:border-0">
                            <td className="py-3 px-2">
                              <div className="flex items-center gap-2">
                                <div 
                                  className="w-3 h-3 rounded-full" 
                                  style={{ backgroundColor: TIER_COLORS[tier.tier] }}
                                />
                                <span className="font-medium">{TIER_LABELS[tier.tier]}</span>
                              </div>
                            </td>
                            <td className="text-right py-3 px-2">{tier.count.toLocaleString()}</td>
                            <td className="text-right py-3 px-2">{formatCurrency(tier.mrr)}</td>
                            <td className="text-right py-3 px-2">
                              {tier.count > 0 ? formatCurrency(tier.mrr / tier.count) : "-"}
                            </td>
                            <td className="text-right py-3 px-2">{formatNumber(tier.eliteQueriesUsed)}</td>
                            <td className="text-right py-3 px-2">
                              <div className="flex items-center justify-end gap-2">
                                <Progress value={utilization} className="w-16 h-2" />
                                <span className="text-xs text-muted-foreground w-10">
                                  {utilization.toFixed(0)}%
                                </span>
                              </div>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right Column - Activity & Efficiency */}
          <div className="space-y-6">
            {/* Efficiency Metrics */}
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Key Metrics
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-muted-foreground">ELITE Utilization</span>
                    <span className="text-sm font-medium">{stats.efficiency.eliteUtilization.toFixed(1)}%</span>
                  </div>
                  <Progress value={stats.efficiency.eliteUtilization} className="h-2" />
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-muted-foreground">Throttle Rate</span>
                    <span className={`text-sm font-medium ${stats.efficiency.throttleRate > 20 ? "text-red-500" : "text-green-500"}`}>
                      {stats.efficiency.throttleRate.toFixed(1)}%
                    </span>
                  </div>
                  <Progress value={stats.efficiency.throttleRate} className="h-2" />
                  <p className="text-xs text-muted-foreground mt-1">Users hitting ELITE quota limits</p>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-muted-foreground">Upgrade Conversion</span>
                    <span className="text-sm font-medium text-green-500">{stats.efficiency.upgradeConversion.toFixed(1)}%</span>
                  </div>
                  <Progress value={stats.efficiency.upgradeConversion} className="h-2" />
                  <p className="text-xs text-muted-foreground mt-1">Free → Paid conversion this month</p>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-muted-foreground">Churn Rate</span>
                    <span className={`text-sm font-medium ${stats.efficiency.churnRate > 5 ? "text-red-500" : "text-green-500"}`}>
                      {stats.efficiency.churnRate.toFixed(1)}%
                    </span>
                  </div>
                  <Progress value={stats.efficiency.churnRate * 10} className="h-2" />
                  <p className="text-xs text-muted-foreground mt-1">Monthly subscription churn</p>
                </div>
              </CardContent>
            </Card>

            {/* Recent Activity */}
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  Recent Activity
                </CardTitle>
                <CardDescription>Latest subscription events</CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[300px]">
                  {stats.recentActivity.map((activity, i) => (
                    <ActivityItem key={i} {...activity} />
                  ))}
                </ScrollArea>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Link href="/admin/analytics" className="block">
                  <Button variant="outline" className="w-full justify-start">
                    <BarChart3 className="h-4 w-4 mr-2" />
                    View Detailed Analytics
                  </Button>
                </Link>
                <Link href="/admin/benchmarks" className="block">
                  <Button variant="outline" className="w-full justify-start">
                    <Zap className="h-4 w-4 mr-2" />
                    Run Benchmarks
                  </Button>
                </Link>
                <a 
                  href="https://dashboard.stripe.com" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="block"
                >
                  <Button variant="outline" className="w-full justify-start">
                    <DollarSign className="h-4 w-4 mr-2" />
                    Stripe Dashboard
                    <ArrowUpRight className="h-3 w-3 ml-auto" />
                  </Button>
                </a>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  )
}
