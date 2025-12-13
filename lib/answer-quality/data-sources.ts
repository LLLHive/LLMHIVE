/**
 * Data Sources & Freshness System
 * 
 * Manages data retrieval from multiple sources with freshness awareness:
 * - Web search for real-time information
 * - Knowledge bases for domain expertise
 * - Document retrieval for context
 * - Data freshness validation
 */

import type { QueryAnalysis, Citation } from './types'

export interface DataSource {
  id: string
  name: string
  type: DataSourceType
  priority: number
  freshness: DataFreshness
  reliability: number
  config: DataSourceConfig
}

export type DataSourceType = 
  | 'web-search'
  | 'knowledge-base'
  | 'document-store'
  | 'api'
  | 'database'
  | 'cache'

export type DataFreshness = 
  | 'realtime'      // Seconds old
  | 'hourly'        // Hours old
  | 'daily'         // Days old
  | 'weekly'        // Weeks old
  | 'monthly'       // Months old
  | 'static'        // Rarely changes

export interface DataSourceConfig {
  endpoint?: string
  apiKey?: string
  maxResults?: number
  timeout?: number
  cachePolicy?: 'no-cache' | 'cache-first' | 'stale-while-revalidate'
}

export interface RetrievedData {
  source: string
  content: string
  url?: string
  title?: string
  timestamp: Date
  freshness: DataFreshness
  relevance: number
  reliability: number
  citations: Citation[]
}

export interface DataRetrievalPlan {
  sources: DataSource[]
  strategy: RetrievalStrategy
  freshnessRequirement: DataFreshness
  maxSources: number
  timeout: number
}

export type RetrievalStrategy = 
  | 'first-match'     // Use first relevant result
  | 'best-match'      // Score and use best
  | 'aggregate'       // Combine from multiple
  | 'verify'          // Cross-reference multiple

// Pre-configured data sources
export const DATA_SOURCES: Record<string, DataSource> = {
  'web-search-primary': {
    id: 'web-search-primary',
    name: 'Web Search',
    type: 'web-search',
    priority: 1,
    freshness: 'realtime',
    reliability: 0.85,
    config: {
      maxResults: 10,
      timeout: 5000,
    },
  },
  
  'web-search-news': {
    id: 'web-search-news',
    name: 'News Search',
    type: 'web-search',
    priority: 2,
    freshness: 'realtime',
    reliability: 0.9,
    config: {
      maxResults: 5,
      timeout: 5000,
    },
  },
  
  'knowledge-base-general': {
    id: 'knowledge-base-general',
    name: 'General Knowledge Base',
    type: 'knowledge-base',
    priority: 3,
    freshness: 'monthly',
    reliability: 0.95,
    config: {
      maxResults: 20,
      timeout: 3000,
      cachePolicy: 'stale-while-revalidate',
    },
  },
  
  'knowledge-base-technical': {
    id: 'knowledge-base-technical',
    name: 'Technical Documentation',
    type: 'knowledge-base',
    priority: 2,
    freshness: 'weekly',
    reliability: 0.95,
    config: {
      maxResults: 15,
      timeout: 3000,
    },
  },
  
  'document-store': {
    id: 'document-store',
    name: 'Document Store',
    type: 'document-store',
    priority: 4,
    freshness: 'static',
    reliability: 0.9,
    config: {
      maxResults: 10,
      timeout: 2000,
    },
  },
  
  'cache': {
    id: 'cache',
    name: 'Response Cache',
    type: 'cache',
    priority: 0, // Highest priority
    freshness: 'hourly',
    reliability: 0.99,
    config: {
      timeout: 100,
      cachePolicy: 'cache-first',
    },
  },
}

// Freshness requirements by query type
const FRESHNESS_REQUIREMENTS: Record<string, DataFreshness> = {
  'news': 'realtime',
  'current-events': 'realtime',
  'stock-prices': 'realtime',
  'weather': 'hourly',
  'sports-scores': 'realtime',
  'technology-trends': 'daily',
  'research': 'weekly',
  'historical': 'static',
  'definitions': 'static',
  'how-to': 'weekly',
  'best-practices': 'weekly',
}

/**
 * Determine data freshness requirement from query
 */
export function determineFreshnessRequirement(analysis: QueryAnalysis): DataFreshness {
  // Check temporal context
  if (analysis.temporalContext) {
    if (analysis.temporalContext.dataFreshness === 'current') {
      return 'realtime'
    }
    if (analysis.temporalContext.dataFreshness === 'recent') {
      return 'daily'
    }
    if (analysis.temporalContext.dataFreshness === 'historical') {
      return 'static'
    }
  }
  
  // Check for freshness indicators in domain
  const domainFreshness: Record<string, DataFreshness> = {
    'technology': 'weekly',
    'finance': 'realtime',
    'science': 'monthly',
    'medical': 'weekly',
    'legal': 'monthly',
    'business': 'daily',
  }
  
  return domainFreshness[analysis.domain] || 'weekly'
}

/**
 * Select optimal data sources for a query
 */
export function selectDataSources(
  analysis: QueryAnalysis,
  freshnessRequirement: DataFreshness
): DataSource[] {
  const sources: DataSource[] = []
  
  // Always check cache first
  sources.push(DATA_SOURCES['cache'])
  
  // Add web search for realtime/daily freshness
  if (['realtime', 'hourly', 'daily'].includes(freshnessRequirement)) {
    sources.push(DATA_SOURCES['web-search-primary'])
    
    // Add news search for current events
    if (analysis.intent === 'factual' || analysis.domain === 'news') {
      sources.push(DATA_SOURCES['web-search-news'])
    }
  }
  
  // Add knowledge bases for technical queries
  if (analysis.domain === 'technology' || analysis.intent === 'code') {
    sources.push(DATA_SOURCES['knowledge-base-technical'])
  }
  
  // Add general knowledge base
  sources.push(DATA_SOURCES['knowledge-base-general'])
  
  // Sort by priority
  return sources.sort((a, b) => a.priority - b.priority)
}

/**
 * Create a data retrieval plan
 */
export function createRetrievalPlan(analysis: QueryAnalysis): DataRetrievalPlan {
  const freshnessRequirement = determineFreshnessRequirement(analysis)
  const sources = selectDataSources(analysis, freshnessRequirement)
  
  // Determine strategy based on query type
  let strategy: RetrievalStrategy = 'best-match'
  
  if (analysis.intent === 'factual') {
    strategy = 'verify' // Cross-reference for facts
  } else if (analysis.intent === 'research') {
    strategy = 'aggregate' // Combine from multiple sources
  } else if (analysis.complexity === 'simple') {
    strategy = 'first-match' // Quick answer
  }
  
  return {
    sources,
    strategy,
    freshnessRequirement,
    maxSources: analysis.complexity === 'expert' ? 5 : 3,
    timeout: freshnessRequirement === 'realtime' ? 10000 : 5000,
  }
}

/**
 * Format web search results for inclusion in prompt
 */
export function formatSearchResults(results: RetrievedData[]): string {
  if (results.length === 0) {
    return ''
  }
  
  const parts: string[] = ['**Relevant Information from Sources:**\n']
  
  results.forEach((result, idx) => {
    parts.push(`[${idx + 1}] **${result.title || result.source}**`)
    if (result.url) {
      parts.push(`   Source: ${result.url}`)
    }
    parts.push(`   ${result.content.slice(0, 300)}${result.content.length > 300 ? '...' : ''}`)
    parts.push(`   (Updated: ${formatFreshness(result.timestamp, result.freshness)})\n`)
  })
  
  return parts.join('\n')
}

/**
 * Format freshness for display
 */
function formatFreshness(timestamp: Date, freshness: DataFreshness): string {
  const now = new Date()
  const diff = now.getTime() - timestamp.getTime()
  
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  
  if (minutes < 5) return 'Just now'
  if (minutes < 60) return `${minutes} minutes ago`
  if (hours < 24) return `${hours} hours ago`
  if (days < 7) return `${days} days ago`
  if (days < 30) return `${Math.floor(days / 7)} weeks ago`
  return `${Math.floor(days / 30)} months ago`
}

/**
 * Validate data freshness
 */
export function validateFreshness(
  data: RetrievedData,
  requirement: DataFreshness
): boolean {
  const freshnessOrder: DataFreshness[] = [
    'realtime', 'hourly', 'daily', 'weekly', 'monthly', 'static'
  ]
  
  const requirementIdx = freshnessOrder.indexOf(requirement)
  const dataIdx = freshnessOrder.indexOf(data.freshness)
  
  // Data is fresh enough if its freshness level is same or better
  return dataIdx <= requirementIdx
}

/**
 * Calculate overall data quality score
 */
export function calculateDataQuality(data: RetrievedData[]): number {
  if (data.length === 0) return 0
  
  let totalScore = 0
  
  for (const item of data) {
    let score = 0
    
    // Relevance (0-40 points)
    score += item.relevance * 40
    
    // Reliability (0-30 points)
    score += item.reliability * 30
    
    // Freshness (0-20 points)
    const freshnessScores: Record<DataFreshness, number> = {
      'realtime': 20,
      'hourly': 18,
      'daily': 15,
      'weekly': 12,
      'monthly': 8,
      'static': 5,
    }
    score += freshnessScores[item.freshness]
    
    // Has citations (0-10 points)
    score += Math.min(10, item.citations.length * 2)
    
    totalScore += score
  }
  
  return Math.round(totalScore / data.length)
}

/**
 * Generate context augmentation for prompt
 */
export function generateContextAugmentation(
  query: string,
  data: RetrievedData[],
  analysis: QueryAnalysis
): string {
  const parts: string[] = []
  
  // Add freshness notice if using real-time data
  const hasRealtimeData = data.some(d => d.freshness === 'realtime')
  if (hasRealtimeData) {
    parts.push('**Note:** Using real-time information retrieved just now.\n')
  }
  
  // Add search results
  const formattedResults = formatSearchResults(data)
  if (formattedResults) {
    parts.push(formattedResults)
  }
  
  // Add instructions for using the data
  parts.push('\n**Instructions:**')
  parts.push('- Use the above information to inform your response')
  parts.push('- Cite sources using [1], [2], etc. when referencing specific information')
  parts.push('- If the retrieved information conflicts, note the discrepancy')
  parts.push('- If retrieved information is insufficient, indicate what else would be helpful')
  
  return parts.join('\n')
}

/**
 * Simulate web search (placeholder for actual implementation)
 * In production, this would call actual search APIs
 */
export async function performWebSearch(
  query: string,
  options: { maxResults?: number; freshness?: DataFreshness }
): Promise<RetrievedData[]> {
  // Placeholder - in production, integrate with:
  // - Bing Search API
  // - Google Custom Search
  // - Tavily
  // - Serper
  // - Brave Search
  
  return [{
    source: 'web-search',
    content: `[Simulated search result for: "${query}"]`,
    timestamp: new Date(),
    freshness: 'realtime',
    relevance: 0.8,
    reliability: 0.75,
    citations: [],
  }]
}

/**
 * Query knowledge base (placeholder for actual implementation)
 */
export async function queryKnowledgeBase(
  query: string,
  knowledgeBaseId: string
): Promise<RetrievedData[]> {
  // Placeholder - in production, integrate with:
  // - Pinecone
  // - Weaviate
  // - Milvus
  // - Qdrant
  
  return []
}

/**
 * Retrieve from document store (placeholder)
 */
export async function retrieveDocuments(
  query: string,
  filters?: Record<string, string>
): Promise<RetrievedData[]> {
  // Placeholder for document retrieval
  return []
}

/**
 * Check cache for previous answers
 */
export async function checkCache(
  query: string,
  maxAge?: number
): Promise<RetrievedData | null> {
  // Placeholder for cache lookup
  // In production, use Redis or similar
  return null
}

/**
 * Execute full data retrieval based on plan
 */
export async function executeRetrievalPlan(
  query: string,
  plan: DataRetrievalPlan
): Promise<RetrievedData[]> {
  const results: RetrievedData[] = []
  
  // Check cache first
  const cached = await checkCache(query)
  if (cached && validateFreshness(cached, plan.freshnessRequirement)) {
    return [cached]
  }
  
  // Execute in parallel with timeout
  const promises = plan.sources
    .filter(s => s.type !== 'cache')
    .slice(0, plan.maxSources)
    .map(async source => {
      try {
        switch (source.type) {
          case 'web-search':
            return await performWebSearch(query, { 
              maxResults: source.config.maxResults,
              freshness: plan.freshnessRequirement,
            })
          case 'knowledge-base':
            return await queryKnowledgeBase(query, source.id)
          case 'document-store':
            return await retrieveDocuments(query)
          default:
            return []
        }
      } catch (error) {
        console.error(`Error retrieving from ${source.name}:`, error)
        return []
      }
    })
  
  // Race against timeout
  const timeoutPromise = new Promise<RetrievedData[][]>(resolve => 
    setTimeout(() => resolve([]), plan.timeout)
  )
  
  const allResults = await Promise.race([
    Promise.all(promises),
    timeoutPromise,
  ])
  
  // Flatten and deduplicate
  for (const sourceResults of allResults) {
    results.push(...sourceResults)
  }
  
  // Sort by relevance
  results.sort((a, b) => b.relevance - a.relevance)
  
  return results.slice(0, plan.maxSources * 3) // Return top results
}

