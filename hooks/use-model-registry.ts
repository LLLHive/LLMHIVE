/**
 * Hook for loading the authoritative model registry from models.json.
 *
 * models.json is exported from the Python model_registry.py via
 * scripts/export_model_registry.py.  The UI reads it at runtime so
 * backend and frontend stay in sync without manual duplication.
 */

import * as React from "react"

export interface RegistryModel {
  id: string
  tier: "elite" | "free" | "both"
  tierDisplay: string
  capabilities: string[]
  latencyTier: "fast" | "medium" | "slow" | "very_slow"
  reliability: number
  contextWindow: number
  categoryScores: Record<string, number>
  recommended: boolean
  bestForCategories: string[]
  leaderboardRank: Record<string, number>
  notes: string | null
}

export interface CategoryLeader {
  category_key: string
  display_name: string
  leader_score: string
  leader_model: string
}

export interface ModelRegistry {
  registryVersion: string
  generatedBy: string
  models: RegistryModel[]
  categoryLeaders?: CategoryLeader[]
  categoryLeadersVersion?: string
}

export interface UseModelRegistryResult {
  registry: ModelRegistry | null
  models: RegistryModel[]
  loading: boolean
  error: string | null
  version: string | null
  manifestVersion: string | null
  registryMismatch: boolean
  getModel: (id: string) => RegistryModel | undefined
  getRecommended: () => RegistryModel[]
  getByTier: (tier: "elite" | "free" | "both") => RegistryModel[]
  getByCapability: (cap: string) => RegistryModel[]
  getBestFor: (category: string) => RegistryModel[]
}

let _cache: ModelRegistry | null = null
let _manifestVersion: string | null = null

async function _fetchManifestVersion(): Promise<string | null> {
  try {
    const res = await fetch(`/release_manifest.json?v=${Date.now()}`)
    if (!res.ok) return null
    const data = await res.json()
    return data.model_registry_version ?? null
  } catch {
    return null
  }
}

export function useModelRegistry(): UseModelRegistryResult {
  const [registry, setRegistry] = React.useState<ModelRegistry | null>(_cache)
  const [loading, setLoading] = React.useState(!_cache)
  const [error, setError] = React.useState<string | null>(null)
  const [registryMismatch, setRegistryMismatch] = React.useState(false)

  React.useEffect(() => {
    if (_cache) {
      setRegistry(_cache)
      setLoading(false)
      return
    }

    let cancelled = false

    async function load() {
      try {
        const manifestVer = await _fetchManifestVersion()
        _manifestVersion = manifestVer

        const cacheBust = manifestVer ? `v=${manifestVer}` : `v=${Date.now()}`
        const res = await fetch(`/models.json?${cacheBust}`)
        if (!res.ok) throw new Error(`Failed to load models.json: ${res.status}`)
        const data: ModelRegistry = await res.json()
        if (!cancelled) {
          _cache = data
          setRegistry(data)

          if (manifestVer && data.registryVersion && manifestVer !== data.registryVersion) {
            setRegistryMismatch(true)
          }
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Unknown error")
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [])

  const models = registry?.models ?? []

  const getModel = React.useCallback(
    (id: string) => models.find((m) => m.id === id),
    [models],
  )

  const getRecommended = React.useCallback(
    () => models.filter((m) => m.recommended),
    [models],
  )

  const getByTier = React.useCallback(
    (tier: "elite" | "free" | "both") =>
      models.filter((m) => m.tier === tier || m.tier === "both"),
    [models],
  )

  const getByCapability = React.useCallback(
    (cap: string) => models.filter((m) => m.capabilities.includes(cap)),
    [models],
  )

  const getBestFor = React.useCallback(
    (category: string) =>
      models.filter((m) => m.bestForCategories?.includes(category)),
    [models],
  )

  const categoryLeaders = registry?.categoryLeaders ?? []
  const categoryLeadersVersion = registry?.categoryLeadersVersion ?? null

  const getCategoryLeader = React.useCallback(
    (categoryKey: string) =>
      categoryLeaders.find((c) => c.category_key === categoryKey),
    [categoryLeaders],
  )

  return {
    registry,
    models,
    loading,
    error,
    version: registry?.registryVersion ?? null,
    manifestVersion: _manifestVersion,
    registryMismatch,
    categoryLeaders,
    categoryLeadersVersion,
    getModel,
    getRecommended,
    getByTier,
    getByCapability,
    getBestFor,
    getCategoryLeader,
  }
}
