/**
 * Advanced Reasoning System v2
 * 
 * State-of-the-art reasoning techniques based on latest research:
 * 
 * 1. Chain-of-Thought (CoT) - Step-by-step explicit reasoning
 * 2. Tree-of-Thought (ToT) - Explore multiple reasoning paths
 * 3. Self-Consistency - Sample multiple solutions, vote
 * 4. ReAct - Interleave reasoning with tool actions
 * 5. Reflexion - Self-critique and iterative improvement
 * 6. Program-of-Thought (PoT) - Generate executable code
 * 7. Chain-of-Verification (CoVe) - Verify each step
 * 8. Step-Back Prompting - Abstract to principles first
 * 9. Decomposed Prompting (DecomP) - Break into sub-problems
 * 10. Analogical Reasoning - Learn from similar examples
 * 11. Contrastive CoT - Compare correct vs incorrect reasoning
 * 12. Self-Refine - Iterative self-improvement loop
 */

import type { QueryAnalysis } from './types'
import { getModelProfile, type ModelProfile } from './model-profiles'

export interface ReasoningStrategy {
  id: string
  name: string
  description: string
  
  // When to use this strategy
  triggers: {
    intents: string[]
    complexityLevels: string[]
    domains: string[]
  }
  
  // Implementation details
  promptTemplate: string
  requiresMultipleSamples: boolean
  sampleCount: number
  temperature: number
  
  // Post-processing
  aggregationMethod: 'best-of' | 'vote' | 'synthesize' | 'verify'
  
  // Estimated improvements
  accuracyBoost: number
  timeMultiplier: number
  
  // Compatible models
  bestModels: string[]
}

// ====================================
// REASONING STRATEGY DEFINITIONS
// ====================================

export const REASONING_STRATEGIES: Record<string, ReasoningStrategy> = {
  // 1. Zero-shot Chain-of-Thought
  'cot-zero-shot': {
    id: 'cot-zero-shot',
    name: 'Zero-shot Chain-of-Thought',
    description: 'Simple "think step by step" prompting',
    triggers: {
      intents: ['analytical', 'procedural', 'factual'],
      complexityLevels: ['moderate', 'complex'],
      domains: ['general', 'technology', 'science'],
    },
    promptTemplate: `{query}

Let's think through this step by step:

Step 1:`,
    requiresMultipleSamples: false,
    sampleCount: 1,
    temperature: 0.3,
    aggregationMethod: 'best-of',
    accuracyBoost: 15,
    timeMultiplier: 1.2,
    bestModels: ['gpt-4o', 'claude-3-5-sonnet', 'deepseek-chat'],
  },
  
  // 2. Few-shot Chain-of-Thought
  'cot-few-shot': {
    id: 'cot-few-shot',
    name: 'Few-shot Chain-of-Thought',
    description: 'Provide examples of step-by-step reasoning',
    triggers: {
      intents: ['analytical', 'code', 'troubleshooting'],
      complexityLevels: ['complex', 'expert'],
      domains: ['technology', 'science', 'math'],
    },
    promptTemplate: `Here's an example of careful step-by-step reasoning:

Example Problem: [Similar problem]
Step 1: [First step]
Step 2: [Second step]
Step 3: [Third step]
Answer: [Solution]

Now let's apply the same careful reasoning:

Problem: {query}
Step 1:`,
    requiresMultipleSamples: false,
    sampleCount: 1,
    temperature: 0.2,
    aggregationMethod: 'best-of',
    accuracyBoost: 20,
    timeMultiplier: 1.3,
    bestModels: ['gpt-4o', 'claude-3-5-sonnet', 'o1-preview'],
  },
  
  // 3. Tree-of-Thought
  'tree-of-thought': {
    id: 'tree-of-thought',
    name: 'Tree-of-Thought',
    description: 'Explore multiple reasoning paths in parallel',
    triggers: {
      intents: ['analytical', 'research', 'comparative'],
      complexityLevels: ['complex', 'expert'],
      domains: ['general', 'business', 'science'],
    },
    promptTemplate: `{query}

I'll explore multiple reasoning approaches and evaluate each:

**Approach 1: Direct Analysis**
- Initial thought: [Consider the straightforward interpretation]
- Evaluation: [Rate this approach]
- Conclusion: [Finding from this path]

**Approach 2: Alternative Perspective**
- Initial thought: [Consider a different angle]
- Evaluation: [Rate this approach]
- Conclusion: [Finding from this path]

**Approach 3: Edge Cases**
- Initial thought: [Consider special cases or exceptions]
- Evaluation: [Rate this approach]
- Conclusion: [Finding from this path]

**Synthesis:**
After evaluating all approaches, the best reasoning path is:
[Select and explain the winning approach]

**Final Answer:**`,
    requiresMultipleSamples: true,
    sampleCount: 3,
    temperature: 0.7,
    aggregationMethod: 'synthesize',
    accuracyBoost: 25,
    timeMultiplier: 3.0,
    bestModels: ['claude-3-5-sonnet', 'gpt-4o', 'o1-preview'],
  },
  
  // 4. Self-Consistency
  'self-consistency': {
    id: 'self-consistency',
    name: 'Self-Consistency',
    description: 'Generate multiple solutions and vote on the most consistent',
    triggers: {
      intents: ['factual', 'analytical', 'code'],
      complexityLevels: ['complex', 'expert'],
      domains: ['science', 'math', 'technology'],
    },
    promptTemplate: `{query}

Solve this carefully, showing your reasoning:`,
    requiresMultipleSamples: true,
    sampleCount: 5,
    temperature: 0.8,
    aggregationMethod: 'vote',
    accuracyBoost: 30,
    timeMultiplier: 5.0,
    bestModels: ['gpt-4o', 'claude-3-5-sonnet', 'o1-preview'],
  },
  
  // 5. ReAct (Reason + Act)
  'react': {
    id: 'react',
    name: 'ReAct',
    description: 'Interleave reasoning with tool/action steps',
    triggers: {
      intents: ['code', 'troubleshooting', 'research'],
      complexityLevels: ['moderate', 'complex', 'expert'],
      domains: ['technology'],
    },
    promptTemplate: `{query}

I'll solve this using a Thought-Action-Observation loop:

**Thought 1:** What is the core problem I need to address?
[Analyze the problem]

**Action 1:** [What I need to do or look up]
[Execute action]

**Observation 1:** [What I learned from the action]

**Thought 2:** Based on this observation, what's the next step?
[Continue reasoning]

**Action 2:** [Next action]
[Execute action]

**Observation 2:** [What I learned]

**Thought 3:** Do I have enough information to solve this?
[Evaluate progress]

**Final Answer:**`,
    requiresMultipleSamples: false,
    sampleCount: 1,
    temperature: 0.3,
    aggregationMethod: 'best-of',
    accuracyBoost: 20,
    timeMultiplier: 1.5,
    bestModels: ['gpt-4o', 'claude-3-5-sonnet', 'gemini-1-5-pro'],
  },
  
  // 6. Reflexion
  'reflexion': {
    id: 'reflexion',
    name: 'Reflexion',
    description: 'Generate, critique, and refine answers iteratively',
    triggers: {
      intents: ['code', 'analytical', 'creative'],
      complexityLevels: ['complex', 'expert'],
      domains: ['technology', 'business'],
    },
    promptTemplate: `{query}

**Initial Attempt:**
[Provide comprehensive answer]

**Self-Critique:**
Let me critically evaluate my response:
- What might be wrong or incomplete?
- What assumptions did I make?
- What edge cases did I miss?
- How could this be improved?

**Critique Findings:**
1. [Issue 1]
2. [Issue 2]
3. [Issue 3]

**Refined Answer:**
Based on my critique, here's an improved response:
[Improved answer addressing the critique]`,
    requiresMultipleSamples: false,
    sampleCount: 1,
    temperature: 0.4,
    aggregationMethod: 'best-of',
    accuracyBoost: 25,
    timeMultiplier: 2.0,
    bestModels: ['claude-3-5-sonnet', 'gpt-4o'],
  },
  
  // 7. Program-of-Thought
  'program-of-thought': {
    id: 'program-of-thought',
    name: 'Program-of-Thought',
    description: 'Generate executable code as part of reasoning',
    triggers: {
      intents: ['code', 'analytical'],
      complexityLevels: ['moderate', 'complex', 'expert'],
      domains: ['technology', 'math', 'science'],
    },
    promptTemplate: `{query}

I'll solve this by breaking it down into code that I can reason about:

**Problem Analysis:**
[Understand what we need to compute]

**Algorithm Design:**
\`\`\`python
# Step 1: [Description]
[code]

# Step 2: [Description]
[code]

# Step 3: [Description]
[code]

# Result
[final computation]
\`\`\`

**Execution Trace:**
[Walk through the code step by step]

**Final Answer:**`,
    requiresMultipleSamples: false,
    sampleCount: 1,
    temperature: 0.1,
    aggregationMethod: 'best-of',
    accuracyBoost: 35,
    timeMultiplier: 1.4,
    bestModels: ['deepseek-chat', 'claude-3-5-sonnet', 'gpt-4o'],
  },
  
  // 8. Chain-of-Verification
  'chain-of-verification': {
    id: 'chain-of-verification',
    name: 'Chain-of-Verification',
    description: 'Verify each reasoning step before proceeding',
    triggers: {
      intents: ['factual', 'analytical', 'research'],
      complexityLevels: ['complex', 'expert'],
      domains: ['science', 'medical', 'legal', 'finance'],
    },
    promptTemplate: `{query}

I'll answer carefully, verifying each step:

**Step 1:** [First reasoning step]
**Verification 1:** Is this step correct? [Check assumptions and logic]
**Status:** ✓ Verified / ✗ Needs correction

**Step 2:** [Second reasoning step]
**Verification 2:** Is this step correct? [Check]
**Status:** ✓ Verified / ✗ Needs correction

**Step 3:** [Third reasoning step]
**Verification 3:** Is this step correct? [Check]
**Status:** ✓ Verified / ✗ Needs correction

**Corrections Applied:**
[List any corrections made]

**Verified Conclusion:**`,
    requiresMultipleSamples: false,
    sampleCount: 1,
    temperature: 0.2,
    aggregationMethod: 'verify',
    accuracyBoost: 30,
    timeMultiplier: 1.8,
    bestModels: ['claude-3-5-sonnet', 'o1-preview', 'gpt-4o'],
  },
  
  // 9. Step-Back Prompting
  'step-back': {
    id: 'step-back',
    name: 'Step-Back Prompting',
    description: 'Abstract to high-level principles before solving',
    triggers: {
      intents: ['analytical', 'research', 'factual'],
      complexityLevels: ['complex', 'expert'],
      domains: ['science', 'philosophy', 'business'],
    },
    promptTemplate: `{query}

Before answering directly, let me step back to consider the fundamental principles:

**High-Level Question:** What are the underlying principles or concepts relevant here?

**Key Principles:**
1. [Principle 1]
2. [Principle 2]
3. [Principle 3]

**How These Apply:**
[Connect principles to the specific question]

**Grounded Answer:**
Now, applying these principles to the original question:`,
    requiresMultipleSamples: false,
    sampleCount: 1,
    temperature: 0.3,
    aggregationMethod: 'best-of',
    accuracyBoost: 20,
    timeMultiplier: 1.4,
    bestModels: ['claude-3-opus', 'claude-3-5-sonnet', 'gpt-4-turbo'],
  },
  
  // 10. Decomposed Prompting
  'decomposed': {
    id: 'decomposed',
    name: 'Decomposed Prompting',
    description: 'Break complex problems into sub-problems',
    triggers: {
      intents: ['procedural', 'code', 'research'],
      complexityLevels: ['complex', 'expert'],
      domains: ['technology', 'business'],
    },
    promptTemplate: `{query}

This is a complex problem. Let me decompose it into manageable sub-problems:

**Sub-problem 1:** [First sub-problem]
**Solution 1:** [Solve it]

**Sub-problem 2:** [Second sub-problem] 
**Solution 2:** [Solve it, building on Solution 1]

**Sub-problem 3:** [Third sub-problem]
**Solution 3:** [Solve it, building on previous solutions]

**Integration:**
Combining all sub-solutions:

**Complete Solution:**`,
    requiresMultipleSamples: false,
    sampleCount: 1,
    temperature: 0.3,
    aggregationMethod: 'best-of',
    accuracyBoost: 22,
    timeMultiplier: 1.5,
    bestModels: ['gpt-4o', 'claude-3-5-sonnet', 'deepseek-chat'],
  },
  
  // 11. Contrastive Chain-of-Thought
  'contrastive-cot': {
    id: 'contrastive-cot',
    name: 'Contrastive Chain-of-Thought',
    description: 'Show correct vs incorrect reasoning paths',
    triggers: {
      intents: ['factual', 'troubleshooting'],
      complexityLevels: ['moderate', 'complex'],
      domains: ['education', 'technology'],
    },
    promptTemplate: `{query}

Let me contrast correct and incorrect approaches:

**Common Mistake (WRONG):**
[Show a plausible but incorrect approach]
❌ This is wrong because: [Explain the error]

**Correct Approach (RIGHT):**
[Show the correct reasoning]
✓ This is correct because: [Explain why]

**Key Insight:**
The difference between the wrong and right approach is:
[Highlight the critical distinction]

**Correct Answer:**`,
    requiresMultipleSamples: false,
    sampleCount: 1,
    temperature: 0.3,
    aggregationMethod: 'best-of',
    accuracyBoost: 18,
    timeMultiplier: 1.3,
    bestModels: ['claude-3-5-sonnet', 'gpt-4o'],
  },
  
  // 12. Self-Refine
  'self-refine': {
    id: 'self-refine',
    name: 'Self-Refine',
    description: 'Iterative self-improvement loop',
    triggers: {
      intents: ['creative', 'code', 'analytical'],
      complexityLevels: ['complex', 'expert'],
      domains: ['creative', 'technology'],
    },
    promptTemplate: `{query}

**Draft 1:**
[Initial response]

**Feedback on Draft 1:**
- What could be improved?
- [List specific improvements]

**Draft 2 (Improved):**
[Improved response based on feedback]

**Feedback on Draft 2:**
- Is this good enough?
- [List any remaining issues]

**Final Refined Response:**
[Best version incorporating all improvements]`,
    requiresMultipleSamples: false,
    sampleCount: 1,
    temperature: 0.4,
    aggregationMethod: 'best-of',
    accuracyBoost: 25,
    timeMultiplier: 2.5,
    bestModels: ['claude-3-5-sonnet', 'gpt-4o'],
  },
  
  // 13. Analogical Reasoning
  'analogical': {
    id: 'analogical',
    name: 'Analogical Reasoning',
    description: 'Reason by analogy to similar solved problems',
    triggers: {
      intents: ['analytical', 'troubleshooting', 'creative'],
      complexityLevels: ['moderate', 'complex'],
      domains: ['general', 'business', 'technology'],
    },
    promptTemplate: `{query}

Let me think of analogous situations:

**Similar Problem 1:**
[Describe a similar problem]
How it was solved: [Solution approach]
What we can learn: [Key insight]

**Similar Problem 2:**
[Describe another similar problem]
How it was solved: [Solution approach]
What we can learn: [Key insight]

**Applying Analogies:**
Based on these analogies, the best approach here is:
[Apply insights to current problem]

**Solution:**`,
    requiresMultipleSamples: false,
    sampleCount: 1,
    temperature: 0.5,
    aggregationMethod: 'best-of',
    accuracyBoost: 18,
    timeMultiplier: 1.4,
    bestModels: ['gpt-4o', 'claude-3-5-sonnet'],
  },
  
  // 14. Meta-Cognitive Prompting
  'meta-cognitive': {
    id: 'meta-cognitive',
    name: 'Meta-Cognitive Prompting',
    description: 'Think about thinking - plan and monitor reasoning',
    triggers: {
      intents: ['analytical', 'research'],
      complexityLevels: ['expert'],
      domains: ['science', 'philosophy'],
    },
    promptTemplate: `{query}

**Planning Phase:**
Before I answer, let me plan my approach:
- What type of problem is this?
- What knowledge domains are relevant?
- What's my strategy for solving it?
- What pitfalls should I avoid?

**Execution Phase:**
[Work through the problem]

**Monitoring Phase:**
As I work:
- Am I on the right track?
- Should I adjust my approach?
- Am I making any assumptions?

**Evaluation Phase:**
- Did my strategy work?
- How confident am I?
- What could I have done better?

**Final Answer:**`,
    requiresMultipleSamples: false,
    sampleCount: 1,
    temperature: 0.3,
    aggregationMethod: 'best-of',
    accuracyBoost: 22,
    timeMultiplier: 1.6,
    bestModels: ['o1-preview', 'claude-3-opus', 'claude-3-5-sonnet'],
  },
}

/**
 * Select the best reasoning strategy for a query
 */
export function selectReasoningStrategy(
  analysis: QueryAnalysis,
  availableModels: string[] = ['gpt-4o', 'claude-3-5-sonnet']
): ReasoningStrategy {
  const candidates: { strategy: ReasoningStrategy; score: number }[] = []
  
  for (const strategy of Object.values(REASONING_STRATEGIES)) {
    let score = 0
    
    // Intent match
    if (strategy.triggers.intents.includes(analysis.intent)) {
      score += 30
    }
    
    // Complexity match
    if (strategy.triggers.complexityLevels.includes(analysis.complexity)) {
      score += 25
    }
    
    // Domain match
    if (strategy.triggers.domains.includes(analysis.domain) || 
        strategy.triggers.domains.includes('general')) {
      score += 20
    }
    
    // Model availability
    const availableBestModels = strategy.bestModels.filter(m => 
      availableModels.some(am => am.toLowerCase().includes(m.toLowerCase()))
    )
    score += availableBestModels.length * 5
    
    // Accuracy boost consideration
    score += strategy.accuracyBoost * 0.5
    
    // Time/cost consideration (prefer faster for simple queries)
    if (analysis.complexity === 'simple') {
      score -= strategy.timeMultiplier * 5
    }
    
    candidates.push({ strategy, score })
  }
  
  // Sort by score and return best
  candidates.sort((a, b) => b.score - a.score)
  
  return candidates[0]?.strategy || REASONING_STRATEGIES['cot-zero-shot']
}

/**
 * Generate prompt with reasoning strategy applied
 */
export function applyReasoningStrategy(
  query: string,
  strategy: ReasoningStrategy
): string {
  return strategy.promptTemplate.replace('{query}', query)
}

/**
 * Aggregate multiple samples based on strategy
 */
export function aggregateSamples(
  samples: string[],
  strategy: ReasoningStrategy
): string {
  if (samples.length === 0) return ''
  if (samples.length === 1) return samples[0]
  
  switch (strategy.aggregationMethod) {
    case 'best-of':
      // Return longest/most detailed (simple heuristic)
      return samples.reduce((best, current) => 
        current.length > best.length ? current : best
      )
    
    case 'vote':
      // Find most common answer pattern
      return votingAggregation(samples)
    
    case 'synthesize':
      // Combine insights (placeholder - would use LLM)
      return synthesizeAggregation(samples)
    
    case 'verify':
      // Return only verified parts
      return samples[0] // Simplified
    
    default:
      return samples[0]
  }
}

/**
 * Voting-based aggregation for self-consistency
 */
function votingAggregation(samples: string[]): string {
  // Extract final answers (simplified)
  const answers: Record<string, { count: number; sample: string }> = {}
  
  for (const sample of samples) {
    // Use last paragraph as "answer signature"
    const paragraphs = sample.split('\n\n').filter(p => p.trim())
    const signature = paragraphs[paragraphs.length - 1]?.slice(0, 100) || ''
    
    const key = signature.toLowerCase().replace(/\s+/g, ' ')
    
    if (!answers[key]) {
      answers[key] = { count: 0, sample }
    }
    answers[key].count++
  }
  
  // Return most common
  const sorted = Object.entries(answers).sort((a, b) => b[1].count - a[1].count)
  return sorted[0]?.[1].sample || samples[0]
}

/**
 * Synthesis aggregation for tree-of-thought
 */
function synthesizeAggregation(samples: string[]): string {
  // In production, this would use an LLM to synthesize
  // For now, combine unique insights
  
  const parts = ['**Synthesized from multiple reasoning paths:**\n']
  
  samples.forEach((sample, idx) => {
    // Extract key conclusion
    const lines = sample.split('\n').filter(l => l.trim())
    const conclusion = lines.slice(-3).join('\n')
    parts.push(`\n**Path ${idx + 1} Conclusion:**\n${conclusion}\n`)
  })
  
  parts.push('\n**Combined Insight:**')
  parts.push('Based on all reasoning paths, the consensus answer is:')
  parts.push(samples[0]) // Use first as base
  
  return parts.join('\n')
}

/**
 * Get model-specific prompting adjustments
 */
export function getModelPromptAdjustments(
  modelId: string,
  strategy: ReasoningStrategy
): { prefix?: string; suffix?: string; temperature: number } {
  const profile = getModelProfile(modelId)
  
  if (!profile) {
    return { temperature: strategy.temperature }
  }
  
  // Model-specific adjustments
  if (modelId.includes('o1')) {
    // o1 does its own reasoning - simplify
    return {
      prefix: '', // No "think step by step" needed
      temperature: 1.0, // o1 ignores temperature
    }
  }
  
  if (modelId.includes('claude')) {
    // Claude benefits from XML structure
    return {
      prefix: '<thinking>',
      suffix: '</thinking>\n\n<answer>',
      temperature: profile.temperatureGuide.analysis,
    }
  }
  
  if (modelId.includes('deepseek')) {
    // DeepSeek works best with direct, technical prompts
    return {
      temperature: 0.0, // Very low for accuracy
    }
  }
  
  return { temperature: strategy.temperature }
}

/**
 * Build complete reasoning pipeline
 */
export function buildAdvancedReasoningPipeline(
  query: string,
  analysis: QueryAnalysis,
  availableModels: string[]
): {
  strategy: ReasoningStrategy
  prompt: string
  modelAssignments: { model: string; role: string }[]
  samplingConfig: { count: number; temperature: number }
  postProcessing: string[]
} {
  // Select best strategy
  const strategy = selectReasoningStrategy(analysis, availableModels)
  
  // Apply strategy to query
  const prompt = applyReasoningStrategy(query, strategy)
  
  // Assign models based on roles
  const modelAssignments: { model: string; role: string }[] = []
  
  // Primary model
  const primaryModel = strategy.bestModels.find(m => 
    availableModels.some(am => am.toLowerCase().includes(m.toLowerCase()))
  ) || availableModels[0]
  
  modelAssignments.push({ model: primaryModel, role: 'primary' })
  
  // Add verifier if strategy benefits from it
  if (strategy.aggregationMethod === 'verify' && availableModels.length > 1) {
    const verifier = availableModels.find(m => 
      m !== primaryModel && 
      (m.includes('claude') || m.includes('gpt'))
    )
    if (verifier) {
      modelAssignments.push({ model: verifier, role: 'verifier' })
    }
  }
  
  // Sampling configuration
  const samplingConfig = {
    count: strategy.requiresMultipleSamples ? strategy.sampleCount : 1,
    temperature: strategy.temperature,
  }
  
  // Post-processing steps
  const postProcessing: string[] = ['format-output']
  
  if (strategy.aggregationMethod === 'vote') {
    postProcessing.push('voting-aggregation')
  }
  
  if (analysis.complexity === 'expert') {
    postProcessing.push('depth-enhancement')
  }
  
  return {
    strategy,
    prompt,
    modelAssignments,
    samplingConfig,
    postProcessing,
  }
}

