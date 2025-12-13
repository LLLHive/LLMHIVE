/**
 * Domain Templates
 * 
 * Pre-configured templates for specific domains and query types
 * to ensure consistent, high-quality responses.
 */

import type { DomainTemplate, OutputFormat, QueryIntent } from './types'

// Template registry
export const DOMAIN_TEMPLATES: Record<string, DomainTemplate> = {
  // Technical/Code Templates
  'code-review': {
    id: 'code-review',
    domain: 'technology',
    name: 'Code Review',
    description: 'Comprehensive code review with actionable feedback',
    promptEnhancements: [
      'Review this code for: correctness, performance, security, maintainability, and best practices.',
      'Provide specific line-by-line feedback where applicable.',
      'Suggest concrete improvements with code examples.',
      'Rate the overall code quality on a scale of 1-10.',
    ],
    outputStructure: {
      type: 'structured',
      sections: ['Summary', 'Strengths', 'Issues', 'Recommendations', 'Improved Code'],
      includeExamples: true,
      includeSources: false,
    },
    qualityChecks: ['has-code-examples', 'specific-line-references', 'actionable-suggestions'],
    bestModels: ['gpt-4o', 'claude-sonnet-4', 'deepseek-chat'],
    examples: [],
  },

  'debugging': {
    id: 'debugging',
    domain: 'technology',
    name: 'Debugging Assistant',
    description: 'Systematic debugging with root cause analysis',
    promptEnhancements: [
      'Analyze this error/issue systematically.',
      'Identify the root cause, not just symptoms.',
      'Provide step-by-step debugging instructions.',
      'Include preventive measures for the future.',
    ],
    outputStructure: {
      type: 'structured',
      sections: ['Error Analysis', 'Root Cause', 'Solution', 'Prevention'],
      includeExamples: true,
      includeSources: false,
    },
    qualityChecks: ['has-root-cause', 'has-solution', 'has-prevention'],
    bestModels: ['gpt-4o', 'deepseek-chat'],
    examples: [],
  },

  'architecture': {
    id: 'architecture',
    domain: 'technology',
    name: 'System Architecture',
    description: 'System design and architecture guidance',
    promptEnhancements: [
      'Consider scalability, reliability, and maintainability.',
      'Include trade-offs for different approaches.',
      'Provide a high-level architecture diagram description.',
      'Address security and performance considerations.',
    ],
    outputStructure: {
      type: 'structured',
      sections: ['Overview', 'Components', 'Data Flow', 'Trade-offs', 'Recommendations'],
      includeExamples: true,
      includeSources: true,
    },
    qualityChecks: ['covers-scalability', 'covers-security', 'has-trade-offs'],
    bestModels: ['claude-sonnet-4', 'gpt-4o'],
    examples: [],
  },

  // Research Templates
  'research-deep': {
    id: 'research-deep',
    domain: 'research',
    name: 'Deep Research',
    description: 'Comprehensive research with citations',
    promptEnhancements: [
      'Provide a comprehensive analysis with multiple perspectives.',
      'Include relevant statistics and data points.',
      'Cite sources and indicate confidence levels.',
      'Address counterarguments and limitations.',
    ],
    outputStructure: {
      type: 'structured',
      sections: ['Executive Summary', 'Background', 'Key Findings', 'Analysis', 'Limitations', 'Conclusion'],
      includeExamples: true,
      includeSources: true,
    },
    qualityChecks: ['has-citations', 'multiple-perspectives', 'addresses-limitations'],
    bestModels: ['claude-sonnet-4', 'gemini-1.5-pro', 'gpt-4o'],
    examples: [],
  },

  'literature-review': {
    id: 'literature-review',
    domain: 'research',
    name: 'Literature Review',
    description: 'Academic-style literature review',
    promptEnhancements: [
      'Synthesize findings from multiple sources.',
      'Identify gaps in current research.',
      'Organize thematically or chronologically.',
      'Maintain academic tone and rigor.',
    ],
    outputStructure: {
      type: 'structured',
      sections: ['Introduction', 'Methodology', 'Themes', 'Gaps', 'Future Directions'],
      includeExamples: false,
      includeSources: true,
    },
    qualityChecks: ['academic-tone', 'synthesizes-sources', 'identifies-gaps'],
    bestModels: ['claude-sonnet-4', 'gpt-4o'],
    examples: [],
  },

  // Business Templates
  'business-analysis': {
    id: 'business-analysis',
    domain: 'business',
    name: 'Business Analysis',
    description: 'Strategic business analysis and recommendations',
    promptEnhancements: [
      'Apply relevant business frameworks (SWOT, Porter\'s, etc.).',
      'Include market context and competitive landscape.',
      'Provide data-driven insights where possible.',
      'Recommend specific, actionable next steps.',
    ],
    outputStructure: {
      type: 'structured',
      sections: ['Executive Summary', 'Situation Analysis', 'Key Insights', 'Recommendations', 'Next Steps'],
      includeExamples: true,
      includeSources: true,
    },
    qualityChecks: ['uses-frameworks', 'actionable-recommendations', 'data-backed'],
    bestModels: ['gpt-4o', 'claude-sonnet-4'],
    examples: [],
  },

  'strategy': {
    id: 'strategy',
    domain: 'business',
    name: 'Strategic Planning',
    description: 'Strategic planning and roadmap development',
    promptEnhancements: [
      'Consider short-term and long-term implications.',
      'Identify key success factors and risks.',
      'Provide measurable goals and milestones.',
      'Include resource and timeline considerations.',
    ],
    outputStructure: {
      type: 'structured',
      sections: ['Vision', 'Strategic Objectives', 'Key Initiatives', 'Timeline', 'Success Metrics', 'Risks'],
      includeExamples: true,
      includeSources: false,
    },
    qualityChecks: ['has-timeline', 'has-metrics', 'addresses-risks'],
    bestModels: ['claude-sonnet-4', 'gpt-4o'],
    examples: [],
  },

  // Creative Templates
  'writing-professional': {
    id: 'writing-professional',
    domain: 'creative',
    name: 'Professional Writing',
    description: 'Business and professional content writing',
    promptEnhancements: [
      'Use clear, professional language.',
      'Maintain appropriate tone for the context.',
      'Structure content for easy scanning.',
      'Include a clear call-to-action if applicable.',
    ],
    outputStructure: {
      type: 'prose',
      includeExamples: false,
      includeSources: false,
    },
    qualityChecks: ['professional-tone', 'clear-structure', 'appropriate-length'],
    bestModels: ['gpt-4o', 'claude-sonnet-4'],
    examples: [],
  },

  'writing-creative': {
    id: 'writing-creative',
    domain: 'creative',
    name: 'Creative Writing',
    description: 'Creative content with engaging narrative',
    promptEnhancements: [
      'Use vivid, descriptive language.',
      'Create engaging narrative flow.',
      'Develop authentic voice and style.',
      'Include sensory details and emotion.',
    ],
    outputStructure: {
      type: 'prose',
      includeExamples: false,
      includeSources: false,
    },
    qualityChecks: ['engaging-narrative', 'sensory-details', 'consistent-voice'],
    bestModels: ['gpt-4o', 'claude-sonnet-4'],
    examples: [],
  },

  // Educational Templates
  'tutorial': {
    id: 'tutorial',
    domain: 'education',
    name: 'Tutorial/How-To',
    description: 'Step-by-step educational tutorial',
    promptEnhancements: [
      'Break down into clear, numbered steps.',
      'Explain why each step is important.',
      'Anticipate common mistakes and address them.',
      'Include practice exercises if applicable.',
    ],
    outputStructure: {
      type: 'list',
      sections: ['Prerequisites', 'Steps', 'Common Mistakes', 'Practice'],
      includeExamples: true,
      includeSources: false,
    },
    qualityChecks: ['clear-steps', 'explains-why', 'addresses-mistakes'],
    bestModels: ['gpt-4o', 'claude-sonnet-4'],
    examples: [],
  },

  'explanation': {
    id: 'explanation',
    domain: 'education',
    name: 'Concept Explanation',
    description: 'Clear explanation of concepts for learning',
    promptEnhancements: [
      'Start with a simple overview before details.',
      'Use analogies to make concepts relatable.',
      'Build from fundamentals to advanced topics.',
      'Include visual descriptions where helpful.',
    ],
    outputStructure: {
      type: 'structured',
      sections: ['Overview', 'Key Concepts', 'How It Works', 'Examples', 'Related Topics'],
      includeExamples: true,
      includeSources: false,
    },
    qualityChecks: ['has-analogies', 'builds-progressively', 'accessible-language'],
    bestModels: ['claude-sonnet-4', 'gpt-4o'],
    examples: [],
  },

  // Comparison Templates
  'comparison-detailed': {
    id: 'comparison-detailed',
    domain: 'analysis',
    name: 'Detailed Comparison',
    description: 'Comprehensive comparison of options',
    promptEnhancements: [
      'Create a structured comparison matrix.',
      'Evaluate across multiple relevant criteria.',
      'Provide a clear recommendation based on use case.',
      'Acknowledge trade-offs for each option.',
    ],
    outputStructure: {
      type: 'table',
      sections: ['Overview', 'Comparison Matrix', 'Detailed Analysis', 'Recommendations'],
      includeExamples: true,
      includeSources: true,
    },
    qualityChecks: ['has-matrix', 'multiple-criteria', 'clear-recommendation'],
    bestModels: ['claude-sonnet-4', 'gpt-4o'],
    examples: [],
  },

  // Problem-Solving Templates
  'troubleshooting-systematic': {
    id: 'troubleshooting-systematic',
    domain: 'technology',
    name: 'Systematic Troubleshooting',
    description: 'Methodical problem diagnosis and resolution',
    promptEnhancements: [
      'Start with most likely causes first.',
      'Provide verification steps for each solution.',
      'Include rollback/undo instructions if applicable.',
      'Explain how to prevent recurrence.',
    ],
    outputStructure: {
      type: 'list',
      sections: ['Quick Fixes', 'Diagnostic Steps', 'Solutions', 'Prevention'],
      includeExamples: true,
      includeSources: false,
    },
    qualityChecks: ['prioritized-solutions', 'has-verification', 'has-prevention'],
    bestModels: ['gpt-4o', 'deepseek-chat'],
    examples: [],
  },
}

/**
 * Get template for a query based on intent and domain
 */
export function getTemplateForQuery(intent: QueryIntent, domain: string): DomainTemplate | null {
  // Intent-based template selection
  const intentTemplates: Record<QueryIntent, string[]> = {
    procedural: ['tutorial', 'troubleshooting-systematic'],
    code: ['code-review', 'debugging', 'architecture'],
    troubleshooting: ['troubleshooting-systematic', 'debugging'],
    research: ['research-deep', 'literature-review'],
    analytical: ['business-analysis', 'research-deep'],
    comparative: ['comparison-detailed'],
    creative: ['writing-creative', 'writing-professional'],
    factual: ['explanation'],
    opinion: [],
    conversational: [],
    summarization: [],
    translation: [],
    extraction: [],
  }
  
  const candidates = intentTemplates[intent] || []
  
  // Find best matching template
  for (const templateId of candidates) {
    const template = DOMAIN_TEMPLATES[templateId]
    if (template && (template.domain === domain || domain === 'general')) {
      return template
    }
  }
  
  // Fallback to domain-based selection
  for (const template of Object.values(DOMAIN_TEMPLATES)) {
    if (template.domain === domain) {
      return template
    }
  }
  
  return null
}

/**
 * Apply template to prompt
 */
export function applyTemplate(prompt: string, template: DomainTemplate): string {
  const parts: string[] = [prompt]
  
  // Add template enhancements
  if (template.promptEnhancements.length > 0) {
    parts.push('\n\nPlease ensure your response:')
    template.promptEnhancements.forEach((enhancement, idx) => {
      parts.push(`${idx + 1}. ${enhancement}`)
    })
  }
  
  // Add structure requirements
  if (template.outputStructure.sections) {
    parts.push(`\n\nStructure your response with these sections: ${template.outputStructure.sections.join(', ')}.`)
  }
  
  return parts.join('\n')
}

/**
 * Validate response against template quality checks
 */
export function validateAgainstTemplate(
  response: string,
  template: DomainTemplate
): { passed: boolean; score: number; failures: string[] } {
  const failures: string[] = []
  let passedChecks = 0
  
  for (const check of template.qualityChecks) {
    const passed = runQualityCheck(response, check)
    if (passed) {
      passedChecks++
    } else {
      failures.push(check)
    }
  }
  
  const score = template.qualityChecks.length > 0 
    ? (passedChecks / template.qualityChecks.length) * 100 
    : 100
  
  return {
    passed: failures.length === 0,
    score,
    failures,
  }
}

/**
 * Run a specific quality check
 */
function runQualityCheck(response: string, checkName: string): boolean {
  const checks: Record<string, (r: string) => boolean> = {
    'has-code-examples': (r) => /```[\s\S]*```/.test(r),
    'specific-line-references': (r) => /line \d+|lines? \d+(-\d+)?/i.test(r),
    'actionable-suggestions': (r) => /should|recommend|suggest|consider|try/i.test(r),
    'has-root-cause': (r) => /root cause|because|due to|caused by/i.test(r),
    'has-solution': (r) => /solution|fix|resolve|to solve/i.test(r),
    'has-prevention': (r) => /prevent|avoid|future|next time/i.test(r),
    'covers-scalability': (r) => /scal(e|able|ability)|growth|load/i.test(r),
    'covers-security': (r) => /secur(e|ity)|vulnerab|auth|encrypt/i.test(r),
    'has-trade-offs': (r) => /trade-?off|pros? and cons?|however|but|although/i.test(r),
    'has-citations': (r) => /\[\d+\]|according to|source:|cited/i.test(r),
    'multiple-perspectives': (r) => /perspective|view|approach|on the other hand/i.test(r),
    'addresses-limitations': (r) => /limit(ation)?|caveat|note that|however/i.test(r),
    'academic-tone': (r) => /research|study|findings|evidence|methodology/i.test(r),
    'synthesizes-sources': (r) => /combined|together|overall|in summary/i.test(r),
    'identifies-gaps': (r) => /gap|missing|lack|need for|future/i.test(r),
    'uses-frameworks': (r) => /SWOT|Porter|framework|model|matrix/i.test(r),
    'actionable-recommendations': (r) => /recommend|should|next step|action/i.test(r),
    'data-backed': (r) => /\d+%|\d+ percent|statistics|data shows/i.test(r),
    'has-timeline': (r) => /timeline|phase|week|month|quarter|year/i.test(r),
    'has-metrics': (r) => /metric|KPI|measure|goal|target/i.test(r),
    'addresses-risks': (r) => /risk|challenge|obstacle|threat/i.test(r),
    'professional-tone': (r) => !/lol|omg|gonna|wanna|btw/i.test(r),
    'clear-structure': (r) => /^(#{1,3}|\d+\.|\*|\-)/m.test(r),
    'appropriate-length': (r) => r.length > 200 && r.length < 10000,
    'engaging-narrative': (r) => /felt|saw|heard|touched|imagined/i.test(r),
    'sensory-details': (r) => /color|sound|smell|taste|texture/i.test(r),
    'consistent-voice': () => true, // Complex check, default to pass
    'clear-steps': (r) => /\b(step \d|first|second|third|then|next|finally)\b/i.test(r),
    'explains-why': (r) => /because|reason|important because|this ensures/i.test(r),
    'addresses-mistakes': (r) => /mistake|error|avoid|don't|common issue/i.test(r),
    'has-analogies': (r) => /like|similar to|think of|imagine|analogy/i.test(r),
    'builds-progressively': (r) => /first|then|now|finally|building on/i.test(r),
    'accessible-language': (r) => !/(?:\b\w{15,}\b.*){5,}/i.test(r), // No more than 5 very long words
    'has-matrix': (r) => /\|.*\|.*\|/m.test(r) || /comparison|matrix|table/i.test(r),
    'multiple-criteria': (r) => (r.match(/\b(criterion|criteria|factor|aspect|dimension)\b/gi) || []).length >= 2,
    'clear-recommendation': (r) => /recommend|best choice|winner|prefer|suggest/i.test(r),
    'prioritized-solutions': (r) => /first|most likely|primary|start with/i.test(r),
    'has-verification': (r) => /verify|confirm|check|test|ensure/i.test(r),
  }
  
  const checkFn = checks[checkName]
  return checkFn ? checkFn(response) : true
}

/**
 * Get all templates for a domain
 */
export function getTemplatesForDomain(domain: string): DomainTemplate[] {
  return Object.values(DOMAIN_TEMPLATES).filter(t => t.domain === domain)
}

/**
 * List all available templates
 */
export function listTemplates(): { id: string; name: string; domain: string }[] {
  return Object.values(DOMAIN_TEMPLATES).map(t => ({
    id: t.id,
    name: t.name,
    domain: t.domain,
  }))
}

