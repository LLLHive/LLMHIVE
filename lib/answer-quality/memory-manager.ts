/**
 * Memory & Context Management System
 * 
 * Manages conversation context and long-term memory to provide
 * personalized, contextually-aware responses.
 */

export interface MemoryEntry {
  id: string
  type: MemoryType
  content: string
  importance: number
  created: Date
  lastAccessed: Date
  accessCount: number
  tags: string[]
  sourceConversation?: string
  embedding?: number[]
}

export type MemoryType = 
  | 'fact'           // Factual information learned
  | 'preference'     // User preferences
  | 'context'        // Conversation context
  | 'pattern'        // Learned patterns
  | 'correction'     // Corrections made

export interface ConversationContext {
  id: string
  topic: string
  entities: string[]
  keyPoints: string[]
  userPreferences: Record<string, string>
  previousQuestions: string[]
  previousResponses: string[]
  emotionalTone: string
  expertise: 'beginner' | 'intermediate' | 'expert'
}

export interface ContextWindow {
  shortTerm: MemoryEntry[]   // Current conversation
  mediumTerm: MemoryEntry[]  // Recent sessions
  longTerm: MemoryEntry[]    // Persistent memory
  maxTokens: number
  currentTokens: number
}

export interface RetrievedContext {
  memories: MemoryEntry[]
  conversationHistory: string[]
  userProfile: UserProfile
  relevanceScores: number[]
}

export interface UserProfile {
  id: string
  preferences: Record<string, string>
  expertise: Record<string, 'beginner' | 'intermediate' | 'expert'>
  communicationStyle: 'formal' | 'casual' | 'technical'
  interests: string[]
  frequentTopics: string[]
}

// Storage keys
const MEMORY_KEY = 'llmhive-memory'
const CONTEXT_KEY = 'llmhive-context'
const PROFILE_KEY = 'llmhive-profile'

/**
 * Memory Manager for context and long-term memory
 */
export class MemoryManager {
  private memories: MemoryEntry[] = []
  private currentContext: ConversationContext | null = null
  private userProfile: UserProfile
  private maxMemories: number = 1000
  private maxShortTermTokens: number = 4000
  
  constructor() {
    this.userProfile = this.loadProfile()
    this.loadMemories()
    this.loadContext()
  }
  
  private loadMemories(): void {
    if (typeof window === 'undefined') return
    
    try {
      const stored = localStorage.getItem(MEMORY_KEY)
      if (stored) {
        this.memories = JSON.parse(stored).map((m: MemoryEntry) => ({
          ...m,
          created: new Date(m.created),
          lastAccessed: new Date(m.lastAccessed),
        }))
      }
    } catch (error) {
      console.error('Error loading memories:', error)
      this.memories = []
    }
  }
  
  private saveMemories(): void {
    if (typeof window === 'undefined') return
    
    try {
      // Keep only most important memories
      const toSave = this.memories
        .sort((a, b) => this.calculateImportance(b) - this.calculateImportance(a))
        .slice(0, this.maxMemories)
      
      localStorage.setItem(MEMORY_KEY, JSON.stringify(toSave))
    } catch (error) {
      console.error('Error saving memories:', error)
    }
  }
  
  private loadContext(): void {
    if (typeof window === 'undefined') return
    
    try {
      const stored = localStorage.getItem(CONTEXT_KEY)
      if (stored) {
        this.currentContext = JSON.parse(stored)
      }
    } catch (error) {
      console.error('Error loading context:', error)
    }
  }
  
  private saveContext(): void {
    if (typeof window === 'undefined') return
    
    try {
      if (this.currentContext) {
        localStorage.setItem(CONTEXT_KEY, JSON.stringify(this.currentContext))
      }
    } catch (error) {
      console.error('Error saving context:', error)
    }
  }
  
  private loadProfile(): UserProfile {
    if (typeof window === 'undefined') {
      return this.createDefaultProfile()
    }
    
    try {
      const stored = localStorage.getItem(PROFILE_KEY)
      if (stored) {
        return JSON.parse(stored)
      }
    } catch (error) {
      console.error('Error loading profile:', error)
    }
    
    return this.createDefaultProfile()
  }
  
  private createDefaultProfile(): UserProfile {
    return {
      id: `user-${Date.now()}`,
      preferences: {},
      expertise: {},
      communicationStyle: 'casual',
      interests: [],
      frequentTopics: [],
    }
  }
  
  private saveProfile(): void {
    if (typeof window === 'undefined') return
    
    try {
      localStorage.setItem(PROFILE_KEY, JSON.stringify(this.userProfile))
    } catch (error) {
      console.error('Error saving profile:', error)
    }
  }
  
  /**
   * Calculate importance score for a memory
   */
  private calculateImportance(memory: MemoryEntry): number {
    const now = new Date()
    const age = (now.getTime() - memory.lastAccessed.getTime()) / (1000 * 60 * 60 * 24)
    
    // Decay factor based on age
    const decayFactor = Math.exp(-age / 30) // 30-day half-life
    
    // Access frequency boost
    const accessBoost = Math.log(memory.accessCount + 1)
    
    // Type importance
    const typeWeights: Record<MemoryType, number> = {
      'preference': 1.5,
      'fact': 1.2,
      'correction': 1.3,
      'pattern': 1.1,
      'context': 0.8,
    }
    
    return memory.importance * decayFactor * accessBoost * (typeWeights[memory.type] || 1)
  }
  
  /**
   * Add a new memory
   */
  addMemory(
    content: string,
    type: MemoryType,
    options: {
      importance?: number
      tags?: string[]
      sourceConversation?: string
    } = {}
  ): MemoryEntry {
    const memory: MemoryEntry = {
      id: `mem-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      type,
      content,
      importance: options.importance || 0.5,
      created: new Date(),
      lastAccessed: new Date(),
      accessCount: 1,
      tags: options.tags || [],
      sourceConversation: options.sourceConversation,
    }
    
    // Check for duplicates
    const existing = this.memories.find(m => 
      m.content.toLowerCase() === content.toLowerCase() && m.type === type
    )
    
    if (existing) {
      // Update existing memory
      existing.lastAccessed = new Date()
      existing.accessCount++
      existing.importance = Math.min(1, existing.importance + 0.1)
      this.saveMemories()
      return existing
    }
    
    this.memories.push(memory)
    this.saveMemories()
    
    return memory
  }
  
  /**
   * Retrieve relevant memories for a query
   */
  retrieveMemories(
    query: string,
    options: {
      types?: MemoryType[]
      limit?: number
      minImportance?: number
    } = {}
  ): MemoryEntry[] {
    const { types, limit = 10, minImportance = 0.3 } = options
    
    // Simple keyword-based retrieval (in production, use embeddings)
    const queryTerms = new Set(
      query.toLowerCase()
        .split(/\W+/)
        .filter(w => w.length > 3)
    )
    
    const scoredMemories = this.memories
      .filter(m => {
        if (types && !types.includes(m.type)) return false
        if (this.calculateImportance(m) < minImportance) return false
        return true
      })
      .map(memory => {
        const memoryTerms = memory.content.toLowerCase().split(/\W+/)
        const matchCount = memoryTerms.filter(t => queryTerms.has(t)).length
        const relevance = matchCount / Math.max(queryTerms.size, 1)
        
        // Also check tags
        const tagMatches = memory.tags.filter(t => 
          queryTerms.has(t.toLowerCase())
        ).length
        
        const score = relevance + (tagMatches * 0.1) + (this.calculateImportance(memory) * 0.3)
        
        return { memory, score }
      })
      .filter(({ score }) => score > 0.1)
      .sort((a, b) => b.score - a.score)
      .slice(0, limit)
    
    // Update access counts
    for (const { memory } of scoredMemories) {
      memory.lastAccessed = new Date()
      memory.accessCount++
    }
    this.saveMemories()
    
    return scoredMemories.map(({ memory }) => memory)
  }
  
  /**
   * Start a new conversation context
   */
  startConversation(topic?: string): ConversationContext {
    this.currentContext = {
      id: `conv-${Date.now()}`,
      topic: topic || 'General',
      entities: [],
      keyPoints: [],
      userPreferences: { ...this.userProfile.preferences },
      previousQuestions: [],
      previousResponses: [],
      emotionalTone: 'neutral',
      expertise: 'intermediate',
    }
    
    this.saveContext()
    return this.currentContext
  }
  
  /**
   * Update conversation context with new exchange
   */
  updateContext(
    question: string,
    response: string,
    options: {
      entities?: string[]
      keyPoints?: string[]
      preferences?: Record<string, string>
    } = {}
  ): void {
    if (!this.currentContext) {
      this.startConversation()
    }
    
    const ctx = this.currentContext!
    
    // Add to history
    ctx.previousQuestions.push(question)
    ctx.previousResponses.push(response)
    
    // Keep last 10 exchanges
    if (ctx.previousQuestions.length > 10) {
      ctx.previousQuestions = ctx.previousQuestions.slice(-10)
      ctx.previousResponses = ctx.previousResponses.slice(-10)
    }
    
    // Update entities
    if (options.entities) {
      ctx.entities = [...new Set([...ctx.entities, ...options.entities])]
    }
    
    // Update key points
    if (options.keyPoints) {
      ctx.keyPoints = [...ctx.keyPoints, ...options.keyPoints].slice(-20)
    }
    
    // Update preferences
    if (options.preferences) {
      ctx.userPreferences = { ...ctx.userPreferences, ...options.preferences }
      this.userProfile.preferences = { ...this.userProfile.preferences, ...options.preferences }
      this.saveProfile()
    }
    
    // Detect expertise level from questions
    ctx.expertise = this.detectExpertise(question)
    
    // Detect emotional tone
    ctx.emotionalTone = this.detectTone(question)
    
    this.saveContext()
  }
  
  /**
   * Detect user expertise level
   */
  private detectExpertise(text: string): 'beginner' | 'intermediate' | 'expert' {
    const expertTerms = /\b(architecture|infrastructure|optimization|implementation|algorithm|protocol|framework)\b/gi
    const beginnerTerms = /\b(what is|how do I|explain|basic|simple|easy|help me understand)\b/gi
    
    const expertMatches = (text.match(expertTerms) || []).length
    const beginnerMatches = (text.match(beginnerTerms) || []).length
    
    if (expertMatches > 2) return 'expert'
    if (beginnerMatches > 1) return 'beginner'
    return 'intermediate'
  }
  
  /**
   * Detect emotional tone
   */
  private detectTone(text: string): string {
    if (/\b(urgent|asap|quickly|emergency|help)\b/i.test(text)) return 'urgent'
    if (/\b(confused|don't understand|unclear)\b/i.test(text)) return 'confused'
    if (/\b(frustrated|annoying|doesn't work)\b/i.test(text)) return 'frustrated'
    if (/\b(curious|wondering|interested)\b/i.test(text)) return 'curious'
    if (/\b(thanks|appreciate|great)\b/i.test(text)) return 'positive'
    return 'neutral'
  }
  
  /**
   * Get current context for prompt augmentation
   */
  getContextForPrompt(): string {
    const parts: string[] = []
    
    if (this.currentContext) {
      const ctx = this.currentContext
      
      // Add conversation summary
      if (ctx.keyPoints.length > 0) {
        parts.push('**Context from this conversation:**')
        ctx.keyPoints.slice(-5).forEach(point => parts.push(`- ${point}`))
        parts.push('')
      }
      
      // Add user expertise
      if (ctx.expertise !== 'intermediate') {
        parts.push(`**User expertise level:** ${ctx.expertise}`)
        if (ctx.expertise === 'beginner') {
          parts.push('Explain concepts simply and avoid jargon.')
        } else if (ctx.expertise === 'expert') {
          parts.push('User has advanced knowledge; technical depth is appropriate.')
        }
        parts.push('')
      }
      
      // Add emotional tone awareness
      if (ctx.emotionalTone !== 'neutral') {
        parts.push(`**User tone:** ${ctx.emotionalTone}`)
        if (ctx.emotionalTone === 'urgent') {
          parts.push('Prioritize a quick, actionable response.')
        } else if (ctx.emotionalTone === 'frustrated') {
          parts.push('Be empathetic and provide clear solutions.')
        }
        parts.push('')
      }
    }
    
    // Add relevant long-term memories
    // (This would be called with the current query in practice)
    
    return parts.join('\n')
  }
  
  /**
   * Learn from a conversation
   */
  learnFromConversation(): void {
    if (!this.currentContext) return
    
    const ctx = this.currentContext
    
    // Extract facts to remember
    for (const point of ctx.keyPoints) {
      if (point.length > 20) {
        this.addMemory(point, 'fact', {
          importance: 0.6,
          tags: ctx.entities,
          sourceConversation: ctx.id,
        })
      }
    }
    
    // Learn topic preferences
    if (ctx.topic && ctx.topic !== 'General') {
      this.userProfile.frequentTopics.push(ctx.topic)
      // Keep unique topics
      this.userProfile.frequentTopics = [...new Set(this.userProfile.frequentTopics)].slice(-20)
      this.saveProfile()
    }
    
    // Update expertise for domain
    if (ctx.entities.length > 0) {
      const domain = ctx.entities[0]
      this.userProfile.expertise[domain] = ctx.expertise
      this.saveProfile()
    }
  }
  
  /**
   * Build context window for LLM
   */
  buildContextWindow(query: string): ContextWindow {
    const shortTerm: MemoryEntry[] = []
    const mediumTerm: MemoryEntry[] = []
    const longTerm: MemoryEntry[] = []
    
    // Add current conversation as short-term
    if (this.currentContext) {
      for (let i = 0; i < this.currentContext.previousQuestions.length; i++) {
        shortTerm.push({
          id: `short-${i}`,
          type: 'context',
          content: `Q: ${this.currentContext.previousQuestions[i]}\nA: ${this.currentContext.previousResponses[i]}`,
          importance: 0.8,
          created: new Date(),
          lastAccessed: new Date(),
          accessCount: 1,
          tags: [],
        })
      }
    }
    
    // Retrieve relevant long-term memories
    const relevantMemories = this.retrieveMemories(query, { limit: 15 })
    
    for (const memory of relevantMemories) {
      if (memory.type === 'context') {
        mediumTerm.push(memory)
      } else {
        longTerm.push(memory)
      }
    }
    
    // Estimate tokens (rough: 4 chars per token)
    const estimateTokens = (entries: MemoryEntry[]) => 
      entries.reduce((sum, e) => sum + Math.ceil(e.content.length / 4), 0)
    
    return {
      shortTerm,
      mediumTerm,
      longTerm,
      maxTokens: this.maxShortTermTokens,
      currentTokens: estimateTokens([...shortTerm, ...mediumTerm, ...longTerm]),
    }
  }
  
  /**
   * Clear all memories (for privacy)
   */
  clearMemories(): void {
    this.memories = []
    this.currentContext = null
    this.userProfile = this.createDefaultProfile()
    
    if (typeof window !== 'undefined') {
      localStorage.removeItem(MEMORY_KEY)
      localStorage.removeItem(CONTEXT_KEY)
      localStorage.removeItem(PROFILE_KEY)
    }
  }
  
  /**
   * Export memories for backup
   */
  exportMemories(): string {
    return JSON.stringify({
      memories: this.memories,
      profile: this.userProfile,
      context: this.currentContext,
    }, null, 2)
  }
  
  /**
   * Import memories from backup
   */
  importMemories(data: string): boolean {
    try {
      const parsed = JSON.parse(data)
      
      if (parsed.memories) {
        this.memories = parsed.memories
        this.saveMemories()
      }
      
      if (parsed.profile) {
        this.userProfile = parsed.profile
        this.saveProfile()
      }
      
      if (parsed.context) {
        this.currentContext = parsed.context
        this.saveContext()
      }
      
      return true
    } catch (error) {
      console.error('Error importing memories:', error)
      return false
    }
  }
}

// Singleton instance
let memoryInstance: MemoryManager | null = null

export function getMemoryManager(): MemoryManager {
  if (!memoryInstance) {
    memoryInstance = new MemoryManager()
  }
  return memoryInstance
}

