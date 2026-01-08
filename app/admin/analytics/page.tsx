"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  ThumbsUp, 
  ThumbsDown, 
  Copy, 
  Share2, 
  RefreshCw, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  BarChart3,
  PieChart as PieChartIcon,
  Activity,
  Calendar,
  ArrowLeft,
} from "lucide-react"
import Link from "next/link"
import { cn } from "@/lib/utils"
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadialBarChart,
  RadialBar,
} from "recharts"

interface FeedbackStats {
  period_days: number
  totals: {
    thumbs_up: number
    thumbs_down: number
    copies: number
    shares: number
    regenerations: number
    total: number
  }
  overall_satisfaction: number
  daily_stats: Array<{
    date: string
    thumbs_up: number
    thumbs_down: number
    copies: number
    shares: number
    regenerations: number
    total: number
    satisfaction_rate: number
  }>
  model_stats: Array<{
    model: string
    thumbs_up: number
    thumbs_down: number
    satisfaction: number
  }>
  domain_stats: Array<{
    domain: string
    count: number
    satisfaction: number
  }>
  trends: {
    satisfaction_trend: "up" | "down" | "stable"
    engagement_trend: "up" | "down" | "stable"
    quality_score: number
  }
}

// Chart colors
const COLORS = {
  bronze: "hsl(30, 72%, 45%)",
  gold: "hsl(42, 87%, 55%)",
  green: "hsl(142, 76%, 36%)",
  red: "hsl(0, 84%, 60%)",
  blue: "hsl(217, 91%, 60%)",
  purple: "hsl(262, 83%, 58%)",
  orange: "hsl(25, 95%, 53%)",
  cyan: "hsl(187, 92%, 40%)",
}

const PIE_COLORS = [COLORS.bronze, COLORS.green, COLORS.blue, COLORS.purple, COLORS.orange]

function TrendIcon({ trend }: { trend: "up" | "down" | "stable" }) {
  if (trend === "up") return <TrendingUp className="h-4 w-4 text-green-500" />
  if (trend === "down") return <TrendingDown className="h-4 w-4 text-red-500" />
  return <Minus className="h-4 w-4 text-yellow-500" />
}

function StatCard({ 
  title, 
  value, 
  icon: Icon, 
  description,
  trend,
  color = "bronze"
}: { 
  title: string
  value: string | number
  icon: any
  description?: string
  trend?: "up" | "down" | "stable"
  color?: string
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className={cn("h-4 w-4", `text-${color === "bronze" ? "[var(--bronze)]" : color}`)} />
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-2">
          <div className="text-2xl font-bold">{value}</div>
          {trend && <TrendIcon trend={trend} />}
        </div>
        {description && (
          <p className="text-xs text-muted-foreground mt-1">{description}</p>
        )}
      </CardContent>
    </Card>
  )
}

// Custom tooltip for charts
function CustomTooltip({ active, payload, label }: any) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-popover border border-border rounded-lg p-3 shadow-lg">
        <p className="text-sm font-medium mb-1">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-xs" style={{ color: entry.color }}>
            {entry.name}: {entry.value}
          </p>
        ))}
      </div>
    )
  }
  return null
}

// Satisfaction Gauge using RadialBarChart
function SatisfactionGauge({ value }: { value: number }) {
  const percentage = Math.round(value * 100)
  const color = percentage >= 80 ? COLORS.green : percentage >= 60 ? COLORS.orange : COLORS.red
  
  const data = [{ name: "Satisfaction", value: percentage, fill: color }]
  
  return (
    <div className="flex flex-col items-center justify-center p-4">
      <ResponsiveContainer width={200} height={200}>
        <RadialBarChart
          cx="50%"
          cy="50%"
          innerRadius="70%"
          outerRadius="100%"
          barSize={20}
          data={data}
          startAngle={180}
          endAngle={0}
        >
          <RadialBar
            dataKey="value"
            cornerRadius={10}
            background={{ fill: "hsl(var(--muted))" }}
          />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="mt-[-100px] flex flex-col items-center">
        <span className="text-4xl font-bold" style={{ color }}>{percentage}%</span>
        <span className="text-sm text-muted-foreground">Satisfaction</span>
      </div>
    </div>
  )
}

export default function FeedbackAnalyticsPage() {
  const [stats, setStats] = useState<FeedbackStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [selectedPeriod, setSelectedPeriod] = useState("30")

  const fetchStats = useCallback(async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`/api/analytics/feedback?days=${selectedPeriod}`)
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (error) {
      console.error("Failed to fetch analytics:", error)
    } finally {
      setIsLoading(false)
    }
  }, [selectedPeriod])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  if (isLoading) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="h-8 w-8 animate-spin text-[var(--bronze)]" />
        </div>
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="text-center">
          <p className="text-muted-foreground">No analytics data available</p>
        </div>
      </div>
    )
  }

  // Prepare data for charts
  const feedbackBreakdownData = [
    { name: "Thumbs Up", value: stats.totals.thumbs_up, color: COLORS.green },
    { name: "Thumbs Down", value: stats.totals.thumbs_down, color: COLORS.red },
    { name: "Copies", value: stats.totals.copies, color: COLORS.blue },
    { name: "Shares", value: stats.totals.shares, color: COLORS.purple },
    { name: "Regenerations", value: stats.totals.regenerations, color: COLORS.orange },
  ]

  const modelBarData = stats.model_stats.map(m => ({
    name: m.model.split("/").pop() || m.model,
    satisfaction: Math.round(m.satisfaction * 100),
    thumbsUp: m.thumbs_up,
    thumbsDown: m.thumbs_down,
  })).sort((a, b) => b.satisfaction - a.satisfaction)

  const domainData = stats.domain_stats.map(d => ({
    name: d.domain.charAt(0).toUpperCase() + d.domain.slice(1),
    count: d.count,
    satisfaction: Math.round(d.satisfaction * 100),
  }))

  const timelineData = stats.daily_stats.map(d => ({
    date: new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    satisfaction: Math.round(d.satisfaction_rate * 100),
    total: d.total,
    thumbsUp: d.thumbs_up,
    thumbsDown: d.thumbs_down,
  }))

  return (
    <div className="container mx-auto py-8 px-4 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/settings">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">Feedback Analytics</h1>
            <p className="text-muted-foreground">User satisfaction and engagement trends</p>
          </div>
        </div>
        
        {/* Period Selector + Refresh */}
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-muted-foreground" />
          <select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-border bg-background text-sm"
          >
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
          </select>
          <Button variant="outline" size="icon" onClick={fetchStats} disabled={isLoading}>
            <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 grid-cols-2 md:grid-cols-4 lg:grid-cols-6">
        <StatCard
          title="Quality Score"
          value={`${stats.trends.quality_score}%`}
          icon={Activity}
          trend={stats.trends.satisfaction_trend}
          description="Overall quality rating"
        />
        <StatCard
          title="Thumbs Up"
          value={stats.totals.thumbs_up.toLocaleString()}
          icon={ThumbsUp}
          description="Positive feedback"
          color="green-500"
        />
        <StatCard
          title="Thumbs Down"
          value={stats.totals.thumbs_down.toLocaleString()}
          icon={ThumbsDown}
          description="Negative feedback"
          color="red-500"
        />
        <StatCard
          title="Copies"
          value={stats.totals.copies.toLocaleString()}
          icon={Copy}
          description="Answer copied"
        />
        <StatCard
          title="Shares"
          value={stats.totals.shares.toLocaleString()}
          icon={Share2}
          description="Answers shared"
        />
        <StatCard
          title="Regenerations"
          value={stats.totals.regenerations.toLocaleString()}
          icon={RefreshCw}
          description="Retry requests"
          color="yellow-500"
        />
      </div>

      {/* Main Content - Charts */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column - Satisfaction Gauge */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PieChartIcon className="h-5 w-5" />
              Overall Satisfaction
            </CardTitle>
            <CardDescription>
              Based on thumbs up vs thumbs down ratio
            </CardDescription>
          </CardHeader>
          <CardContent>
            <SatisfactionGauge value={stats.overall_satisfaction} />
            
            <div className="mt-4 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Satisfaction trend</span>
                <Badge variant={stats.trends.satisfaction_trend === "up" ? "default" : "secondary"}>
                  <TrendIcon trend={stats.trends.satisfaction_trend} />
                  <span className="ml-1 capitalize">{stats.trends.satisfaction_trend}</span>
                </Badge>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Engagement trend</span>
                <Badge variant={stats.trends.engagement_trend === "up" ? "default" : "secondary"}>
                  <TrendIcon trend={stats.trends.engagement_trend} />
                  <span className="ml-1 capitalize">{stats.trends.engagement_trend}</span>
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Right Column - Tabs with detailed charts */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Detailed Analytics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="timeline">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="timeline">Timeline</TabsTrigger>
                <TabsTrigger value="models">Models</TabsTrigger>
                <TabsTrigger value="domains">Domains</TabsTrigger>
                <TabsTrigger value="breakdown">Breakdown</TabsTrigger>
              </TabsList>
              
              {/* Timeline Tab - Area Chart */}
              <TabsContent value="timeline" className="mt-4">
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={timelineData}>
                      <defs>
                        <linearGradient id="colorSatisfaction" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={COLORS.bronze} stopOpacity={0.8}/>
                          <stop offset="95%" stopColor={COLORS.bronze} stopOpacity={0.1}/>
                        </linearGradient>
                        <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={COLORS.blue} stopOpacity={0.8}/>
                          <stop offset="95%" stopColor={COLORS.blue} stopOpacity={0.1}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="date" className="text-xs" tick={{ fill: "hsl(var(--muted-foreground))" }} />
                      <YAxis className="text-xs" tick={{ fill: "hsl(var(--muted-foreground))" }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="satisfaction"
                        name="Satisfaction %"
                        stroke={COLORS.bronze}
                        fillOpacity={1}
                        fill="url(#colorSatisfaction)"
                      />
                      <Area
                        type="monotone"
                        dataKey="total"
                        name="Total Feedback"
                        stroke={COLORS.blue}
                        fillOpacity={1}
                        fill="url(#colorTotal)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Daily satisfaction rate and engagement over {stats.period_days} days
                </p>
              </TabsContent>
              
              {/* Models Tab - Bar Chart */}
              <TabsContent value="models" className="mt-4">
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={modelBarData} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis type="number" domain={[0, 100]} tick={{ fill: "hsl(var(--muted-foreground))" }} />
                      <YAxis dataKey="name" type="category" width={100} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar
                        dataKey="satisfaction"
                        name="Satisfaction %"
                        fill={COLORS.bronze}
                        radius={[0, 4, 4, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Satisfaction rate by model (higher is better)
                </p>
              </TabsContent>
              
              {/* Domains Tab - Bar Chart */}
              <TabsContent value="domains" className="mt-4">
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={domainData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="name" tick={{ fill: "hsl(var(--muted-foreground))" }} />
                      <YAxis tick={{ fill: "hsl(var(--muted-foreground))" }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend />
                      <Bar dataKey="count" name="Query Count" fill={COLORS.blue} radius={[4, 4, 0, 0]} />
                      <Bar dataKey="satisfaction" name="Satisfaction %" fill={COLORS.bronze} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Query distribution and satisfaction by domain
                </p>
              </TabsContent>

              {/* Breakdown Tab - Pie Chart */}
              <TabsContent value="breakdown" className="mt-4">
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={feedbackBreakdownData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={5}
                        dataKey="value"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        labelLine={false}
                      >
                        {feedbackBreakdownData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip content={<CustomTooltip />} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Distribution of feedback types
                </p>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>

      {/* Model Performance Table */}
      <Card>
        <CardHeader>
          <CardTitle>Model Performance Comparison</CardTitle>
          <CardDescription>
            Detailed breakdown of user satisfaction by model
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 px-4 font-medium">Model</th>
                  <th className="text-center py-2 px-4 font-medium">Thumbs Up</th>
                  <th className="text-center py-2 px-4 font-medium">Thumbs Down</th>
                  <th className="text-center py-2 px-4 font-medium">Satisfaction</th>
                  <th className="text-center py-2 px-4 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {stats.model_stats.map((model, i) => (
                  <tr key={i} className="border-b last:border-0">
                    <td className="py-3 px-4 font-medium">{model.model}</td>
                    <td className="py-3 px-4 text-center text-green-600">{model.thumbs_up}</td>
                    <td className="py-3 px-4 text-center text-red-600">{model.thumbs_down}</td>
                    <td className="py-3 px-4 text-center">{Math.round(model.satisfaction * 100)}%</td>
                    <td className="py-3 px-4 text-center">
                      <Badge 
                        variant={model.satisfaction >= 0.8 ? "default" : model.satisfaction >= 0.6 ? "secondary" : "destructive"}
                      >
                        {model.satisfaction >= 0.8 ? "Excellent" : model.satisfaction >= 0.6 ? "Good" : "Needs Improvement"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Engagement Timeline - Line Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Engagement Over Time</CardTitle>
          <CardDescription>
            Thumbs up vs thumbs down trends
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timelineData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="date" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} />
                <YAxis tick={{ fill: "hsl(var(--muted-foreground))" }} />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="thumbsUp"
                  name="Thumbs Up"
                  stroke={COLORS.green}
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                />
                <Line
                  type="monotone"
                  dataKey="thumbsDown"
                  name="Thumbs Down"
                  stroke={COLORS.red}
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
