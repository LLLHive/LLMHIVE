"use client"

import { useCallback, useEffect, useState } from "react"
import { Crown, Sparkles, Star, TrendingUp } from "lucide-react"
import { AdminShell } from "@/components/admin/admin-shell"
import { MetricCard } from "@/components/admin/metric-card"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { getProviderLogoUrl } from "@/lib/provider-logos"
import type { ModelRankingsDashboard } from "@/lib/admin/types"

function ModelAvatar({ author }: { author: string }) {
  const logo = getProviderLogoUrl(author)
  return (
    <div className="h-8 w-8 rounded-lg bg-muted/50 flex items-center justify-center overflow-hidden shrink-0">
      {logo ? (
        <img src={logo} alt={author} className="h-5 w-5 object-contain" />
      ) : (
        <span className="text-xs font-bold text-muted-foreground">{author.slice(0, 2).toUpperCase()}</span>
      )}
    </div>
  )
}

function RankingTable({ entries, showCategory }: { entries: ModelRankingsDashboard["byCategory"][0]["entries"]; showCategory?: boolean }) {
  return (
    <div className="space-y-1">
      {entries.map((entry) => (
        <div
          key={`${entry.category}-${entry.modelId}`}
          className="flex items-center gap-3 rounded-lg px-3 py-2.5 hover:bg-muted/30 transition-colors group"
        >
          <div className="w-8 text-center">
            <span className={`text-sm font-bold ${entry.rank <= 3 ? "text-[var(--bronze)]" : "text-muted-foreground"}`}>
              {entry.rank}
            </span>
          </div>
          <ModelAvatar author={entry.author} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm truncate">{entry.modelName}</span>
              {entry.isNew && (
                <Badge className="bg-[var(--bronze)]/10 text-[var(--bronze)] border-[var(--bronze)]/30 text-[10px] px-1.5">
                  NEW
                </Badge>
              )}
            </div>
            <div className="text-xs text-muted-foreground truncate">
              {entry.author}
              {showCategory && ` · ${entry.categoryLabel}`}
            </div>
          </div>
          {entry.score !== undefined && (
            <div className="text-right shrink-0">
              <div className="text-sm font-mono font-medium">{entry.score.toFixed(1)}</div>
              <div className="text-[10px] text-muted-foreground">score</div>
            </div>
          )}
          <Badge
            variant="outline"
            className={
              entry.isFree
                ? "border-emerald-500/30 text-emerald-500 bg-emerald-500/5 shrink-0"
                : "border-blue-500/30 text-blue-400 bg-blue-500/5 shrink-0"
            }
          >
            {entry.isFree ? "Free" : "Paid"}
          </Badge>
        </div>
      ))}
    </div>
  )
}

export default function AdminModelsPage() {
  const [data, setData] = useState<ModelRankingsDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeCategory, setActiveCategory] = useState("programming")

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch("/api/admin/models")
      if (res.ok) setData(await res.json())
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const activeEntries = data?.byCategory.find((c) => c.slug === activeCategory)?.entries ?? []

  return (
    <AdminShell
      title="Model Intelligence"
      description="Top-10 rankings, new model alerts, free vs paid breakdown"
      onRefresh={fetchData}
      refreshing={loading}
    >
      {loading && !data ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-28 rounded-xl" />
            ))}
          </div>
          <Skeleton className="h-96 rounded-xl" />
        </div>
      ) : data && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="Categories Tracked"
              value={data.summary.totalCategories}
              icon={TrendingUp}
              variant="bronze"
            />
            <MetricCard
              title="New in Top 10"
              value={data.summary.newModelsCount}
              icon={Sparkles}
              subtitle="Across all categories"
              variant="bronze"
            />
            <MetricCard
              title="Free Models"
              value={data.summary.freeInTop10}
              icon={Star}
              subtitle="In top-10 rankings"
              variant="success"
            />
            <MetricCard
              title="Paid Models"
              value={data.summary.paidInTop10}
              icon={Crown}
              subtitle="In top-10 rankings"
            />
          </div>

          <div className="grid lg:grid-cols-3 gap-6">
            {/* New models alert panel */}
            <Card className="lg:col-span-1 bg-gradient-to-br from-[var(--bronze)]/5 to-transparent border-[var(--bronze)]/20">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-[var(--bronze)]" />
                  New Model Alerts
                </CardTitle>
                <CardDescription>
                  Models newly appearing in category top-10 rankings
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[420px] pr-4">
                  {data.newModels.length > 0 ? (
                    <RankingTable entries={data.newModels} showCategory />
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-12">No new models detected</p>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>

            {/* Category rankings */}
            <Card className="lg:col-span-2 bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle>Category Rankings — Top 10</CardTitle>
                <CardDescription>
                  Benchmark scores across {data.summary.totalCategories} use-case categories
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs value={activeCategory} onValueChange={setActiveCategory}>
                  <ScrollArea className="w-full">
                    <TabsList className="inline-flex w-max mb-4 h-auto flex-wrap gap-1">
                      {data.byCategory.map((cat) => (
                        <TabsTrigger key={cat.slug} value={cat.slug} className="text-xs">
                          {cat.label}
                          {cat.newCount > 0 && (
                            <span className="ml-1.5 rounded-full bg-[var(--bronze)]/20 text-[var(--bronze)] px-1.5 text-[10px]">
                              {cat.newCount}
                            </span>
                          )}
                        </TabsTrigger>
                      ))}
                    </TabsList>
                  </ScrollArea>

                  {data.byCategory.map((cat) => (
                    <TabsContent key={cat.slug} value={cat.slug}>
                      <RankingTable entries={cat.entries} />
                    </TabsContent>
                  ))}
                </Tabs>
              </CardContent>
            </Card>
          </div>

          {/* Category overview grid */}
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader>
              <CardTitle>Category Overview</CardTitle>
              <CardDescription>New model count per category</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {data.byCategory.map((cat) => (
                  <button
                    key={cat.slug}
                    onClick={() => setActiveCategory(cat.slug)}
                    className={`text-left rounded-xl border p-4 transition-all hover:shadow-md ${
                      activeCategory === cat.slug
                        ? "border-[var(--bronze)]/40 bg-[var(--bronze)]/5"
                        : "border-border/50 bg-muted/10 hover:bg-muted/20"
                    }`}
                  >
                    <div className="font-medium text-sm">{cat.label}</div>
                    <div className="text-xs text-muted-foreground mt-1">{cat.entries.length} models ranked</div>
                    {cat.newCount > 0 && (
                      <Badge className="mt-2 bg-[var(--bronze)]/10 text-[var(--bronze)] border-[var(--bronze)]/30 text-[10px]">
                        {cat.newCount} new
                      </Badge>
                    )}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </AdminShell>
  )
}
