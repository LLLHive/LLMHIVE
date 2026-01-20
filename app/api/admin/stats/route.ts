import { NextRequest, NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";

// Admin user IDs - in production, use a proper role system
const ADMIN_USERS = process.env.ADMIN_USER_IDS?.split(",") || [];

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

// Mock data generator - replace with actual database queries
function generateMockStats(): AdminStats {
  const tiers: TierStats[] = [
    { tier: "free", count: 847, mrr: 0, eliteQueriesUsed: 31250, eliteQueriesLimit: 42350 },
    { tier: "lite", count: 234, mrr: 234 * 9, eliteQueriesUsed: 18720, eliteQueriesLimit: 23400 },
    { tier: "pro", count: 156, mrr: 156 * 29, eliteQueriesUsed: 62400, eliteQueriesLimit: 78000 },
    { tier: "enterprise", count: 23, mrr: 23 * 5 * 25, eliteQueriesUsed: 115000, eliteQueriesLimit: 184000 },
    { tier: "maximum", count: 8, mrr: 8 * 99, eliteQueriesUsed: 80000, eliteQueriesLimit: 80000 },
  ];

  const totalMrr = tiers.reduce((sum, t) => sum + t.mrr, 0);
  const totalUsers = tiers.reduce((sum, t) => sum + t.count, 0);
  const activeSubscribers = totalUsers - tiers[0].count;
  const totalEliteUsed = tiers.reduce((sum, t) => sum + t.eliteQueriesUsed, 0);
  const totalEliteLimit = tiers.reduce((sum, t) => sum + t.eliteQueriesLimit, 0);

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
      totalApiCost: 892456 * 0.023,
    },
    efficiency: {
      eliteUtilization: (totalEliteUsed / totalEliteLimit) * 100,
      throttleRate: 12.3,
      upgradeConversion: 18.5,
      churnRate: 2.1,
    },
    recentActivity: [
      { type: "subscription", description: "New Pro subscription", timestamp: new Date().toISOString(), tier: "pro" },
      { type: "upgrade", description: "User upgraded from Lite to Pro", timestamp: new Date(Date.now() - 3600000).toISOString(), tier: "pro" },
      { type: "subscription", description: "New Enterprise (8 seats)", timestamp: new Date(Date.now() - 7200000).toISOString(), tier: "enterprise" },
      { type: "cancel", description: "Lite subscription cancelled", timestamp: new Date(Date.now() - 14400000).toISOString(), tier: "lite" },
      { type: "upgrade", description: "User upgraded from Pro to Maximum", timestamp: new Date(Date.now() - 28800000).toISOString(), tier: "maximum" },
    ],
  };
}

export async function GET(request: NextRequest) {
  try {
    const { userId } = await auth();

    // Check if user is admin
    if (!userId || (!ADMIN_USERS.includes(userId) && ADMIN_USERS.length > 0)) {
      return NextResponse.json(
        { error: "Unauthorized - Admin access required" },
        { status: 403 }
      );
    }

    // In production, fetch real data from:
    // - Firestore for user/subscription counts
    // - Stripe for revenue data
    // - Your usage tracking system for query counts
    const stats = generateMockStats();

    // TODO: Replace with real database queries
    // Example:
    // const firestore = getFirestore();
    // const usersSnapshot = await firestore.collection('users').get();
    // const subscriptionsSnapshot = await firestore.collection('subscriptions').where('status', '==', 'active').get();
    // const stripeBalance = await stripe.balance.retrieve();

    return NextResponse.json(stats);
  } catch (error) {
    console.error("Error fetching admin stats:", error);
    return NextResponse.json(
      { error: "Failed to fetch admin stats" },
      { status: 500 }
    );
  }
}
