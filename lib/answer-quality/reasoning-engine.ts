/**
 * Advanced Reasoning Engine
 * 
 * Implements state-of-the-art reasoning techniques to enhance answer quality:
 * 
 * 1. Chain-of-Thought (CoT) - Step-by-step reasoning
 * 2. Tree-of-Thought (ToT) - Explore multiple reasoning paths
 * 3. Self-Consistency - Multiple samples with voting
 * 4. ReAct - Reason + Act iteratively
 * 5. Reflexion - Self-reflection and correction
 * 6. Meta-Prompting - LLM orchestrates sub-tasks
 * 7. Skeleton-of-Thought - Parallel expansion
 */

import type { QueryAnalysis } from './types'

export type ReasoningMethod = 
  | 'chain-of-thought'
  | 'tree-of-thought'
  | 'self-consistency'
  | 'react'
  | 'reflexion'
  | 'meta-prompting'
  | 'skeleton-of-thought'
  | 'step-back'
  | 'least-to-most'
  | 'plan-and-solve'

export interface ReasoningConfig {
  method: ReasoningMethod
  temperature: number
  samplingCount: number
  maxDepth: number
  enableSelfCritique: boolean
  enableVerification: boolean
}

export interface ReasoningStep {
  id: string
  type: 'thought' | 'action' | 'observation' | 'reflection' | 'decision'
  content: string
  confidence: number
  children?: ReasoningStep[]
}

export interface ReasoningResult {
  method: ReasoningMethod
  steps: ReasoningStep[]
  finalAnswer: string
  confidence: number
  alternatives: string[]
  reasoning: string
}

// Reasoning method configurations
const REASONING_CONFIGS: Record<ReasoningMethod, Partial<ReasoningConfig>> = {
  'chain-of-thought': {
    temperature: 0.3,
    samplingCount: 1,
    maxDepth: 10,
    enableSelfCritique: true,
  },
  'tree-of-thought': {
    temperature: 0.7,
    samplingCount: 3,
    maxDepth: 5,
    enableSelfCritique: true,
  },
  'self-consistency': {
    temperature: 0.8,
    samplingCount: 5,
    maxDepth: 10,
    enableSelfCritique: false,
  },
  'react': {
    temperature: 0.3,
    samplingCount: 1,
    maxDepth: 8,
    enableVerification: true,
  },
  'reflexion': {
    temperature: 0.4,
    samplingCount: 1,
    maxDepth: 5,
    enableSelfCritique: true,
  },
  'meta-prompting': {
    temperature: 0.5,
    samplingCount: 1,
    maxDepth: 3,
    enableSelfCritique: true,
  },
  'skeleton-of-thought': {
    temperature: 0.4,
    samplingCount: 1,
    maxDepth: 2,
    enableSelfCritique: false,
  },
  'step-back': {
    temperature: 0.3,
    samplingCount: 1,
    maxDepth: 3,
    enableSelfCritique: true,
  },
  'least-to-most': {
    temperature: 0.3,
    samplingCount: 1,
    maxDepth: 5,
    enableSelfCritique: false,
  },
  'plan-and-solve': {
    temperature: 0.4,
    samplingCount: 1,
    maxDepth: 6,
    enableSelfCritique: true,
  },
}

/**
 * Select optimal reasoning method based on query analysis
 */
export function selectReasoningMethod(analysis: QueryAnalysis): ReasoningMethod {
  const { intent, complexity, domain } = analysis
  
  // Complex analytical queries benefit from tree exploration
  if (complexity === 'expert' && intent === 'analytical') {
    return 'tree-of-thought'
  }
  
  // Multi-step procedures need plan-and-solve
  if (intent === 'procedural' && complexity !== 'simple') {
    return 'plan-and-solve'
  }
  
  // Code/debugging benefits from ReAct
  if (intent === 'code' || intent === 'troubleshooting') {
    return 'react'
  }
  
  // Research queries need self-consistency
  if (intent === 'research') {
    return 'self-consistency'
  }
  
  // Complex questions benefit from least-to-most decomposition
  if (complexity === 'complex') {
    return 'least-to-most'
  }
  
  // Abstract questions benefit from step-back
  if (intent === 'analytical' && domain === 'science') {
    return 'step-back'
  }
  
  // Default to chain-of-thought
  return 'chain-of-thought'
}

/**
 * Generate Chain-of-Thought prompt enhancement
 */
export function generateChainOfThoughtPrompt(query: string): string {
  return `${query}

Let's approach this step-by-step:

1. First, I'll identify the key aspects of this question
2. Then, I'll analyze each aspect systematically
3. Next, I'll consider any relevant context or constraints
4. Finally, I'll synthesize my findings into a comprehensive answer

Let me work through this carefully...`
}

/**
 * Generate Tree-of-Thought prompt structure
 */
export function generateTreeOfThoughtPrompt(query: string): string {
  return `${query}

I'll explore multiple reasoning paths to find the best answer:

**Path 1: Direct approach**
[Evaluate the straightforward interpretation]

**Path 2: Alternative perspective**
[Consider a different angle or interpretation]

**Path 3: Edge cases and nuances**
[Examine special cases and subtle aspects]

After evaluating all paths, the strongest reasoning leads to:`
}

/**
 * Generate Self-Consistency prompt for multiple samples
 */
export function generateSelfConsistencyPrompt(query: string, sampleIndex: number): string {
  const approaches = [
    'analytical and systematic',
    'creative and lateral-thinking',
    'practical and example-driven',
    'theoretical and principle-based',
    'comparative and contrastive',
  ]
  
  const approach = approaches[sampleIndex % approaches.length]
  
  return `${query}

Approach this question from a ${approach} perspective. Think through your reasoning carefully before providing your answer.`
}

/**
 * Generate ReAct (Reason + Act) prompt structure
 */
export function generateReActPrompt(query: string): string {
  return `${query}

I'll solve this using a Thought-Action-Observation loop:

**Thought 1:** What is the core problem I need to solve?
**Action 1:** [Identify the main challenge]
**Observation 1:** [What I learned]

**Thought 2:** What approach should I take?
**Action 2:** [Plan the solution strategy]
**Observation 2:** [Evaluate the approach]

**Thought 3:** How do I implement this?
**Action 3:** [Execute the solution]
**Observation 3:** [Verify the result]

**Final Answer:**`
}

/**
 * Generate Reflexion prompt with self-critique
 */
export function generateReflexionPrompt(query: string, previousAttempt?: string): string {
  if (!previousAttempt) {
    return `${query}

I'll solve this and then reflect on my answer to improve it.

**Initial Attempt:**
[Provide thorough answer]

**Self-Reflection:**
- What might be wrong or incomplete?
- What assumptions did I make?
- How could this be improved?

**Refined Answer:**
[Improved response based on reflection]`
  }
  
  return `Previous attempt: ${previousAttempt}

**Reflection on Previous Answer:**
- Identified issues: [List problems]
- Missing elements: [What was left out]
- Improvements needed: [Specific changes]

**Improved Answer:**`
}

/**
 * Generate Meta-Prompting structure for complex tasks
 */
export function generateMetaPromptingPrompt(query: string): string {
  return `${query}

As a Meta-Coordinator, I'll break this into specialized sub-tasks:

**Sub-task 1: Understanding**
[Expert role: Clarify the exact requirements]

**Sub-task 2: Research**
[Expert role: Gather relevant information and context]

**Sub-task 3: Analysis**
[Expert role: Analyze the information critically]

**Sub-task 4: Synthesis**
[Expert role: Combine insights into coherent answer]

**Sub-task 5: Validation**
[Expert role: Check for accuracy and completeness]

**Final Synthesized Response:**`
}

/**
 * Generate Skeleton-of-Thought for parallel expansion
 */
export function generateSkeletonOfThoughtPrompt(query: string): string {
  return `${query}

**SKELETON (outline to expand):**
1. [Key Point 1]
2. [Key Point 2]
3. [Key Point 3]
4. [Key Point 4]

Now expanding each point in detail:

**1. [Key Point 1]:**
[Detailed explanation]

**2. [Key Point 2]:**
[Detailed explanation]

**3. [Key Point 3]:**
[Detailed explanation]

**4. [Key Point 4]:**
[Detailed explanation]

**Summary:**`
}

/**
 * Generate Step-Back prompt for abstraction
 */
export function generateStepBackPrompt(query: string): string {
  return `${query}

Before answering directly, let me step back and consider the broader context:

**Higher-Level Question:** What are the fundamental principles involved here?

**Principles Identified:**
1. [Principle 1]
2. [Principle 2]
3. [Principle 3]

**Applying Principles to Original Question:**
Now, using these principles, I can provide a more grounded answer:

**Answer:**`
}

/**
 * Generate Least-to-Most decomposition prompt
 */
export function generateLeastToMostPrompt(query: string): string {
  return `${query}

I'll decompose this into simpler sub-questions and solve from easiest to hardest:

**Sub-questions (easiest to hardest):**
1. [Simple sub-question]
2. [Medium sub-question]
3. [Complex sub-question]
4. [Most complex sub-question]

**Solutions:**

**Q1:** [Answer to simplest]
**Q2:** Building on Q1: [Answer]
**Q3:** Building on Q1 & Q2: [Answer]
**Q4:** Building on all previous: [Answer]

**Complete Answer:**`
}

/**
 * Generate Plan-and-Solve prompt
 */
export function generatePlanAndSolvePrompt(query: string): string {
  return `${query}

**PLAN:**
First, let me devise a plan to solve this:
1. Understand: [What exactly is being asked]
2. Identify: [Key information and constraints]
3. Approach: [Method to solve]
4. Execute: [Step-by-step solution]
5. Verify: [Check the answer]

**SOLVE:**

**Step 1 - Understand:**
[Clarify the problem]

**Step 2 - Identify:**
[List key information]

**Step 3 - Approach:**
[Describe the method]

**Step 4 - Execute:**
[Work through the solution]

**Step 5 - Verify:**
[Validate the answer]

**Final Answer:**`
}

/**
 * Get the prompt generator for a reasoning method
 */
export function getPromptGenerator(method: ReasoningMethod): (query: string) => string {
  const generators: Record<ReasoningMethod, (query: string) => string> = {
    'chain-of-thought': generateChainOfThoughtPrompt,
    'tree-of-thought': generateTreeOfThoughtPrompt,
    'self-consistency': (q) => generateSelfConsistencyPrompt(q, 0),
    'react': generateReActPrompt,
    'reflexion': generateReflexionPrompt,
    'meta-prompting': generateMetaPromptingPrompt,
    'skeleton-of-thought': generateSkeletonOfThoughtPrompt,
    'step-back': generateStepBackPrompt,
    'least-to-most': generateLeastToMostPrompt,
    'plan-and-solve': generatePlanAndSolvePrompt,
  }
  
  return generators[method]
}

/**
 * Get configuration for a reasoning method
 */
export function getReasoningConfig(method: ReasoningMethod): ReasoningConfig {
  const base: ReasoningConfig = {
    method,
    temperature: 0.4,
    samplingCount: 1,
    maxDepth: 5,
    enableSelfCritique: false,
    enableVerification: false,
  }
  
  return { ...base, ...REASONING_CONFIGS[method] }
}

/**
 * Extract reasoning steps from a response
 */
export function extractReasoningSteps(response: string): ReasoningStep[] {
  const steps: ReasoningStep[] = []
  
  // Extract numbered steps
  const numberedPattern = /(?:Step\s*)?(\d+)[.:\s]+(.+?)(?=(?:Step\s*)?\d+[.:\s]|$)/gi
  let match
  
  while ((match = numberedPattern.exec(response)) !== null) {
    steps.push({
      id: `step-${match[1]}`,
      type: 'thought',
      content: match[2].trim(),
      confidence: 0.8,
    })
  }
  
  // Extract thought/action/observation patterns (ReAct)
  const reactPattern = /\*\*(Thought|Action|Observation)\s*\d*:?\*\*\s*(.+?)(?=\*\*(?:Thought|Action|Observation|Final)|$)/gi
  
  while ((match = reactPattern.exec(response)) !== null) {
    const type = match[1].toLowerCase() as 'thought' | 'action' | 'observation'
    steps.push({
      id: `react-${steps.length}`,
      type,
      content: match[2].trim(),
      confidence: 0.85,
    })
  }
  
  return steps
}

/**
 * Combine multiple reasoning results (for self-consistency)
 */
export function combineReasoningResults(results: ReasoningResult[]): ReasoningResult {
  if (results.length === 0) {
    return {
      method: 'chain-of-thought',
      steps: [],
      finalAnswer: '',
      confidence: 0,
      alternatives: [],
      reasoning: 'No results to combine',
    }
  }
  
  if (results.length === 1) {
    return results[0]
  }
  
  // Vote on final answers (simplified - in production, use semantic similarity)
  const answerVotes: Record<string, number> = {}
  
  for (const result of results) {
    // Use first 200 chars as answer signature
    const signature = result.finalAnswer.slice(0, 200).toLowerCase().trim()
    answerVotes[signature] = (answerVotes[signature] || 0) + 1
  }
  
  // Find the most common answer pattern
  let maxVotes = 0
  let winningSignature = ''
  
  for (const [sig, votes] of Object.entries(answerVotes)) {
    if (votes > maxVotes) {
      maxVotes = votes
      winningSignature = sig
    }
  }
  
  // Get the full answer from the winning result
  const winningResult = results.find(r => 
    r.finalAnswer.slice(0, 200).toLowerCase().trim() === winningSignature
  ) || results[0]
  
  // Collect alternatives
  const alternatives = results
    .filter(r => r !== winningResult)
    .map(r => r.finalAnswer)
    .slice(0, 3)
  
  return {
    method: 'self-consistency',
    steps: winningResult.steps,
    finalAnswer: winningResult.finalAnswer,
    confidence: maxVotes / results.length,
    alternatives,
    reasoning: `Selected by ${maxVotes}/${results.length} consensus`,
  }
}

/**
 * Apply self-critique to improve an answer
 */
export function generateSelfCritiquePrompt(originalAnswer: string): string {
  return `Please critique this answer and identify any issues:

---
${originalAnswer}
---

**Critique:**

1. **Accuracy Issues:**
   - [List any factual errors or unsupported claims]

2. **Completeness Issues:**
   - [List any missing information or aspects not addressed]

3. **Clarity Issues:**
   - [List any confusing or unclear explanations]

4. **Structure Issues:**
   - [List any organizational problems]

**Suggested Improvements:**
[Specific suggestions for how to improve the answer]

**Improved Answer:**
[Provide the corrected and enhanced version]`
}

/**
 * Build the full reasoning pipeline for a query
 */
export function buildReasoningPipeline(
  query: string,
  analysis: QueryAnalysis
): {
  method: ReasoningMethod
  config: ReasoningConfig
  enhancedPrompt: string
  postProcessing: string[]
} {
  const method = selectReasoningMethod(analysis)
  const config = getReasoningConfig(method)
  const promptGenerator = getPromptGenerator(method)
  const enhancedPrompt = promptGenerator(query)
  
  const postProcessing: string[] = []
  
  if (config.enableSelfCritique) {
    postProcessing.push('self-critique')
  }
  
  if (config.enableVerification) {
    postProcessing.push('fact-verification')
  }
  
  if (analysis.complexity === 'expert') {
    postProcessing.push('depth-enhancement')
  }
  
  return {
    method,
    config,
    enhancedPrompt,
    postProcessing,
  }
}

