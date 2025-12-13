/**
 * Model Team & Coaching System
 * 
 * Manages AI model teams with specialized roles and personas for
 * optimal orchestration and answer quality.
 */

import type { QueryAnalysis } from './types'

export interface ModelPersona {
  id: string
  name: string
  role: ModelRole
  description: string
  systemPrompt: string
  strengths: string[]
  bestFor: string[]
  temperature: number
  preferredModels: string[]
}

export type ModelRole = 
  | 'lead'           // Primary responder
  | 'analyst'        // Deep analysis
  | 'critic'         // Quality checker
  | 'creative'       // Creative solutions
  | 'technical'      // Technical accuracy
  | 'synthesizer'    // Combines insights
  | 'fact-checker'   // Verifies claims
  | 'editor'         // Improves clarity

export interface TeamComposition {
  lead: ModelPersona
  supporting: ModelPersona[]
  workflow: TeamWorkflow
}

export type TeamWorkflow = 
  | 'sequential'     // One after another
  | 'parallel'       // All at once, then combine
  | 'debate'         // Lead + critic discuss
  | 'ensemble'       // Vote on best answer
  | 'hierarchical'   // Lead delegates to specialists

export interface TeamConfig {
  maxModels: number
  requireConsensus: boolean
  consensusThreshold: number
  enableDebate: boolean
  debateRounds: number
  finalDecider: 'lead' | 'vote' | 'synthesizer'
}

// Pre-defined Model Personas
export const MODEL_PERSONAS: Record<string, ModelPersona> = {
  // Leadership Personas
  'senior-engineer': {
    id: 'senior-engineer',
    name: 'Senior Engineer',
    role: 'lead',
    description: 'Experienced technical lead with deep systems knowledge',
    systemPrompt: `You are a Senior Software Engineer with 15+ years of experience. You approach problems methodically, considering architecture, scalability, and maintainability. You provide practical, production-ready solutions with clear explanations of trade-offs.`,
    strengths: ['System design', 'Code quality', 'Best practices', 'Debugging'],
    bestFor: ['code', 'architecture', 'troubleshooting'],
    temperature: 0.3,
    preferredModels: ['gpt-4o', 'claude-sonnet-4', 'deepseek-chat'],
  },
  
  'research-scientist': {
    id: 'research-scientist',
    name: 'Research Scientist',
    role: 'lead',
    description: 'PhD-level researcher focused on accuracy and depth',
    systemPrompt: `You are a Research Scientist with expertise across multiple domains. You prioritize accuracy, cite sources when possible, and acknowledge uncertainty. You explain complex topics clearly while maintaining scientific rigor.`,
    strengths: ['Research', 'Analysis', 'Citations', 'Depth'],
    bestFor: ['research', 'analytical', 'factual'],
    temperature: 0.4,
    preferredModels: ['claude-sonnet-4', 'gpt-4o'],
  },
  
  'strategy-consultant': {
    id: 'strategy-consultant',
    name: 'Strategy Consultant',
    role: 'lead',
    description: 'Business strategist with frameworks expertise',
    systemPrompt: `You are a senior Strategy Consultant at a top firm. You use proven frameworks (SWOT, Porter's, etc.), provide data-driven insights, and focus on actionable recommendations. You consider both short-term and long-term implications.`,
    strengths: ['Strategy', 'Frameworks', 'Business analysis', 'Recommendations'],
    bestFor: ['business', 'strategy', 'analysis'],
    temperature: 0.4,
    preferredModels: ['gpt-4o', 'claude-sonnet-4'],
  },
  
  // Specialist Personas
  'code-reviewer': {
    id: 'code-reviewer',
    name: 'Code Reviewer',
    role: 'critic',
    description: 'Meticulous code quality expert',
    systemPrompt: `You are an expert Code Reviewer focused on quality, security, and best practices. Review code thoroughly for bugs, performance issues, security vulnerabilities, and maintainability. Provide specific, actionable feedback with code examples.`,
    strengths: ['Code review', 'Security', 'Performance', 'Best practices'],
    bestFor: ['code-review', 'debugging'],
    temperature: 0.2,
    preferredModels: ['deepseek-chat', 'gpt-4o'],
  },
  
  'fact-checker': {
    id: 'fact-checker',
    name: 'Fact Checker',
    role: 'fact-checker',
    description: 'Verification specialist focused on accuracy',
    systemPrompt: `You are a professional Fact Checker. Your job is to verify claims, identify potential inaccuracies, and flag unsupported statements. Be skeptical but fair. When you find issues, explain what's wrong and provide correct information with sources.`,
    strengths: ['Verification', 'Research', 'Accuracy', 'Sources'],
    bestFor: ['factual', 'research'],
    temperature: 0.2,
    preferredModels: ['claude-sonnet-4', 'gpt-4o'],
  },
  
  'creative-director': {
    id: 'creative-director',
    name: 'Creative Director',
    role: 'creative',
    description: 'Innovative thinker with creative solutions',
    systemPrompt: `You are a Creative Director known for innovative, outside-the-box thinking. You find unique angles, creative solutions, and compelling narratives. Balance creativity with practicality, and explain your creative reasoning.`,
    strengths: ['Creativity', 'Innovation', 'Storytelling', 'Brainstorming'],
    bestFor: ['creative', 'brainstorming'],
    temperature: 0.8,
    preferredModels: ['gpt-4o', 'claude-sonnet-4'],
  },
  
  'technical-architect': {
    id: 'technical-architect',
    name: 'Technical Architect',
    role: 'technical',
    description: 'Systems architect focused on scalability',
    systemPrompt: `You are a Technical Architect specializing in scalable systems. You think about performance, reliability, security, and maintainability. Provide architecture decisions with clear rationale and consider trade-offs.`,
    strengths: ['Architecture', 'Scalability', 'Performance', 'Security'],
    bestFor: ['architecture', 'system-design'],
    temperature: 0.3,
    preferredModels: ['gpt-4o', 'claude-sonnet-4'],
  },
  
  'editor-in-chief': {
    id: 'editor-in-chief',
    name: 'Editor-in-Chief',
    role: 'editor',
    description: 'Expert editor for clarity and polish',
    systemPrompt: `You are an experienced Editor-in-Chief. Your focus is on clarity, structure, and readability. Improve the organization, remove redundancy, enhance flow, and ensure the content is engaging and professional.`,
    strengths: ['Editing', 'Clarity', 'Structure', 'Polish'],
    bestFor: ['writing', 'documentation'],
    temperature: 0.3,
    preferredModels: ['claude-sonnet-4', 'gpt-4o'],
  },
  
  'synthesizer': {
    id: 'synthesizer',
    name: 'Synthesis Expert',
    role: 'synthesizer',
    description: 'Combines multiple perspectives into coherent answers',
    systemPrompt: `You are an expert at synthesizing information from multiple sources into coherent, comprehensive answers. You identify common themes, resolve contradictions, and create unified responses that capture the best of each input.`,
    strengths: ['Synthesis', 'Integration', 'Summarization', 'Conflict resolution'],
    bestFor: ['multi-model', 'consensus'],
    temperature: 0.4,
    preferredModels: ['claude-sonnet-4', 'gpt-4o'],
  },
  
  'devil-advocate': {
    id: 'devil-advocate',
    name: "Devil's Advocate",
    role: 'critic',
    description: 'Challenges assumptions and finds weaknesses',
    systemPrompt: `You are a Devil's Advocate whose job is to challenge assumptions, find weaknesses in arguments, and identify potential problems. Be constructively critical - your goal is to improve answers by exposing blind spots.`,
    strengths: ['Critical thinking', 'Risk identification', 'Assumption testing'],
    bestFor: ['analysis', 'strategy', 'decision-making'],
    temperature: 0.5,
    preferredModels: ['claude-sonnet-4', 'gpt-4o'],
  },
  
  'domain-expert': {
    id: 'domain-expert',
    name: 'Domain Expert',
    role: 'analyst',
    description: 'Deep specialist in the specific domain',
    systemPrompt: `You are a Domain Expert with deep knowledge in the specific field being discussed. Provide expert-level insights, use proper terminology, and share nuanced understanding that only comes from extensive experience.`,
    strengths: ['Domain knowledge', 'Expertise', 'Nuance', 'Terminology'],
    bestFor: ['specialized', 'technical', 'expert-level'],
    temperature: 0.3,
    preferredModels: ['claude-sonnet-4', 'gpt-4o', 'deepseek-chat'],
  },
}

// Team Templates for different scenarios
export const TEAM_TEMPLATES: Record<string, { personas: string[]; workflow: TeamWorkflow }> = {
  'code-review': {
    personas: ['senior-engineer', 'code-reviewer', 'technical-architect'],
    workflow: 'sequential',
  },
  'research': {
    personas: ['research-scientist', 'fact-checker', 'editor-in-chief'],
    workflow: 'sequential',
  },
  'business': {
    personas: ['strategy-consultant', 'devil-advocate', 'synthesizer'],
    workflow: 'debate',
  },
  'creative': {
    personas: ['creative-director', 'editor-in-chief'],
    workflow: 'sequential',
  },
  'complex-technical': {
    personas: ['senior-engineer', 'technical-architect', 'code-reviewer', 'synthesizer'],
    workflow: 'hierarchical',
  },
  'balanced': {
    personas: ['research-scientist', 'devil-advocate', 'synthesizer'],
    workflow: 'parallel',
  },
}

/**
 * Build an optimal team for a given query
 */
export function buildTeam(analysis: QueryAnalysis): TeamComposition {
  const { intent, complexity, domain } = analysis
  
  // Select lead persona based on intent
  const leadPersonaId = selectLeadPersona(intent, domain)
  const lead = MODEL_PERSONAS[leadPersonaId] || MODEL_PERSONAS['research-scientist']
  
  // Select supporting personas
  const supporting = selectSupportingPersonas(intent, complexity, lead.id)
  
  // Determine workflow
  const workflow = selectWorkflow(complexity, supporting.length)
  
  return { lead, supporting, workflow }
}

/**
 * Select the lead persona based on query intent
 */
function selectLeadPersona(intent: string, domain: string): string {
  const intentLeads: Record<string, string> = {
    'code': 'senior-engineer',
    'troubleshooting': 'senior-engineer',
    'research': 'research-scientist',
    'analytical': 'research-scientist',
    'factual': 'research-scientist',
    'business': 'strategy-consultant',
    'creative': 'creative-director',
    'procedural': 'senior-engineer',
  }
  
  const domainLeads: Record<string, string> = {
    'technology': 'senior-engineer',
    'business': 'strategy-consultant',
    'science': 'research-scientist',
    'creative': 'creative-director',
  }
  
  return intentLeads[intent] || domainLeads[domain] || 'research-scientist'
}

/**
 * Select supporting personas for the team
 */
function selectSupportingPersonas(
  intent: string,
  complexity: string,
  leadId: string
): ModelPersona[] {
  const supporting: ModelPersona[] = []
  
  // Always add fact-checker for complex queries
  if (complexity === 'complex' || complexity === 'expert') {
    supporting.push(MODEL_PERSONAS['fact-checker'])
  }
  
  // Add critic for analytical/research queries
  if (intent === 'analytical' || intent === 'research') {
    supporting.push(MODEL_PERSONAS['devil-advocate'])
  }
  
  // Add editor for writing/documentation
  if (intent === 'creative' || intent === 'procedural') {
    supporting.push(MODEL_PERSONAS['editor-in-chief'])
  }
  
  // Add technical reviewer for code
  if (intent === 'code' && leadId !== 'code-reviewer') {
    supporting.push(MODEL_PERSONAS['code-reviewer'])
  }
  
  // Add synthesizer for multi-perspective queries
  if (supporting.length > 1) {
    supporting.push(MODEL_PERSONAS['synthesizer'])
  }
  
  // Limit to 3 supporting personas
  return supporting.slice(0, 3)
}

/**
 * Select workflow based on team composition
 */
function selectWorkflow(complexity: string, teamSize: number): TeamWorkflow {
  if (complexity === 'expert' && teamSize >= 2) {
    return 'debate'
  }
  
  if (teamSize >= 3) {
    return 'hierarchical'
  }
  
  if (complexity === 'complex') {
    return 'sequential'
  }
  
  return 'parallel'
}

/**
 * Generate the system prompt for a persona
 */
export function getPersonaSystemPrompt(persona: ModelPersona, context?: string): string {
  let prompt = persona.systemPrompt
  
  if (context) {
    prompt += `\n\nContext for this task: ${context}`
  }
  
  return prompt
}

/**
 * Get team configuration for a workflow
 */
export function getTeamConfig(workflow: TeamWorkflow): TeamConfig {
  const configs: Record<TeamWorkflow, TeamConfig> = {
    'sequential': {
      maxModels: 4,
      requireConsensus: false,
      consensusThreshold: 0.7,
      enableDebate: false,
      debateRounds: 0,
      finalDecider: 'synthesizer',
    },
    'parallel': {
      maxModels: 3,
      requireConsensus: true,
      consensusThreshold: 0.6,
      enableDebate: false,
      debateRounds: 0,
      finalDecider: 'vote',
    },
    'debate': {
      maxModels: 3,
      requireConsensus: false,
      consensusThreshold: 0.8,
      enableDebate: true,
      debateRounds: 2,
      finalDecider: 'synthesizer',
    },
    'ensemble': {
      maxModels: 5,
      requireConsensus: true,
      consensusThreshold: 0.5,
      enableDebate: false,
      debateRounds: 0,
      finalDecider: 'vote',
    },
    'hierarchical': {
      maxModels: 4,
      requireConsensus: false,
      consensusThreshold: 0.7,
      enableDebate: true,
      debateRounds: 1,
      finalDecider: 'lead',
    },
  }
  
  return configs[workflow]
}

/**
 * Generate a debate prompt between two personas
 */
export function generateDebatePrompt(
  topic: string,
  persona1: ModelPersona,
  position1: string,
  persona2: ModelPersona,
  position2: string
): string {
  return `**Debate Topic:** ${topic}

**${persona1.name}'s Position:**
${position1}

**${persona2.name}'s Position:**
${position2}

---

**Instructions for Resolution:**
Analyze both positions carefully. Identify:
1. Points of agreement
2. Points of disagreement
3. Strengths of each position
4. Weaknesses of each position
5. Synthesized best answer incorporating the strongest elements of both

**Synthesized Response:**`
}

/**
 * Get optimal model for a persona
 */
export function getModelForPersona(persona: ModelPersona, availableModels: string[]): string {
  // Find first preferred model that's available
  for (const preferred of persona.preferredModels) {
    if (availableModels.includes(preferred)) {
      return preferred
    }
  }
  
  // Default to first available
  return availableModels[0] || 'gpt-4o'
}

/**
 * Create execution plan for a team
 */
export function createTeamExecutionPlan(
  team: TeamComposition,
  query: string
): { step: number; persona: ModelPersona; task: string; dependsOn: number[] }[] {
  const plan: { step: number; persona: ModelPersona; task: string; dependsOn: number[] }[] = []
  
  switch (team.workflow) {
    case 'sequential':
      // Lead first, then each supporting in order
      plan.push({ step: 1, persona: team.lead, task: 'primary-response', dependsOn: [] })
      team.supporting.forEach((p, i) => {
        plan.push({ step: i + 2, persona: p, task: 'enhance', dependsOn: [i + 1] })
      })
      break
      
    case 'parallel':
      // Everyone in parallel, then synthesize
      plan.push({ step: 1, persona: team.lead, task: 'primary-response', dependsOn: [] })
      team.supporting.forEach((p, i) => {
        plan.push({ step: 1, persona: p, task: 'parallel-response', dependsOn: [] })
      })
      const synthesizer = team.supporting.find(p => p.role === 'synthesizer') || team.lead
      plan.push({ step: 2, persona: synthesizer, task: 'synthesize', dependsOn: [1] })
      break
      
    case 'debate':
      // Lead + critic debate, then synthesize
      plan.push({ step: 1, persona: team.lead, task: 'initial-position', dependsOn: [] })
      const critic = team.supporting.find(p => p.role === 'critic')
      if (critic) {
        plan.push({ step: 2, persona: critic, task: 'critique', dependsOn: [1] })
        plan.push({ step: 3, persona: team.lead, task: 'respond-to-critique', dependsOn: [2] })
        plan.push({ step: 4, persona: MODEL_PERSONAS['synthesizer'], task: 'synthesize-debate', dependsOn: [3] })
      }
      break
      
    case 'hierarchical':
      // Lead delegates to specialists
      plan.push({ step: 1, persona: team.lead, task: 'decompose-and-delegate', dependsOn: [] })
      team.supporting.forEach((p, i) => {
        plan.push({ step: 2, persona: p, task: 'specialist-task', dependsOn: [1] })
      })
      plan.push({ step: 3, persona: team.lead, task: 'integrate-responses', dependsOn: [2] })
      break
      
    default:
      plan.push({ step: 1, persona: team.lead, task: 'primary-response', dependsOn: [] })
  }
  
  return plan
}

