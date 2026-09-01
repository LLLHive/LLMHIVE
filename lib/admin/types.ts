export type ProviderStatus = "healthy" | "degraded" | "down" | "unconfigured" | "throttled"
export type ConnectionType = "direct" | "aggregator"

export interface ProviderMetric {
  id: string
  name: string
  connectionType: ConnectionType
  status: ProviderStatus
  configured: boolean
  uptimePercent: number
  requests24h: number
  successRate: number
  avgLatencyMs: number
  p95LatencyMs: number
  errorRate: number
  throttleEvents24h: number
  downtimeMinutes24h: number
  costUsd24h: number
  tokens24h: number
  rpmLimit?: number
  rpmUsed?: number
  lastChecked: string
  lastIncident?: string
  models: string[]
}

export interface ProviderDashboard {
  summary: {
    totalProviders: number
    healthy: number
    degraded: number
    down: number
    unconfigured: number
    totalRequests24h: number
    totalCost24h: number
    avgLatencyMs: number
    overallUptime: number
  }
  providers: ProviderMetric[]
  latencyTrend: Array<{ time: string; latency: number; provider: string }>
  incidentLog: Array<{
    id: string
    provider: string
    type: "down" | "throttle" | "degraded"
    message: string
    startedAt: string
    resolvedAt?: string
    durationMinutes?: number
  }>
  lastUpdated: string
}

export interface TierStats {
  tier: string
  count: number
  mrr: number
  eliteQueriesUsed: number
  eliteQueriesLimit: number
}

export interface AdminStats {
  overview: {
    totalUsers: number
    activeSubscribers: number
    freeUsers: number
    mrr: number
    arr: number
    totalQueriesThisMonth: number
    averageQueriesPerUser: number
  }
  tiers: TierStats[]
  revenue: {
    thisMonth: number
    lastMonth: number
    growthPercent: number
    projectedArr: number
  }
  usage: {
    eliteQueriesUsed: number
    eliteQueriesTotal: number
    standardQueriesUsed: number
    budgetQueriesUsed: number
    averageCostPerQuery: number
    totalApiCost: number
  }
  efficiency: {
    eliteUtilization: number
    throttleRate: number
    upgradeConversion: number
    churnRate: number
  }
  retention: {
    avgRetentionDays: number
    monthlyRetentionRate: number
    ltv: number
    cac: number
    ltvCacRatio: number
    netRevenueRetention: number
  }
  recentActivity: Array<{
    type: string
    description: string
    timestamp: string
    tier?: string
  }>
}

export interface RankedModelEntry {
  rank: number
  modelId: string
  modelName: string
  author: string
  category: string
  categoryLabel: string
  score?: number
  isFree: boolean
  isNew: boolean
  pricing?: { prompt: number; completion: number }
}

export interface ModelRankingsDashboard {
  summary: {
    totalCategories: number
    totalRankedModels: number
    newModelsCount: number
    freeInTop10: number
    paidInTop10: number
    lastSynced: string
  }
  newModels: RankedModelEntry[]
  byCategory: Array<{
    slug: string
    label: string
    entries: RankedModelEntry[]
    newCount: number
  }>
  freeVsPaid: { free: number; paid: number }
}
