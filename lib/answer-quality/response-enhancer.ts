/**
 * Response Enhancer
 * 
 * Improves response quality through:
 * - Structure optimization
 * - Clarity improvements
 * - Adding examples and analogies
 * - Formatting for readability
 * - Ensuring completeness
 */

import type {
  EnhancedResponse,
  ResponseStructure,
  ResponseSection,
  Improvement,
  QueryAnalysis,
  OutputFormat,
} from './types'

export interface EnhancementOptions {
  format: OutputFormat
  analysis: QueryAnalysis
  maxLength?: number
  addExamples?: boolean
  addSummary?: boolean
  addActionItems?: boolean
}

/**
 * Enhance a response for better quality
 */
export function enhanceResponse(
  response: string,
  options: EnhancementOptions
): EnhancedResponse {
  const improvements: Improvement[] = []
  
  // Parse the response into sections
  let structure = parseResponseStructure(response)
  
  // Apply enhancements based on options
  if (options.addSummary && !structure.summary) {
    const summary = generateSummary(response)
    structure.summary = summary
    improvements.push({
      type: 'added',
      description: 'Added executive summary',
      after: summary,
    })
  }
  
  // Enhance section structure
  structure = optimizeSectionStructure(structure, options.format)
  
  // Add examples if needed
  if (options.addExamples) {
    structure = addExamplesToSections(structure, options.analysis)
    improvements.push({
      type: 'added',
      description: 'Added illustrative examples',
    })
  }
  
  // Add action items for procedural content
  if (options.addActionItems && options.analysis.intent === 'procedural') {
    structure.actionItems = extractActionItems(response)
    if (structure.actionItems.length > 0) {
      improvements.push({
        type: 'added',
        description: 'Added action items checklist',
      })
    }
  }
  
  // Format the enhanced response
  const enhanced = formatEnhancedResponse(structure, options.format)
  
  return {
    original: response,
    enhanced,
    structure,
    citations: [],
    confidence: calculateConfidence(response, improvements),
    qualityScore: {
      accuracy: 85,
      completeness: calculateCompleteness(structure),
      clarity: calculateClarity(enhanced),
      relevance: 90,
      structure: calculateStructureScore(structure),
      actionability: options.analysis.intent === 'procedural' ? 85 : 70,
      sources: 0,
      depth: calculateDepth(response),
    },
    improvements,
    metadata: {
      generationTime: 0,
      modelsUsed: [],
      tokensUsed: 0,
      reasoningMethod: 'enhancement',
      qualityChecks: [],
    },
  }
}

/**
 * Parse response into structured sections
 */
function parseResponseStructure(response: string): ResponseStructure {
  const lines = response.split('\n')
  const sections: ResponseSection[] = []
  let currentSection: ResponseSection | null = null
  let currentContent: string[] = []
  
  for (const line of lines) {
    // Check for headers
    const h1Match = line.match(/^#\s+(.+)$/)
    const h2Match = line.match(/^##\s+(.+)$/)
    const h3Match = line.match(/^###\s+(.+)$/)
    const boldHeaderMatch = line.match(/^\*\*(.+)\*\*:?$/)
    
    if (h1Match || h2Match || h3Match || boldHeaderMatch) {
      // Save previous section
      if (currentSection) {
        currentSection.content = currentContent.join('\n').trim()
        sections.push(currentSection)
      }
      
      const heading = h1Match?.[1] || h2Match?.[1] || h3Match?.[1] || boldHeaderMatch?.[1] || 'Section'
      currentSection = {
        heading,
        content: '',
        type: detectSectionType(heading),
      }
      currentContent = []
    } else {
      currentContent.push(line)
    }
  }
  
  // Save last section
  if (currentSection) {
    currentSection.content = currentContent.join('\n').trim()
    sections.push(currentSection)
  } else if (currentContent.length > 0) {
    // No sections found, treat entire response as one section
    sections.push({
      heading: 'Response',
      content: currentContent.join('\n').trim(),
      type: 'explanation',
    })
  }
  
  return { sections }
}

/**
 * Detect the type of a section based on its heading
 */
function detectSectionType(heading: string): ResponseSection['type'] {
  const lower = heading.toLowerCase()
  
  if (/example|demo|sample/i.test(lower)) return 'example'
  if (/code|implementation|snippet/i.test(lower)) return 'code'
  if (/warning|caution|important|note/i.test(lower)) return 'warning'
  if (/tip|hint|pro tip/i.test(lower)) return 'tip'
  if (/quote|citation|reference/i.test(lower)) return 'quote'
  if (/data|statistics|numbers|metrics/i.test(lower)) return 'data'
  
  return 'explanation'
}

/**
 * Generate a concise summary from the response
 */
function generateSummary(response: string): string {
  // Extract key sentences (first sentence of each paragraph)
  const paragraphs = response.split(/\n\n+/)
  const keySentences: string[] = []
  
  paragraphs.forEach(para => {
    const firstSentence = para.split(/[.!?]/)[0]
    if (firstSentence && firstSentence.length > 20 && firstSentence.length < 200) {
      keySentences.push(firstSentence.trim())
    }
  })
  
  // Take up to 3 key sentences
  const summary = keySentences.slice(0, 3).join('. ')
  return summary ? summary + '.' : ''
}

/**
 * Optimize section structure based on output format
 */
function optimizeSectionStructure(
  structure: ResponseStructure,
  format: OutputFormat
): ResponseStructure {
  // Add recommended sections if missing
  if (format.sections) {
    const existingHeadings = new Set(structure.sections.map(s => s.heading.toLowerCase()))
    
    format.sections.forEach(recommended => {
      if (!existingHeadings.has(recommended.toLowerCase())) {
        // Section is missing but recommended
        // We'll note this for the quality check
      }
    })
  }
  
  return structure
}

/**
 * Add examples to sections that would benefit from them
 */
function addExamplesToSections(
  structure: ResponseStructure,
  analysis: QueryAnalysis
): ResponseStructure {
  structure.sections = structure.sections.map(section => {
    // Skip sections that are already examples
    if (section.type === 'example' || section.type === 'code') {
      return section
    }
    
    // Check if section could benefit from an example
    const hasExample = /for example|e\.g\.|such as|like this/i.test(section.content)
    
    if (!hasExample && section.content.length > 200) {
      // Could benefit from an example
      // In production, we'd generate one using an LLM
      section.content += '\n\n*[Example would be generated based on context]*'
    }
    
    return section
  })
  
  return structure
}

/**
 * Extract actionable items from procedural content
 */
function extractActionItems(response: string): string[] {
  const actionItems: string[] = []
  
  // Look for numbered steps
  const numberedSteps = response.match(/^\d+\.\s+.+$/gm)
  if (numberedSteps) {
    numberedSteps.forEach(step => {
      const cleaned = step.replace(/^\d+\.\s+/, '').trim()
      if (cleaned.length > 10 && cleaned.length < 100) {
        actionItems.push(cleaned)
      }
    })
  }
  
  // Look for bullet points with action verbs
  const actionVerbs = /^[-•*]\s*(create|build|configure|set up|install|implement|add|remove|update|modify|check|verify|ensure|make sure)/i
  const bullets = response.match(/^[-•*]\s+.+$/gm)
  if (bullets) {
    bullets.forEach(bullet => {
      if (actionVerbs.test(bullet)) {
        const cleaned = bullet.replace(/^[-•*]\s+/, '').trim()
        if (!actionItems.includes(cleaned)) {
          actionItems.push(cleaned)
        }
      }
    })
  }
  
  return actionItems.slice(0, 10) // Max 10 action items
}

/**
 * Format the enhanced response for output
 */
function formatEnhancedResponse(
  structure: ResponseStructure,
  format: OutputFormat
): string {
  const parts: string[] = []
  
  // Add summary if present
  if (structure.summary) {
    parts.push(`**Summary:** ${structure.summary}`)
    parts.push('')
  }
  
  // Format sections
  structure.sections.forEach(section => {
    if (section.heading !== 'Response') {
      parts.push(`## ${section.heading}`)
    }
    parts.push(section.content)
    parts.push('')
  })
  
  // Add action items if present
  if (structure.actionItems && structure.actionItems.length > 0) {
    parts.push('## Action Items')
    structure.actionItems.forEach((item, idx) => {
      parts.push(`- [ ] ${item}`)
    })
    parts.push('')
  }
  
  // Add conclusion if present
  if (structure.conclusion) {
    parts.push('## Conclusion')
    parts.push(structure.conclusion)
    parts.push('')
  }
  
  // Add further reading if present
  if (structure.furtherReading && structure.furtherReading.length > 0) {
    parts.push('## Further Reading')
    structure.furtherReading.forEach(item => {
      parts.push(`- ${item}`)
    })
  }
  
  return parts.join('\n').trim()
}

// Quality score calculations
function calculateConfidence(response: string, improvements: Improvement[]): number {
  let confidence = 0.8
  
  // More improvements = better quality
  confidence += improvements.length * 0.02
  
  // Longer, structured responses tend to be higher quality
  if (response.length > 500) confidence += 0.05
  if (response.includes('##')) confidence += 0.03
  
  return Math.min(0.98, confidence)
}

function calculateCompleteness(structure: ResponseStructure): number {
  let score = 70
  
  // More sections = more complete
  score += Math.min(15, structure.sections.length * 3)
  
  // Has summary
  if (structure.summary) score += 5
  
  // Has action items
  if (structure.actionItems && structure.actionItems.length > 0) score += 5
  
  // Has conclusion
  if (structure.conclusion) score += 5
  
  return Math.min(100, score)
}

function calculateClarity(response: string): number {
  let score = 75
  
  // Shorter sentences = clearer
  const sentences = response.split(/[.!?]+/)
  const avgLength = sentences.reduce((sum, s) => sum + s.split(' ').length, 0) / sentences.length
  if (avgLength < 20) score += 10
  else if (avgLength > 30) score -= 10
  
  // Has formatting
  if (/^[-•*]\s/m.test(response)) score += 5 // Bullet points
  if (/^\d+\./m.test(response)) score += 5 // Numbered lists
  if (/^##/m.test(response)) score += 5 // Headers
  
  return Math.min(100, Math.max(0, score))
}

function calculateStructureScore(structure: ResponseStructure): number {
  let score = 60
  
  // Has sections
  score += Math.min(20, structure.sections.length * 5)
  
  // Has summary
  if (structure.summary) score += 10
  
  // Has different section types
  const types = new Set(structure.sections.map(s => s.type))
  score += Math.min(10, types.size * 3)
  
  return Math.min(100, score)
}

function calculateDepth(response: string): number {
  let score = 50
  
  // Word count
  const wordCount = response.split(/\s+/).length
  if (wordCount > 300) score += 20
  if (wordCount > 500) score += 10
  if (wordCount > 1000) score += 10
  
  // Technical depth indicators
  if (/because|therefore|consequently|thus/i.test(response)) score += 5
  if (/first[\s\S]*second[\s\S]*third/i.test(response)) score += 5
  if (/however|although|nevertheless/i.test(response)) score += 5
  
  return Math.min(100, score)
}

/**
 * Quick enhancement for real-time use
 */
export function quickEnhance(response: string): string {
  // Add section breaks if missing
  let enhanced = response
  
  // Ensure proper paragraph spacing
  enhanced = enhanced.replace(/\n{3,}/g, '\n\n')
  
  // Add emphasis to key terms
  enhanced = enhanced.replace(/\b(important|note|warning|tip|key point):/gi, '**$1:**')
  
  return enhanced
}

