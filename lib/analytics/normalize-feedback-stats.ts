/**
 * Normalizes backend RLHF stats into the shape expected by the analytics dashboard.
 * The backend may return Pinecone stats, FeedbackStats, or the full dashboard shape.
 */

export interface FeedbackAnalytics {
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

function hasDashboardShape(data: Record<string, unknown>): boolean {
  const totals = data.totals as Record<string, unknown> | undefined
  return (
    !!totals &&
    typeof totals.thumbs_up === "number" &&
    Array.isArray(data.daily_stats) &&
    Array.isArray(data.model_stats)
  )
}

function fromBackendStats(data: Record<string, unknown>, days: number): FeedbackAnalytics | null {
  const byType = (data.by_type ?? data.byType) as Record<string, number> | undefined
  const byModel = (data.by_model ?? data.byModel) as Record<string, number> | undefined

  const thumbsUp =
    byType?.thumbs_up ??
    byType?.THUMBS_UP ??
    (typeof data.positive_count === "number" ? data.positive_count : undefined) ??
    (typeof data.positive === "number" ? data.positive : undefined) ??
    0

  const thumbsDown =
    byType?.thumbs_down ??
    byType?.THUMBS_DOWN ??
    (typeof data.negative_count === "number" ? data.negative_count : undefined) ??
    (typeof data.negative === "number" ? data.negative : undefined) ??
    0

  const copies = byType?.copy ?? byType?.COPY ?? 0
  const shares = byType?.share ?? byType?.SHARE ?? 0
  const regenerations = byType?.regenerate ?? byType?.REGENERATE ?? byType?.regeneration ?? 0

  const totalFeedback =
    typeof data.total_feedback === "number"
      ? data.total_feedback
      : typeof data.total_entries === "number"
        ? data.total_entries
        : typeof data.total === "number"
          ? data.total
          : thumbsUp + thumbsDown + copies + shares + regenerations

  if (totalFeedback === 0 && thumbsUp === 0 && thumbsDown === 0 && !byType && !byModel) {
    return null
  }

  const satisfaction =
    thumbsUp + thumbsDown > 0
      ? thumbsUp / (thumbsUp + thumbsDown)
      : typeof data.average_rating === "number"
        ? Math.min(1, Math.max(0, data.average_rating / 5))
        : typeof data.avg_rating === "number"
          ? Math.min(1, Math.max(0, data.avg_rating / 5))
          : 0.75

  const modelStats = byModel
    ? Object.entries(byModel).map(([model, count]) => ({
        model,
        thumbs_up: Math.round(count * satisfaction),
        thumbs_down: Math.max(0, count - Math.round(count * satisfaction)),
        satisfaction,
      }))
    : []

  return {
    period_days: days,
    totals: {
      thumbs_up: thumbsUp,
      thumbs_down: thumbsDown,
      copies,
      shares,
      regenerations,
      total: totalFeedback,
    },
    overall_satisfaction: satisfaction,
    daily_stats: [],
    model_stats: modelStats,
    domain_stats: [],
    trends: {
      satisfaction_trend: satisfaction >= 0.8 ? "up" : satisfaction >= 0.6 ? "stable" : "down",
      engagement_trend: totalFeedback > 0 ? "up" : "stable",
      quality_score: Math.round(satisfaction * 100),
    },
  }
}

export function normalizeFeedbackAnalytics(
  raw: unknown,
  days: number,
  fallback: () => FeedbackAnalytics
): FeedbackAnalytics {
  if (!raw || typeof raw !== "object") {
    return fallback()
  }

  const data = raw as Record<string, unknown>

  if (hasDashboardShape(data)) {
    return data as unknown as FeedbackAnalytics
  }

  const transformed = fromBackendStats(data, days)
  if (transformed) {
    return transformed
  }

  return fallback()
}

export function generateMockAnalytics(days: number): FeedbackAnalytics {
  const now = new Date()
  const dailyStats = []

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now)
    date.setDate(date.getDate() - i)

    const baseEngagement = 10 + (days - i) * 0.5
    const variance = Math.random() * 5 - 2.5

    const thumbsUp = Math.max(0, Math.round(baseEngagement * 0.7 + variance))
    const thumbsDown = Math.max(0, Math.round(baseEngagement * 0.2 + variance * 0.5))
    const copies = Math.max(0, Math.round(baseEngagement * 0.5 + variance))
    const shares = Math.max(0, Math.round(baseEngagement * 0.1 + variance * 0.2))
    const regenerations = Math.max(0, Math.round(baseEngagement * 0.15 + variance * 0.3))

    dailyStats.push({
      date: date.toISOString().split("T")[0],
      thumbs_up: thumbsUp,
      thumbs_down: thumbsDown,
      copies,
      shares,
      regenerations,
      total: thumbsUp + thumbsDown + copies + shares + regenerations,
      satisfaction_rate: thumbsUp / Math.max(1, thumbsUp + thumbsDown),
    })
  }

  const totals = dailyStats.reduce(
    (acc, day) => ({
      thumbs_up: acc.thumbs_up + day.thumbs_up,
      thumbs_down: acc.thumbs_down + day.thumbs_down,
      copies: acc.copies + day.copies,
      shares: acc.shares + day.shares,
      regenerations: acc.regenerations + day.regenerations,
      total: acc.total + day.total,
    }),
    { thumbs_up: 0, thumbs_down: 0, copies: 0, shares: 0, regenerations: 0, total: 0 }
  )

  const overallSatisfaction = totals.thumbs_up / Math.max(1, totals.thumbs_up + totals.thumbs_down)

  return {
    period_days: days,
    totals,
    overall_satisfaction: overallSatisfaction,
    daily_stats: dailyStats,
    model_stats: [
      { model: "gpt-4o", thumbs_up: 45, thumbs_down: 5, satisfaction: 0.9 },
      { model: "claude-3.5-sonnet", thumbs_up: 42, thumbs_down: 8, satisfaction: 0.84 },
      { model: "gpt-4o-mini", thumbs_up: 38, thumbs_down: 12, satisfaction: 0.76 },
      { model: "gemini-2.0-flash", thumbs_up: 35, thumbs_down: 10, satisfaction: 0.78 },
      { model: "deepseek-chat", thumbs_up: 30, thumbs_down: 15, satisfaction: 0.67 },
    ],
    domain_stats: [
      { domain: "coding", count: 120, satisfaction: 0.85 },
      { domain: "research", count: 95, satisfaction: 0.82 },
      { domain: "general", count: 85, satisfaction: 0.78 },
      { domain: "medical", count: 45, satisfaction: 0.88 },
      { domain: "legal", count: 30, satisfaction: 0.75 },
    ],
    trends: {
      satisfaction_trend: overallSatisfaction > 0.75 ? "up" : overallSatisfaction > 0.6 ? "stable" : "down",
      engagement_trend: "up",
      quality_score: Math.round(overallSatisfaction * 100),
    },
  }
}
