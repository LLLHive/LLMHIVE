import { NextResponse } from "next/server"
import { requireAdmin } from "@/lib/admin/auth"
import type { AdminStats, TierStats } from "@/lib/admin/types"

function generateBusinessStats(): AdminStats {
  const tiers: TierStats[] = [
    { tier: "free", count: 847, mrr: 0, eliteQueriesUsed: 31250, eliteQueriesLimit: 42350 },
    { tier: "lite", count: 234, mrr: 2340, eliteQueriesUsed: 18720, eliteQueriesLimit: 23400 },
    { tier: "pro", count: 156, mrr: 3120, eliteQueriesUsed: 62400, eliteQueriesLimit: 78000 },
    { tier: "enterprise", count: 23, mrr: 4025, eliteQueriesUsed: 115000, eliteQueriesLimit: 184000 },
  ]

  const totalMrr = tiers.reduce((sum, t) => sum + t.mrr, 0)
  const totalUsers = tiers.reduce((sum, t) => sum + t.count, 0)
  const activeSubscribers = totalUsers - tiers[0].count
  const totalEliteUsed = tiers.reduce((sum, t) => sum + t.eliteQueriesUsed, 0)
  const totalEliteLimit = tiers.reduce((sum, t) => sum + t.eliteQueriesLimit, 0)
  const totalApiCost = 892456 * 0.023

  return {
    overview: {
      totalUsers,
      activeSubscribers,
      freeUsers: tiers[0].count,
      mrr: totalMrr,
      arr: totalMrr * 12,
      totalQueriesThisMonth: 892456,
      averageQueriesPerUser: Math.round(892456 / totalUsers),
    },
    tiers,
    revenue: {
      thisMonth: totalMrr,
      lastMonth: totalMrr * 0.92,
      growthPercent: 8.7,
      projectedArr: totalMrr * 12 * 1.15,
    },
    usage: {
      eliteQueriesUsed: totalEliteUsed,
      eliteQueriesTotal: totalEliteLimit,
      standardQueriesUsed: 245000,
      budgetQueriesUsed: 128000,
      averageCostPerQuery: 0.023,
      totalApiCost,
    },
    efficiency: {
      eliteUtilization: (totalEliteUsed / totalEliteLimit) * 100,
      throttleRate: 12.3,
      upgradeConversion: 18.5,
      churnRate: 2.1,
    },
    retention: {
      avgRetentionDays: 127,
      monthlyRetentionRate: 94.2,
      ltv: 342,
      cac: 48,
      ltvCacRatio: 7.1,
      netRevenueRetention: 108.5,
    },
    recentActivity: [
      { type: "subscription", description: "New Pro subscription", timestamp: new Date().toISOString(), tier: "pro" },
      { type: "upgrade", description: "User upgraded from Standard to Premium", timestamp: new Date(Date.now() - 3600000).toISOString(), tier: "pro" },
      { type: "subscription", description: "New Enterprise (8 seats)", timestamp: new Date(Date.now() - 7200000).toISOString(), tier: "enterprise" },
      { type: "cancel", description: "Standard subscription cancelled", timestamp: new Date(Date.now() - 14400000).toISOString(), tier: "lite" },
      { type: "upgrade", description: "User subscribed to Standard", timestamp: new Date(Date.now() - 28800000).toISOString(), tier: "lite" },
      { type: "subscription", description: "Annual Pro plan activated", timestamp: new Date(Date.now() - 43200000).toISOString(), tier: "pro" },
    ],
  }
}

export async function GET() {
  const authResult = await requireAdmin()
  if ("error" in authResult) return authResult.error

  return NextResponse.json(generateBusinessStats())
}
