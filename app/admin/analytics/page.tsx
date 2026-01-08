"use client"

import { useState, useEffect } from "react"
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
  PieChart,
  Activity,
  Calendar,
  ArrowLeft,
} from "lucide-react"
import Link from "next/link"
import { cn } from "@/lib/utils"

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

function SimpleBarChart({ data, maxValue }: { data: { label: string; value: number; color?: string }[]; maxValue: number }) {
  return (
    <div className="space-y-3">
      {data.map((item, i) => (
        <div key={i} className="space-y-1">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">{item.label}</span>
            <span className="text-muted-foreground">{item.value}</span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div 
              className={cn(
                "h-full rounded-full transition-all",
                item.color || "bg-[var(--bronze)]"
              )}
              style={{ width: `${(item.value / maxValue) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

function SatisfactionGauge({ value }: { value: number }) {
  const percentage = Math.round(value * 100)
  const color = percentage >= 80 ? "text-green-500" : percentage >= 60 ? "text-yellow-500" : "text-red-500"
  const bgColor = percentage >= 80 ? "bg-green-500" : percentage >= 60 ? "bg-yellow-500" : "bg-red-500"
  
  return (
    <div className="flex flex-col items-center justify-center p-6">
      <div className="relative w-32 h-32">
        {/* Background circle */}
        <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="currentColor"
            strokeWidth="10"
            className="text-muted"
          />
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="currentColor"
            strokeWidth="10"
            strokeDasharray={`${percentage * 2.83} 283`}
            className={color}
          />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cn("text-3xl font-bold", color)}>{percentage}%</span>
          <span className="text-xs text-muted-foreground">Satisfaction</span>
        </div>
      </div>
    </div>
  )
}

function MiniChart({ data, height = 40 }: { data: number[]; height?: number }) {
  if (!data.length) return null
  
  const max = Math.max(...data)
  const min = Math.min(...data)
  const range = max - min || 1
  
  const points = data.map((value, i) => {
    const x = (i / (data.length - 1)) * 100
    const y = height - ((value - min) / range) * height
    return `${x},${y}`
  }).join(" ")
  
  return (
    <svg className="w-full" height={height} viewBox={`0 0 100 ${height}`} preserveAspectRatio="none">
      <polyline
        points={points}
        fill="none"
        stroke="var(--bronze)"
        strokeWidth="2"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  )
}

export default function FeedbackAnalyticsPage() {
  const [stats, setStats] = useState<FeedbackStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [selectedPeriod, setSelectedPeriod] = useState("30")

  useEffect(() => {
    async function fetchStats() {
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
    }
    
    fetchStats()
  }, [selectedPeriod])

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
        
        {/* Period Selector */}
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
          value={stats.totals.thumbs_up}
          icon={ThumbsUp}
          description="Positive feedback"
          color="green-500"
        />
        <StatCard
          title="Thumbs Down"
          value={stats.totals.thumbs_down}
          icon={ThumbsDown}
          description="Negative feedback"
          color="red-500"
        />
        <StatCard
          title="Copies"
          value={stats.totals.copies}
          icon={Copy}
          description="Answer copied"
        />
        <StatCard
          title="Shares"
          value={stats.totals.shares}
          icon={Share2}
          description="Answers shared"
        />
        <StatCard
          title="Regenerations"
          value={stats.totals.regenerations}
          icon={RefreshCw}
          description="Retry requests"
          color="yellow-500"
        />
      </div>

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column - Satisfaction Gauge + Trends */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PieChart className="h-5 w-5" />
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

        {/* Right Column - Tabs with detailed views */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Detailed Analytics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="models">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="models">By Model</TabsTrigger>
                <TabsTrigger value="domains">By Domain</TabsTrigger>
                <TabsTrigger value="timeline">Timeline</TabsTrigger>
              </TabsList>
              
              <TabsContent value="models" className="mt-4">
                <SimpleBarChart
                  data={stats.model_stats.map(m => ({
                    label: m.model,
                    value: Math.round(m.satisfaction * 100),
                    color: m.satisfaction >= 0.8 ? "bg-green-500" : m.satisfaction >= 0.6 ? "bg-yellow-500" : "bg-red-500"
                  }))}
                  maxValue={100}
                />
                <p className="text-xs text-muted-foreground mt-4">
                  Satisfaction rate by model (higher is better)
                </p>
              </TabsContent>
              
              <TabsContent value="domains" className="mt-4">
                <SimpleBarChart
                  data={stats.domain_stats.map(d => ({
                    label: d.domain.charAt(0).toUpperCase() + d.domain.slice(1),
                    value: d.count,
                  }))}
                  maxValue={Math.max(...stats.domain_stats.map(d => d.count))}
                />
                <p className="text-xs text-muted-foreground mt-4">
                  Query distribution by domain
                </p>
              </TabsContent>
              
              <TabsContent value="timeline" className="mt-4 space-y-4">
                <div>
                  <p className="text-sm font-medium mb-2">Daily Satisfaction Rate</p>
                  <MiniChart 
                    data={stats.daily_stats.map(d => d.satisfaction_rate * 100)} 
                    height={60}
                  />
                </div>
                <div>
                  <p className="text-sm font-medium mb-2">Daily Engagement</p>
                  <MiniChart 
                    data={stats.daily_stats.map(d => d.total)} 
                    height={60}
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Trends over the selected {stats.period_days} day period
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
    </div>
  )
}

