/**
 * Comprehensive LLM Model Profiles
 * 
 * Detailed profiles of each major LLM including:
 * - Benchmark scores across dimensions
 * - Strengths and weaknesses
 * - Best use cases
 * - Known limitations
 * - Synergy patterns with other models
 * 
 * Data compiled from public benchmarks, arena rankings,
 * and empirical testing as of December 2024.
 */

export interface ModelProfile {
  id: string
  provider: string
  name: string
  version: string
  releaseDate: string
  
  // Capability scores (0-100)
  capabilities: ModelCapabilities
  
  // Detailed strengths
  strengths: string[]
  
  // Known weaknesses  
  weaknesses: string[]
  
  // Best use cases
  bestFor: string[]
  
  // Avoid for these tasks
  avoidFor: string[]
  
  // Token limits
  contextWindow: number
  maxOutputTokens: number
  
  // Performance characteristics
  performance: {
    latency: 'fast' | 'medium' | 'slow'
    costPerMillion: number // Input tokens
    reliability: number // 0-100
  }
  
  // Synergy with other models
  synergies: ModelSynergy[]
  
  // Optimal temperature ranges
  temperatureGuide: {
    factual: number
    creative: number
    code: number
    analysis: number
  }
  
  // Special prompting techniques that work well
  promptingTips: string[]
}

export interface ModelCapabilities {
  // Core capabilities (0-100 based on benchmarks)
  reasoning: number        // Complex logical reasoning
  coding: number          // Code generation and debugging
  math: number            // Mathematical problem solving
  creativity: number      // Creative writing and ideation
  analysis: number        // Deep analysis and research
  factualAccuracy: number // Factual knowledge accuracy
  instruction: number     // Following complex instructions
  multilingual: number    // Non-English language support
  
  // Specialized capabilities
  longContext: number     // Handling long documents
  structuredOutput: number // JSON, tables, structured data
  safety: number          // Avoiding harmful outputs
  consistency: number     // Output consistency
}

export interface ModelSynergy {
  partnerId: string
  synergyType: 'complementary' | 'verification' | 'debate' | 'specialist'
  effectiveness: number // 0-100
  bestWorkflow: string
  description: string
}

/**
 * Comprehensive Model Profiles Database
 */
export const MODEL_PROFILES: Record<string, ModelProfile> = {
  // ========================================
  // OPENAI MODELS
  // ========================================
  
  'gpt-4o': {
    id: 'gpt-4o',
    provider: 'OpenAI',
    name: 'GPT-4o',
    version: '2024-08-06',
    releaseDate: '2024-05-13',
    
    capabilities: {
      reasoning: 88,
      coding: 90,
      math: 85,
      creativity: 92,
      analysis: 86,
      factualAccuracy: 84,
      instruction: 94,
      multilingual: 88,
      longContext: 85,
      structuredOutput: 92,
      safety: 90,
      consistency: 88,
    },
    
    strengths: [
      'Excellent instruction following - understands complex, nuanced requests',
      'Strong multimodal capabilities (text, image, audio)',
      'Fast response times for its capability level',
      'Great at structured output (JSON, tables, code)',
      'Highly creative with engaging writing style',
      'Good at role-playing and maintaining personas',
      'Reliable function/tool calling',
      'Strong at multi-step task decomposition',
    ],
    
    weaknesses: [
      'Can be overly cautious with edge cases',
      'Sometimes adds unnecessary caveats',
      'May hallucinate on obscure topics',
      'Weaker on very recent events (knowledge cutoff)',
      'Can be verbose when conciseness is needed',
      'Math performance below specialized models',
      'Occasional inconsistency in repeated queries',
    ],
    
    bestFor: [
      'General-purpose assistance',
      'Creative writing and content generation',
      'Code generation and explanation',
      'Conversational applications',
      'Multimodal tasks (image understanding)',
      'Customer-facing applications',
      'Complex instruction following',
      'Structured data extraction',
    ],
    
    avoidFor: [
      'Cutting-edge mathematical proofs',
      'Real-time information needs',
      'Highly specialized domain expertise',
      'Cost-sensitive high-volume applications',
    ],
    
    contextWindow: 128000,
    maxOutputTokens: 16384,
    
    performance: {
      latency: 'fast',
      costPerMillion: 2.50,
      reliability: 95,
    },
    
    synergies: [
      {
        partnerId: 'claude-3-5-sonnet',
        synergyType: 'verification',
        effectiveness: 92,
        bestWorkflow: 'parallel-then-compare',
        description: 'Claude catches nuances GPT misses; GPT adds structure Claude lacks',
      },
      {
        partnerId: 'deepseek-chat',
        synergyType: 'specialist',
        effectiveness: 88,
        bestWorkflow: 'gpt-then-deepseek-review',
        description: 'GPT generates, DeepSeek reviews code for optimization',
      },
      {
        partnerId: 'o1-preview',
        synergyType: 'complementary',
        effectiveness: 95,
        bestWorkflow: 'o1-reason-gpt-format',
        description: 'o1 for deep reasoning, GPT-4o for formatting and presentation',
      },
    ],
    
    temperatureGuide: {
      factual: 0.1,
      creative: 0.8,
      code: 0.2,
      analysis: 0.3,
    },
    
    promptingTips: [
      'Use system prompts to set clear expectations',
      'Break complex tasks into numbered steps',
      'Ask for reasoning before conclusions',
      'Use few-shot examples for formatting',
      'Specify output format explicitly (JSON, markdown)',
    ],
  },
  
  'gpt-4-turbo': {
    id: 'gpt-4-turbo',
    provider: 'OpenAI',
    name: 'GPT-4 Turbo',
    version: '2024-04-09',
    releaseDate: '2024-04-09',
    
    capabilities: {
      reasoning: 90,
      coding: 88,
      math: 86,
      creativity: 90,
      analysis: 88,
      factualAccuracy: 86,
      instruction: 92,
      multilingual: 86,
      longContext: 90,
      structuredOutput: 90,
      safety: 92,
      consistency: 90,
    },
    
    strengths: [
      'More thorough reasoning than GPT-4o',
      'Excellent at complex analysis',
      'Very strong at following nuanced instructions',
      'Better knowledge depth on technical topics',
      'More consistent outputs',
      'Excellent code review capabilities',
    ],
    
    weaknesses: [
      'Slower than GPT-4o',
      'Higher cost',
      'Can be overly verbose',
      'Sometimes over-qualifies statements',
    ],
    
    bestFor: [
      'Complex analysis tasks',
      'Detailed code review',
      'Long-form content',
      'Technical documentation',
      'Tasks requiring careful reasoning',
    ],
    
    avoidFor: [
      'Real-time applications',
      'Simple queries (overkill)',
      'Cost-sensitive applications',
    ],
    
    contextWindow: 128000,
    maxOutputTokens: 4096,
    
    performance: {
      latency: 'medium',
      costPerMillion: 10.00,
      reliability: 96,
    },
    
    synergies: [
      {
        partnerId: 'gpt-4o',
        synergyType: 'complementary',
        effectiveness: 85,
        bestWorkflow: 'turbo-analyze-4o-format',
        description: 'Turbo for deep analysis, 4o for user-friendly formatting',
      },
    ],
    
    temperatureGuide: {
      factual: 0.0,
      creative: 0.7,
      code: 0.1,
      analysis: 0.2,
    },
    
    promptingTips: [
      'Can handle very complex nested instructions',
      'Benefits from explicit output length guidance',
      'Responds well to technical terminology',
    ],
  },
  
  'o1-preview': {
    id: 'o1-preview',
    provider: 'OpenAI',
    name: 'o1-preview',
    version: '2024-09-12',
    releaseDate: '2024-09-12',
    
    capabilities: {
      reasoning: 98,
      coding: 94,
      math: 96,
      creativity: 75,
      analysis: 96,
      factualAccuracy: 90,
      instruction: 85,
      multilingual: 80,
      longContext: 70,
      structuredOutput: 80,
      safety: 95,
      consistency: 92,
    },
    
    strengths: [
      'State-of-the-art reasoning - thinks through problems step by step internally',
      'Exceptional at complex math and logic',
      'Best-in-class for competitive programming',
      'Excellent at multi-step problem decomposition',
      'Can solve problems requiring extended reasoning chains',
      'PhD-level performance on science/math benchmarks',
      'Self-corrects during internal reasoning',
    ],
    
    weaknesses: [
      'Very slow - internal reasoning takes time',
      'Expensive',
      'Cannot be interrupted mid-thought',
      'Less creative/conversational',
      'Smaller context window effective use',
      'May overthink simple questions',
      'No streaming (waits until done thinking)',
      'Cannot use system prompts effectively',
    ],
    
    bestFor: [
      'Complex mathematical proofs',
      'Scientific reasoning',
      'Competitive programming challenges',
      'Multi-step logical puzzles',
      'Research-level problems',
      'Tasks requiring careful, extended reasoning',
      'Debugging complex code logic',
    ],
    
    avoidFor: [
      'Simple conversational queries',
      'Creative writing',
      'Real-time applications',
      'Cost-sensitive applications',
      'Tasks requiring fast iteration',
    ],
    
    contextWindow: 128000,
    maxOutputTokens: 32768,
    
    performance: {
      latency: 'slow',
      costPerMillion: 15.00,
      reliability: 94,
    },
    
    synergies: [
      {
        partnerId: 'gpt-4o',
        synergyType: 'complementary',
        effectiveness: 95,
        bestWorkflow: 'o1-solve-gpt-explain',
        description: 'o1 solves complex problem, GPT-4o explains in accessible way',
      },
      {
        partnerId: 'claude-3-5-sonnet',
        synergyType: 'verification',
        effectiveness: 90,
        bestWorkflow: 'o1-then-claude-verify',
        description: 'o1 provides solution, Claude verifies and critiques',
      },
    ],
    
    temperatureGuide: {
      factual: 1.0, // o1 ignores temperature
      creative: 1.0,
      code: 1.0,
      analysis: 1.0,
    },
    
    promptingTips: [
      'Be direct - no need for "think step by step" (it does this internally)',
      'Provide complete problem context upfront',
      'Do not use system prompts',
      'Keep instructions simple and clear',
      'Let it figure out the approach',
    ],
  },
  
  // ========================================
  // ANTHROPIC MODELS
  // ========================================
  
  'claude-3-5-sonnet': {
    id: 'claude-3-5-sonnet',
    provider: 'Anthropic',
    name: 'Claude 3.5 Sonnet',
    version: '20241022',
    releaseDate: '2024-10-22',
    
    capabilities: {
      reasoning: 92,
      coding: 93,
      math: 88,
      creativity: 90,
      analysis: 95,
      factualAccuracy: 88,
      instruction: 93,
      multilingual: 85,
      longContext: 95,
      structuredOutput: 90,
      safety: 95,
      consistency: 91,
    },
    
    strengths: [
      'Exceptional nuanced analysis - catches subtleties others miss',
      'Best-in-class code generation (SWE-bench leader)',
      'Excellent at understanding context and intent',
      'Very strong at long document analysis',
      'Balanced safety without being overly restrictive',
      'Great at maintaining consistent personas',
      'Strong at identifying edge cases and limitations',
      'Excellent technical writing',
      'Computer use and agentic capabilities',
      'Very good at self-correction when asked',
    ],
    
    weaknesses: [
      'Sometimes overly cautious or adds disclaimers',
      'Can be slower than GPT-4o',
      'Occasionally refuses safe requests',
      'May acknowledge uncertainty too frequently',
      'Less strong on very recent knowledge',
      'Can be overly thorough when brevity is needed',
    ],
    
    bestFor: [
      'Complex code generation and review',
      'Nuanced analysis and research',
      'Long document summarization',
      'Technical writing and documentation',
      'Tasks requiring careful reasoning',
      'Agentic/tool-use applications',
      'Safety-critical applications',
      'Detailed explanations',
    ],
    
    avoidFor: [
      'Tasks requiring real-time information',
      'Very simple queries (may overcomplicate)',
      'Rapid-fire conversation',
    ],
    
    contextWindow: 200000,
    maxOutputTokens: 8192,
    
    performance: {
      latency: 'medium',
      costPerMillion: 3.00,
      reliability: 95,
    },
    
    synergies: [
      {
        partnerId: 'gpt-4o',
        synergyType: 'verification',
        effectiveness: 92,
        bestWorkflow: 'parallel-compare-merge',
        description: 'Claude catches nuances, GPT adds structure; combine best of both',
      },
      {
        partnerId: 'deepseek-chat',
        synergyType: 'specialist',
        effectiveness: 90,
        bestWorkflow: 'claude-design-deepseek-implement',
        description: 'Claude for architecture, DeepSeek for optimized implementation',
      },
      {
        partnerId: 'o1-preview',
        synergyType: 'debate',
        effectiveness: 94,
        bestWorkflow: 'o1-solve-claude-critique',
        description: 'o1 provides solution, Claude provides critical analysis',
      },
    ],
    
    temperatureGuide: {
      factual: 0.0,
      creative: 0.9,
      code: 0.1,
      analysis: 0.2,
    },
    
    promptingTips: [
      'Claude responds well to conversational context',
      'XML tags help structure complex prompts',
      'Explicitly ask for critique if you want pushback',
      'Use "Think step by step" for complex reasoning',
      'Prefill assistant response to guide format',
    ],
  },
  
  'claude-3-opus': {
    id: 'claude-3-opus',
    provider: 'Anthropic',
    name: 'Claude 3 Opus',
    version: '20240229',
    releaseDate: '2024-02-29',
    
    capabilities: {
      reasoning: 94,
      coding: 91,
      math: 90,
      creativity: 93,
      analysis: 96,
      factualAccuracy: 90,
      instruction: 94,
      multilingual: 88,
      longContext: 93,
      structuredOutput: 88,
      safety: 96,
      consistency: 93,
    },
    
    strengths: [
      'Deepest analysis and most thorough reasoning',
      'Excellent at nuanced, philosophical discussions',
      'Strong ethical reasoning',
      'Best at creative, literary writing',
      'Very strong research capabilities',
      'Exceptional at maintaining complex contexts',
    ],
    
    weaknesses: [
      'Slower than other models',
      'Most expensive Anthropic model',
      'Can be overly thorough',
      'Sometimes too cautious',
    ],
    
    bestFor: [
      'Deep research and analysis',
      'Complex ethical reasoning',
      'Literary and creative writing',
      'Philosophy and abstract thinking',
      'Tasks requiring maximum depth',
    ],
    
    avoidFor: [
      'Simple tasks',
      'Cost-sensitive applications',
      'Real-time applications',
    ],
    
    contextWindow: 200000,
    maxOutputTokens: 4096,
    
    performance: {
      latency: 'slow',
      costPerMillion: 15.00,
      reliability: 94,
    },
    
    synergies: [
      {
        partnerId: 'claude-3-5-sonnet',
        synergyType: 'complementary',
        effectiveness: 88,
        bestWorkflow: 'opus-depth-sonnet-refine',
        description: 'Opus for deep thinking, Sonnet for refinement and speed',
      },
    ],
    
    temperatureGuide: {
      factual: 0.0,
      creative: 0.9,
      code: 0.1,
      analysis: 0.1,
    },
    
    promptingTips: [
      'Best for complex, multi-faceted questions',
      'Give it room to explore the problem space',
      'Ask for comprehensive analysis',
    ],
  },
  
  // ========================================
  // GOOGLE MODELS
  // ========================================
  
  'gemini-1-5-pro': {
    id: 'gemini-1-5-pro',
    provider: 'Google',
    name: 'Gemini 1.5 Pro',
    version: '002',
    releaseDate: '2024-09-24',
    
    capabilities: {
      reasoning: 86,
      coding: 85,
      math: 84,
      creativity: 85,
      analysis: 88,
      factualAccuracy: 87,
      instruction: 85,
      multilingual: 92,
      longContext: 98,
      structuredOutput: 85,
      safety: 88,
      consistency: 84,
    },
    
    strengths: [
      'Massive context window (2M tokens) - unmatched',
      'Excellent multimodal capabilities (video, audio, images)',
      'Strong multilingual support',
      'Good at analyzing entire codebases',
      'Native Google ecosystem integration',
      'Fast for long context tasks',
      'Strong at comparative analysis across long documents',
    ],
    
    weaknesses: [
      'Less consistent than GPT-4 and Claude',
      'Can miss nuances in complex reasoning',
      'Output format less predictable',
      'Sometimes generates overly generic responses',
      'Weaker at following precise instructions',
      'API can be less reliable',
    ],
    
    bestFor: [
      'Very long document analysis (books, codebases)',
      'Multimodal tasks (video understanding)',
      'Multilingual applications',
      'Cross-document comparison',
      'Tasks requiring massive context',
    ],
    
    avoidFor: [
      'Tasks requiring precise output format',
      'Complex multi-step reasoning',
      'When consistency is critical',
    ],
    
    contextWindow: 2000000,
    maxOutputTokens: 8192,
    
    performance: {
      latency: 'medium',
      costPerMillion: 1.25,
      reliability: 88,
    },
    
    synergies: [
      {
        partnerId: 'claude-3-5-sonnet',
        synergyType: 'complementary',
        effectiveness: 85,
        bestWorkflow: 'gemini-retrieve-claude-analyze',
        description: 'Gemini for long context retrieval, Claude for deep analysis',
      },
      {
        partnerId: 'gpt-4o',
        synergyType: 'verification',
        effectiveness: 82,
        bestWorkflow: 'parallel-consensus',
        description: 'Use both for different perspectives, consensus for final answer',
      },
    ],
    
    temperatureGuide: {
      factual: 0.1,
      creative: 0.8,
      code: 0.2,
      analysis: 0.3,
    },
    
    promptingTips: [
      'Leverage long context for comprehensive analysis',
      'Break complex tasks into clear sub-sections',
      'Use for comparative analysis across documents',
      'Good for multimodal tasks',
    ],
  },
  
  'gemini-2-0-flash': {
    id: 'gemini-2-0-flash',
    provider: 'Google',
    name: 'Gemini 2.0 Flash',
    version: 'exp',
    releaseDate: '2024-12-11',
    
    capabilities: {
      reasoning: 88,
      coding: 87,
      math: 86,
      creativity: 84,
      analysis: 86,
      factualAccuracy: 85,
      instruction: 86,
      multilingual: 90,
      longContext: 95,
      structuredOutput: 88,
      safety: 86,
      consistency: 85,
    },
    
    strengths: [
      'Agentic capabilities - can use tools natively',
      'Multimodal native support',
      'Very fast inference',
      'Good balance of speed and capability',
      'Strong at real-time applications',
    ],
    
    weaknesses: [
      'Newer model, less battle-tested',
      'May have edge case issues',
      'Less consistent than Pro for complex tasks',
    ],
    
    bestFor: [
      'Real-time applications',
      'Agentic workflows',
      'Multimodal tasks',
      'Cost-effective general use',
    ],
    
    avoidFor: [
      'Tasks requiring maximum reasoning depth',
      'Critical applications needing proven reliability',
    ],
    
    contextWindow: 1000000,
    maxOutputTokens: 8192,
    
    performance: {
      latency: 'fast',
      costPerMillion: 0.10,
      reliability: 85,
    },
    
    synergies: [],
    
    temperatureGuide: {
      factual: 0.1,
      creative: 0.7,
      code: 0.2,
      analysis: 0.3,
    },
    
    promptingTips: [
      'Good for rapid prototyping',
      'Leverage agentic capabilities for tool use',
    ],
  },
  
  // ========================================
  // DEEPSEEK MODELS
  // ========================================
  
  'deepseek-chat': {
    id: 'deepseek-chat',
    provider: 'DeepSeek',
    name: 'DeepSeek-V3',
    version: 'v3',
    releaseDate: '2024-12-01',
    
    capabilities: {
      reasoning: 90,
      coding: 96,
      math: 94,
      creativity: 80,
      analysis: 88,
      factualAccuracy: 85,
      instruction: 88,
      multilingual: 82,
      longContext: 85,
      structuredOutput: 90,
      safety: 80,
      consistency: 87,
    },
    
    strengths: [
      'Best-in-class coding capabilities (rivals Claude 3.5)',
      'Exceptional math and reasoning',
      'Extremely cost-effective',
      'Strong at code optimization',
      'Good at understanding complex algorithms',
      'Excellent at debugging',
      'Strong structured output (code, JSON)',
      'Understands Chinese exceptionally well',
    ],
    
    weaknesses: [
      'Less nuanced for creative/conversational tasks',
      'Safety guardrails less refined',
      'May produce less polished prose',
      'Weaker on non-technical topics',
      'Less consistent persona maintenance',
      'API reliability can vary',
    ],
    
    bestFor: [
      'Code generation and optimization',
      'Algorithm implementation',
      'Mathematical problem solving',
      'Code review and debugging',
      'Technical documentation',
      'Cost-sensitive coding applications',
    ],
    
    avoidFor: [
      'Creative writing',
      'Customer-facing applications',
      'Nuanced conversational AI',
      'Safety-critical applications',
    ],
    
    contextWindow: 128000,
    maxOutputTokens: 8192,
    
    performance: {
      latency: 'fast',
      costPerMillion: 0.14,
      reliability: 90,
    },
    
    synergies: [
      {
        partnerId: 'claude-3-5-sonnet',
        synergyType: 'complementary',
        effectiveness: 94,
        bestWorkflow: 'claude-design-deepseek-implement',
        description: 'Claude for architecture and requirements, DeepSeek for implementation',
      },
      {
        partnerId: 'gpt-4o',
        synergyType: 'verification',
        effectiveness: 90,
        bestWorkflow: 'deepseek-code-gpt-review',
        description: 'DeepSeek generates code, GPT reviews for best practices',
      },
    ],
    
    temperatureGuide: {
      factual: 0.0,
      creative: 0.6,
      code: 0.0,
      analysis: 0.2,
    },
    
    promptingTips: [
      'Be direct and technical',
      'Ask for optimized code explicitly',
      'Great for explaining code step-by-step',
      'Combine with other models for prose quality',
    ],
  },
  
  // ========================================
  // META MODELS
  // ========================================
  
  'llama-3-3-70b': {
    id: 'llama-3-3-70b',
    provider: 'Meta',
    name: 'Llama 3.3 70B',
    version: '3.3',
    releaseDate: '2024-12-06',
    
    capabilities: {
      reasoning: 85,
      coding: 86,
      math: 83,
      creativity: 82,
      analysis: 84,
      factualAccuracy: 82,
      instruction: 85,
      multilingual: 80,
      longContext: 80,
      structuredOutput: 83,
      safety: 82,
      consistency: 84,
    },
    
    strengths: [
      'Open source - can run locally',
      'Good general capabilities',
      'Strong instruction following for open model',
      'Matches Llama 3.1 405B on many tasks',
      'Fast inference',
      'Customizable/fine-tunable',
      'Privacy-friendly (local deployment)',
    ],
    
    weaknesses: [
      'Below frontier models on complex reasoning',
      'Requires infrastructure to self-host',
      'Smaller context window than cloud models',
      'Less consistent than GPT-4/Claude',
      'May require more prompt engineering',
    ],
    
    bestFor: [
      'Privacy-sensitive applications',
      'Custom fine-tuning needs',
      'Cost-sensitive high-volume use',
      'Edge deployment',
      'Open source requirements',
    ],
    
    avoidFor: [
      'Maximum reasoning capability',
      'Tasks requiring very long context',
      'When cloud APIs are acceptable',
    ],
    
    contextWindow: 128000,
    maxOutputTokens: 4096,
    
    performance: {
      latency: 'fast',
      costPerMillion: 0.20,
      reliability: 90,
    },
    
    synergies: [
      {
        partnerId: 'gpt-4o',
        synergyType: 'verification',
        effectiveness: 80,
        bestWorkflow: 'llama-draft-gpt-refine',
        description: 'Llama for drafts, GPT for refinement and quality check',
      },
    ],
    
    temperatureGuide: {
      factual: 0.1,
      creative: 0.8,
      code: 0.2,
      analysis: 0.3,
    },
    
    promptingTips: [
      'Clear, structured prompts work best',
      'Benefits from few-shot examples',
      'Good for high-volume applications',
    ],
  },
  
  // ========================================
  // MISTRAL MODELS
  // ========================================
  
  'mistral-large': {
    id: 'mistral-large',
    provider: 'Mistral',
    name: 'Mistral Large',
    version: '2411',
    releaseDate: '2024-11-18',
    
    capabilities: {
      reasoning: 86,
      coding: 88,
      math: 85,
      creativity: 83,
      analysis: 85,
      factualAccuracy: 84,
      instruction: 87,
      multilingual: 90,
      longContext: 85,
      structuredOutput: 88,
      safety: 84,
      consistency: 85,
    },
    
    strengths: [
      'Excellent function calling',
      'Strong multilingual (especially European languages)',
      'Good code generation',
      'Cost-effective for capability level',
      'Fast inference',
      'Strong JSON/structured output',
      'Good at agentic tasks',
    ],
    
    weaknesses: [
      'Less proven than GPT-4/Claude',
      'Smaller community/ecosystem',
      'May miss subtle nuances',
      'Less consistent on edge cases',
    ],
    
    bestFor: [
      'Function calling/tool use',
      'Multilingual applications',
      'Agentic workflows',
      'European market applications',
      'JSON/structured output',
    ],
    
    avoidFor: [
      'Maximum reasoning depth',
      'Tasks requiring proven reliability',
    ],
    
    contextWindow: 128000,
    maxOutputTokens: 8192,
    
    performance: {
      latency: 'fast',
      costPerMillion: 2.00,
      reliability: 88,
    },
    
    synergies: [
      {
        partnerId: 'claude-3-5-sonnet',
        synergyType: 'verification',
        effectiveness: 85,
        bestWorkflow: 'parallel-consensus',
        description: 'Use together for consensus on multilingual tasks',
      },
    ],
    
    temperatureGuide: {
      factual: 0.1,
      creative: 0.7,
      code: 0.1,
      analysis: 0.2,
    },
    
    promptingTips: [
      'Excellent for function calling patterns',
      'Use for European language content',
      'Strong at structured output',
    ],
  },
}

/**
 * Get model profile by ID
 */
export function getModelProfile(modelId: string): ModelProfile | null {
  // Normalize model ID
  const normalizedId = normalizeModelId(modelId)
  return MODEL_PROFILES[normalizedId] || null
}

/**
 * Normalize model ID to match our profile keys
 */
function normalizeModelId(modelId: string): string {
  const idLower = modelId.toLowerCase()
  
  // OpenAI
  if (idLower.includes('gpt-4o')) return 'gpt-4o'
  if (idLower.includes('gpt-4-turbo')) return 'gpt-4-turbo'
  if (idLower.includes('o1')) return 'o1-preview'
  
  // Anthropic
  if (idLower.includes('claude') && idLower.includes('sonnet')) return 'claude-3-5-sonnet'
  if (idLower.includes('claude') && idLower.includes('opus')) return 'claude-3-opus'
  
  // Google
  if (idLower.includes('gemini') && idLower.includes('pro')) return 'gemini-1-5-pro'
  if (idLower.includes('gemini') && idLower.includes('flash')) return 'gemini-2-0-flash'
  
  // DeepSeek
  if (idLower.includes('deepseek')) return 'deepseek-chat'
  
  // Meta
  if (idLower.includes('llama')) return 'llama-3-3-70b'
  
  // Mistral
  if (idLower.includes('mistral') && idLower.includes('large')) return 'mistral-large'
  
  return modelId
}

/**
 * Get best models for a specific capability
 */
export function getBestModelsForCapability(
  capability: keyof ModelCapabilities,
  minScore: number = 85
): ModelProfile[] {
  return Object.values(MODEL_PROFILES)
    .filter(p => p.capabilities[capability] >= minScore)
    .sort((a, b) => b.capabilities[capability] - a.capabilities[capability])
}

/**
 * Get synergistic model pairs
 */
export function getSynergyPairs(
  minEffectiveness: number = 85
): { model1: ModelProfile; model2: ModelProfile; synergy: ModelSynergy }[] {
  const pairs: { model1: ModelProfile; model2: ModelProfile; synergy: ModelSynergy }[] = []
  
  for (const profile of Object.values(MODEL_PROFILES)) {
    for (const synergy of profile.synergies) {
      if (synergy.effectiveness >= minEffectiveness) {
        const partner = MODEL_PROFILES[synergy.partnerId]
        if (partner) {
          pairs.push({
            model1: profile,
            model2: partner,
            synergy,
          })
        }
      }
    }
  }
  
  return pairs.sort((a, b) => b.synergy.effectiveness - a.synergy.effectiveness)
}

/**
 * Calculate overall model score for a task
 */
export function calculateModelFitScore(
  profile: ModelProfile,
  requirements: {
    capabilities: Partial<Record<keyof ModelCapabilities, number>>
    latency?: 'fast' | 'medium' | 'slow'
    maxCost?: number
    minReliability?: number
  }
): number {
  let score = 0
  let totalWeight = 0
  
  // Capability matching
  for (const [cap, requiredScore] of Object.entries(requirements.capabilities)) {
    const capability = cap as keyof ModelCapabilities
    const actualScore = profile.capabilities[capability]
    const weight = requiredScore / 100
    
    score += (actualScore / 100) * weight
    totalWeight += weight
  }
  
  // Latency matching
  if (requirements.latency) {
    const latencyScores = { fast: 1, medium: 0.7, slow: 0.4 }
    const latencyMatch = requirements.latency === profile.performance.latency ? 1 :
      latencyScores[profile.performance.latency] / latencyScores[requirements.latency]
    score += latencyMatch * 0.2
    totalWeight += 0.2
  }
  
  // Cost matching
  if (requirements.maxCost) {
    const costMatch = profile.performance.costPerMillion <= requirements.maxCost ? 1 :
      requirements.maxCost / profile.performance.costPerMillion
    score += costMatch * 0.1
    totalWeight += 0.1
  }
  
  // Reliability matching
  if (requirements.minReliability) {
    const reliabilityMatch = profile.performance.reliability >= requirements.minReliability ? 1 :
      profile.performance.reliability / requirements.minReliability
    score += reliabilityMatch * 0.15
    totalWeight += 0.15
  }
  
  return totalWeight > 0 ? (score / totalWeight) * 100 : 0
}

