// Comprehensive reasoning methods data model with reference links
export interface ReasoningMethodData {
  id: string
  name: string
  year: number
  category: ReasoningCategory
  shortDescription: string
  strengths: string[]
  weaknesses: string[]
  referenceUrl: string
  benchmarkResults?: string
}

export type ReasoningCategory =
  | "General Reasoning"
  | "Code Generation & Reasoning"
  | "Mathematical Reasoning"
  | "Commonsense & Logical Reasoning"
  | "Multi-Modal Reasoning"

export const REASONING_CATEGORIES: ReasoningCategory[] = [
  "General Reasoning",
  "Code Generation & Reasoning",
  "Mathematical Reasoning",
  "Commonsense & Logical Reasoning",
  "Multi-Modal Reasoning",
]

export const REASONING_METHODS: ReasoningMethodData[] = [
  // General Reasoning
  {
    id: "cot",
    name: "Chain-of-Thought (CoT) Prompting",
    year: 2022,
    category: "General Reasoning",
    shortDescription:
      "Breaks problems into steps via prompt engineering. Enables LMs to generate intermediate reasoning steps before the final answer.",
    strengths: [
      "Improves accuracy on multi-step reasoning tasks",
      "State-of-the-art on GSM8K math benchmark",
      "Works across domains (math, logic, commonsense)",
    ],
    weaknesses: [
      "Increases token usage and latency",
      "Mainly effective in sufficiently large models",
      "May produce verbose reasoning",
    ],
    referenceUrl: "https://arxiv.org/abs/2201.11903",
    benchmarkResults: "540B model with CoT achieved SOTA on GSM8K, surpassing fine-tuned GPT-3",
  },
  {
    id: "self-consistency",
    name: "Self-Consistency Decoding",
    year: 2022,
    category: "General Reasoning",
    shortDescription:
      "Majority-vote over multiple reasoning paths. Samples diverse CoT trails and chooses the most common answer.",
    strengths: [
      "+17.9% accuracy on GSM8K",
      "+11% on SVAMP, +12% on AQuA",
      "+6.4% on StrategyQA, +3.9% on ARC-Challenge",
    ],
    weaknesses: [
      "Higher compute cost (sampling many outputs)",
      "Requires multiple inference passes",
      "May not help if all paths share the same bias",
    ],
    referenceUrl: "https://arxiv.org/abs/2203.11171",
    benchmarkResults: "Improved CoT performance on GSM8K by +17.9% absolute",
  },
  {
    id: "tree-of-thoughts",
    name: "Tree-of-Thoughts (ToT) Search",
    year: 2023,
    category: "General Reasoning",
    shortDescription:
      "Deliberative branching of reasoning steps. Explores a tree of possible thought sequences and backtracks as needed.",
    strengths: [
      "74% solve rate on Game of 24 (vs 4% with CoT)",
      "Excels at planning and multi-hop reasoning",
      "Systematically finds correct solutions",
    ],
    weaknesses: [
      "Extra prompting steps and state management",
      "High computational overhead",
      "Complex to implement and tune",
    ],
    referenceUrl: "https://arxiv.org/abs/2305.10601",
    benchmarkResults: "GPT-4 with ToT solved 74% of Game of 24 challenges vs ~4% with standard CoT",
  },
  {
    id: "react",
    name: "ReAct (Reason+Act Framework)",
    year: 2022,
    category: "General Reasoning",
    shortDescription:
      "Interleaving reasoning with tool use/actions. Produces reasoning traces alongside actions in an interwoven loop.",
    strengths: [
      "35.1% exact-match on HotpotQA (vs 29% CoT)",
      "10-34% improvement on interactive tasks",
      "Human-like, interpretable chains",
    ],
    weaknesses: ["Requires external APIs or simulators", "More complex prompting", "Dependent on tool reliability"],
    referenceUrl: "https://research.google/blog/react-synergizing-reasoning-and-acting-in-language-models/",
    benchmarkResults: "ReAct + CoT achieved 35.1% on HotpotQA vs ~29% with CoT alone",
  },
  {
    id: "pal",
    name: "Program-Aided Reasoning (PAL)",
    year: 2022,
    category: "General Reasoning",
    shortDescription:
      "LLM generates code to solve problems. Outputs a Python program as the reasoning chain, executes it, returns the result.",
    strengths: [
      "58.4% accuracy on GSM8K (vs 48.2% with CoT)",
      "Eliminates final-step calculation errors",
      "Verifiable reasoning via executed programs",
    ],
    weaknesses: [
      "Requires execution environment",
      "Overhead of running code",
      "Limited to problems expressible as code",
    ],
    referenceUrl: "https://arxiv.org/abs/2211.10435",
    benchmarkResults: "PAL achieved 58.4% on GSM8K, surpassing 48.2% with plain CoT",
  },
  {
    id: "self-reflection",
    name: "Self-Reflection & Iterative Refinement",
    year: 2023,
    category: "General Reasoning",
    shortDescription:
      "Models critique and refine their own outputs. Generates initial answer, inspects for errors, then improves upon it.",
    strengths: [
      "88% pass@1 on HumanEval (vs 67% base GPT-4)",
      "+12% accuracy on MBPP coding tasks",
      "+9% on hardest Spider SQL queries",
    ],
    weaknesses: [
      "Increased computation from multiple generations",
      "May over-correct or introduce new errors",
      "Diminishing returns after few iterations",
    ],
    referenceUrl: "https://arxiv.org/abs/2303.11366",
    benchmarkResults: "Reflexion-augmented GPT-4 achieved 88% pass@1 on HumanEval",
  },

  // Code Generation & Reasoning
  {
    id: "alphacode",
    name: "Massive Sample & Filter (AlphaCode)",
    year: 2022,
    category: "Code Generation & Reasoning",
    shortDescription:
      "Generate many solutions and test them. Generates tens of thousands of solutions and filters by running against unit tests.",
    strengths: [
      "Top 54.3% rank among human competitors",
      "First AI to achieve median human performance",
      "Robust against edge cases via filtering",
    ],
    weaknesses: [
      "Heavy computation (many samples)",
      "Requires reliable test cases",
      "Not practical for real-time applications",
    ],
    referenceUrl: "https://deepmind.google/discover/blog/competitive-programming-with-alphacode/",
    benchmarkResults: "Achieved average rank in top 54.3% of Codeforces competitors",
  },
  {
    id: "self-debugging",
    name: "Self-Debugging & Automated Repair",
    year: 2023,
    category: "Code Generation & Reasoning",
    shortDescription:
      "LLM fixes its own code errors. Runs the code, reads error messages, generates explanation of what went wrong, then corrects.",
    strengths: ["+12% solve rate on MBPP", "+2-3% on Spider SQL benchmark", "+9% on hardest SQL queries"],
    weaknesses: [
      "Requires execution environment",
      "May enter infinite repair loops",
      "Limited by model's debugging skills",
    ],
    referenceUrl: "https://arxiv.org/abs/2304.05128",
    benchmarkResults: "Improved MBPP solve rate by 12 percentage points",
  },
  {
    id: "reflexion-code",
    name: "Reflexion / Iterative Prompting for Code",
    year: 2023,
    category: "Code Generation & Reasoning",
    shortDescription:
      "Multiple attempts guided by self-reflection. Model tries, checks result, thinks aloud about errors, then attempts again.",
    strengths: [
      "88% pass@1 on HumanEval",
      "Near perfection on certain coding challenges",
      "Eliminates trivial errors through iteration",
    ],
    weaknesses: [
      "Longer runtime (multiple model calls)",
      "Careful prompt design required",
      "May not overcome fundamental capability gaps",
    ],
    referenceUrl: "https://arxiv.org/abs/2303.11366",
    benchmarkResults: "Reflexion-based agent reached 88% pass@1 on HumanEval",
  },
  {
    id: "code-cot",
    name: "Code Chain-of-Thought & Planning",
    year: 2022,
    category: "Code Generation & Reasoning",
    shortDescription:
      "Reasoning steps in natural language before coding. Outlines solution approach or writes pseudo-code, then produces final code.",
    strengths: ["Produces well-organized code", "Reduces logical mistakes", "Human-like planning for coding"],
    weaknesses: [
      "Planning may not match execution needs",
      "Adds overhead for simple tasks",
      "Often combined with other methods",
    ],
    referenceUrl: "https://arxiv.org/abs/2211.01910",
    benchmarkResults: "Improves success on multi-step coding puzzles when combined with Least-to-Most",
  },

  // Mathematical Reasoning
  {
    id: "minerva",
    name: "CoT with Specialized Training (Minerva)",
    year: 2022,
    category: "Mathematical Reasoning",
    shortDescription:
      "Training LLMs on step-by-step solutions. Fine-tuned on 118GB of math/science texts with CoT prompting + voting at inference.",
    strengths: ["50.3% on MATH (vs previous 6.9%)", "SOTA on GSM8K and STEM exams", "Unlocks emergent math abilities"],
    weaknesses: [
      "Needs large curated training data",
      "Very large model sizes required",
      "May not generalize to novel problem types",
    ],
    referenceUrl: "https://research.google/blog/minerva-solving-quantitative-reasoning-problems-with-language-models/",
    benchmarkResults: "50.3% accuracy on MATH dataset vs previous best of 6.9%",
  },
  {
    id: "math-self-consistency",
    name: "Self-Consistency & Voting in Math",
    year: 2022,
    category: "Mathematical Reasoning",
    shortDescription:
      "Mitigating calculation errors by consensus. Samples many CoT solutions and takes majority vote on final answer.",
    strengths: [
      "+17.9% absolute accuracy on GSM8K",
      "74% to 78.5% on GSM8K with voting",
      "Boosts reliability without additional training",
    ],
    weaknesses: [
      "More inference passes required",
      "Wrong answers may still converge",
      "Doesn't improve underlying capabilities",
    ],
    referenceUrl: "https://arxiv.org/abs/2203.11171",
    benchmarkResults: "Voting bumped PaLM 540B model's GSM8K score from ~74% to 78.5%",
  },
  {
    id: "pal-math",
    name: "Program-Aided Math Solving (PAL)",
    year: 2022,
    category: "Mathematical Reasoning",
    shortDescription:
      "Language model writes a program to do the math. Outputs solvable program instead of numeric answer, defers to executor.",
    strengths: ["48.2% to 58.4% on GSM8K", "Introduces symbolic precision", "Eliminates arithmetic errors"],
    weaknesses: [
      "Requires runtime integration",
      "May struggle if coding is incorrect",
      "Problem must be code-expressible",
    ],
    referenceUrl: "https://arxiv.org/abs/2211.10435",
    benchmarkResults: "Improved accuracy from 48.2% to 58.4% on GSM8K",
  },
  {
    id: "tot-puzzle",
    name: "Tree-of-Thought for Puzzle Solving",
    year: 2023,
    category: "Mathematical Reasoning",
    shortDescription:
      "Systematic search for math puzzles. Explores different solution paths and backtracks when a path is invalid.",
    strengths: [
      "74% on Game of 24 (vs <10% linear)",
      "Dramatically boosts combinatorial problems",
      "Ensures model doesn't get stuck",
    ],
    weaknesses: [
      "Complex control logic needed",
      "More calls to the model",
      "May not scale to very large search spaces",
    ],
    referenceUrl: "https://arxiv.org/abs/2305.10601",
    benchmarkResults: "GPT-4 with ToT solved 74% vs <10% with linear reasoning",
  },
  {
    id: "least-to-most",
    name: "Least-to-Most Decomposition",
    year: 2022,
    category: "Mathematical Reasoning",
    shortDescription:
      "Break complex problems into subproblems. Generates simpler sub-questions and solves them incrementally.",
    strengths: [
      "Outperforms standard CoT on certain tasks",
      "Reduces cognitive load per step",
      "Mimics human problem-solving approach",
    ],
    weaknesses: [
      "Relies on correct subproblem generation",
      "May miss holistic solution strategies",
      "Can be tricky to decompose correctly",
    ],
    referenceUrl: "https://arxiv.org/abs/2205.10625",
    benchmarkResults: "Higher accuracy than CoT on last letter concatenation puzzle",
  },

  // Commonsense & Logical Reasoning
  {
    id: "cot-commonsense",
    name: "CoT + Self-Consistency (Commonsense)",
    year: 2022,
    category: "Commonsense & Logical Reasoning",
    shortDescription:
      "Step-by-step reasoning for commonsense QA. Combines CoT with self-consistency for robust answers.",
    strengths: ["+6.4% on StrategyQA", "+3.9% on ARC-Challenge", "Broadly applicable to logic puzzles"],
    weaknesses: [
      "Smaller gains than in math",
      "May not overcome knowledge gaps",
      "Commonsense failures can be systematic",
    ],
    referenceUrl: "https://arxiv.org/abs/2203.11171",
    benchmarkResults: "+6.4% on StrategyQA and +3.9% on ARC-Challenge",
  },
  {
    id: "decomposition",
    name: "Decomposition Prompting (Least-to-Most)",
    year: 2022,
    category: "Commonsense & Logical Reasoning",
    shortDescription:
      "Explicitly break down complex questions. Generates intermediate questions and answers them sequentially.",
    strengths: ["Higher accuracy than vanilla CoT", "Handles multi-hop reasoning", "Ensures each piece is handled"],
    weaknesses: [
      "Decomposition errors propagate",
      "Chain of subquestions can go astray",
      "May lose context across sub-questions",
    ],
    referenceUrl: "https://arxiv.org/abs/2205.10625",
    benchmarkResults: "Outperformed vanilla CoT on multi-step reasoning tasks",
  },
  {
    id: "ircot",
    name: "Iterative Retrieval + CoT (IRCoT)",
    year: 2023,
    category: "Commonsense & Logical Reasoning",
    shortDescription:
      "Fetch relevant knowledge at each reasoning step. Interleaves retrieval with chain-of-thought reasoning.",
    strengths: [
      "+15 points QA accuracy on HotpotQA",
      "+21 points retrieval precision",
      "Stays grounded in facts for multi-hop QA",
    ],
    weaknesses: ["Requires search API", "Complex pipeline management", "Retrieval latency adds up"],
    referenceUrl: "https://arxiv.org/abs/2212.10509",
    benchmarkResults: "Up to +15 points on QA accuracy and +21 on retrieval precision",
  },
  {
    id: "lot",
    name: "Logic-Augmented Prompting (LoT)",
    year: 2024,
    category: "Commonsense & Logical Reasoning",
    shortDescription:
      "Inject formal logic structure into reasoning. Extracts propositional logic from text as additional context.",
    strengths: ["+4.35% on ReClor (LSAT-like QA)", "+5% on LogiQA with CoT+SC", "+8% on ProofWriter with ToT"],
    weaknesses: [
      "Needs reliable text-to-logic parsing",
      "May not generalize to all problems",
      "Added complexity in prompt design",
    ],
    referenceUrl: "https://arxiv.org/abs/2401.04073",
    benchmarkResults: "+4.35% on ReClor, +5% on LogiQA, +8% on ProofWriter",
  },
  {
    id: "neuro-symbolic",
    name: "Hybrid Neuro-Symbolic Solvers",
    year: 2023,
    category: "Commonsense & Logical Reasoning",
    shortDescription:
      "External logical tools with LLM guidance. LLMs call dedicated logic engines (e.g., SAT solvers).",
    strengths: [
      "Perfect accuracy on certain puzzle tasks",
      "Combines language understanding with symbolic rigor",
      "Guaranteed logical reasoning",
    ],
    weaknesses: ["Complex system integration", "Requires domain-specific solvers", "Less common in general usage"],
    referenceUrl: "https://arxiv.org/abs/2304.09102",
    benchmarkResults: "Can achieve perfect accuracy on logic grid puzzles",
  },

  // Multi-Modal Reasoning
  {
    id: "multimodal-cot",
    name: "Multimodal Chain-of-Thought",
    year: 2022,
    category: "Multi-Modal Reasoning",
    shortDescription:
      "Reasoning chains that include visual inputs. Produces explanations that reference image content before answering.",
    strengths: [
      "90.45% on ScienceQA (vs 86.54% prior)",
      "~4% jump on visual reasoning tasks",
      "Transparent decision process",
    ],
    weaknesses: [
      "Requires multimodal training",
      "Model must understand text and images jointly",
      "Visual reasoning steps can be imprecise",
    ],
    referenceUrl: "https://arxiv.org/abs/2302.00923",
    benchmarkResults: "90.45% accuracy on ScienceQA, improving over prior SOTA of 86.54%",
  },
  {
    id: "palm-e",
    name: "Embodied Multimodal Models (PaLM-E)",
    year: 2023,
    category: "Multi-Modal Reasoning",
    shortDescription:
      "Feeding visual features into giant language models. Connects 540B LM with vision encoders for multimodal reasoning.",
    strengths: [
      "66.1% on OK-VQA (outperforms specialists)",
      "Excels in captioning and planning",
      "Seamless text and vision reasoning",
    ],
    weaknesses: [
      "Sheer model size and complexity",
      "Expensive training requirements",
      "Limited to specific embodied domains",
    ],
    referenceUrl: "https://palm-e.github.io/",
    benchmarkResults: "66.1% on OK-VQA, outperforming specialist models",
  },
  {
    id: "tool-visual",
    name: "Tool-Augmented Visual Reasoning",
    year: 2023,
    category: "Multi-Modal Reasoning",
    shortDescription:
      "Using external tools on visual tasks via reasoning. Allows VLMs to call OCR, calculators, or vision APIs.",
    strengths: [
      "Addresses pure vision-to-text failures",
      "Significantly improves chart QA accuracy",
      "Modular and extensible",
    ],
    weaknesses: ["Pipeline complexity", "Errors can compound across tools", "Tool integration overhead"],
    referenceUrl: "https://arxiv.org/abs/2303.04671",
    benchmarkResults: "Solves problems no single model could solve alone on diagram reasoning",
  },
  {
    id: "vlm-cot",
    name: "Large VLMs with CoT (GPT-4V & others)",
    year: 2023,
    category: "Multi-Modal Reasoning",
    shortDescription:
      "Very large multimodal models that inherently reason. Reasons through image content stepwise to answer queries.",
    strengths: [
      "Exceeds human performance on VQAv2 metrics",
      "Benefits from all text-domain advances",
      "Unified architecture simplicity",
    ],
    weaknesses: [
      "Huge scale required",
      "Difficulty evaluating reasoning vs pattern matching",
      "May hallucinate visual details",
    ],
    referenceUrl: "https://openai.com/research/gpt-4v-system-card",
    benchmarkResults: "GPT-4V exceeds human performance on some VQA metrics",
  },
]

export function getMethodsByCategory(category: ReasoningCategory): ReasoningMethodData[] {
  return REASONING_METHODS.filter((method) => method.category === category)
}

export function getMethodById(id: string): ReasoningMethodData | undefined {
  return REASONING_METHODS.find((method) => method.id === id)
}
