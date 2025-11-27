// Comprehensive reasoning methods data model
export interface ReasoningMethodData {
  id: string
  name: string
  category: ReasoningCategory
  shortDescription: string
  strengths: string[]
  weaknesses: string[]
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
    category: "General Reasoning",
    shortDescription:
      "Guides the model to break down complex problems into intermediate reasoning steps before reaching a conclusion.",
    strengths: [
      "Improves accuracy on multi-step reasoning tasks",
      "Makes model reasoning transparent and interpretable",
      "Works well with few-shot examples",
    ],
    weaknesses: [
      "Increases token usage and latency",
      "May produce verbose or redundant reasoning",
      "Less effective for simple factual queries",
    ],
  },
  {
    id: "self-consistency",
    name: "Self-Consistency Decoding",
    category: "General Reasoning",
    shortDescription:
      "Generates multiple reasoning paths and selects the most consistent answer through majority voting.",
    strengths: [
      "Reduces errors from single-path reasoning",
      "Provides confidence estimates via vote distribution",
      "Complements chain-of-thought prompting",
    ],
    weaknesses: [
      "Significantly increases compute cost",
      "Requires multiple inference passes",
      "May not help if all paths share the same bias",
    ],
  },
  {
    id: "tree-of-thoughts",
    name: "Tree-of-Thoughts (ToT) Search",
    category: "General Reasoning",
    shortDescription:
      "Explores multiple reasoning branches in a tree structure, evaluating and pruning paths to find optimal solutions.",
    strengths: [
      "Excels at complex planning and puzzle-solving",
      "Allows backtracking from dead ends",
      "Combines search algorithms with LLM reasoning",
    ],
    weaknesses: [
      "High computational overhead",
      "Complex to implement and tune",
      "Overkill for straightforward problems",
    ],
  },
  {
    id: "react",
    name: "ReAct (Reason+Act Framework)",
    category: "General Reasoning",
    shortDescription:
      "Interleaves reasoning traces with actions, enabling the model to interact with external tools and environments.",
    strengths: [
      "Enables dynamic information retrieval",
      "Grounds reasoning in real-world data",
      "Reduces hallucination through fact-checking",
    ],
    weaknesses: [
      "Requires integration with external tools",
      "Action loops can become inefficient",
      "Dependent on tool reliability and latency",
    ],
  },
  {
    id: "pal",
    name: "Program-Aided Reasoning (PAL)",
    category: "General Reasoning",
    shortDescription:
      "Generates code to solve problems, delegating computation to a program interpreter for precise execution.",
    strengths: [
      "Achieves near-perfect arithmetic accuracy",
      "Leverages code execution for complex logic",
      "Reduces reasoning errors in quantitative tasks",
    ],
    weaknesses: [
      "Requires secure code execution environment",
      "Limited to problems expressible as code",
      "May produce syntactically incorrect programs",
    ],
  },
  {
    id: "self-reflection",
    name: "Self-Reflection & Iterative Refinement",
    category: "General Reasoning",
    shortDescription: "Model critiques its own output and iteratively improves it through multiple refinement cycles.",
    strengths: [
      "Catches and corrects initial errors",
      "Improves output quality over iterations",
      "Mimics human revision process",
    ],
    weaknesses: [
      "Multiple passes increase latency",
      "May over-correct or introduce new errors",
      "Diminishing returns after few iterations",
    ],
  },

  // Code Generation & Reasoning
  {
    id: "alphacode",
    name: "Massive Sample & Filter (AlphaCode Strategy)",
    category: "Code Generation & Reasoning",
    shortDescription:
      "Generates a large number of code solutions and filters them using test cases to find correct implementations.",
    strengths: [
      "Achieves competitive programming-level results",
      "Robust against edge cases via filtering",
      "Leverages diversity in generation",
    ],
    weaknesses: [
      "Extremely compute-intensive",
      "Requires comprehensive test suites",
      "Not practical for real-time applications",
    ],
  },
  {
    id: "self-debugging",
    name: "Self-Debugging & Automated Repair",
    category: "Code Generation & Reasoning",
    shortDescription: "Model identifies bugs in generated code and iteratively repairs them using error feedback.",
    strengths: [
      "Autonomously fixes syntax and logic errors",
      "Learns from execution feedback",
      "Reduces manual debugging effort",
    ],
    weaknesses: [
      "Requires code execution capabilities",
      "May enter infinite repair loops",
      "Limited by model's debugging skills",
    ],
  },
  {
    id: "reflexion-code",
    name: "Reflexion / Iterative Prompting for Code",
    category: "Code Generation & Reasoning",
    shortDescription: "Uses verbal feedback from failed attempts to guide subsequent code generation iterations.",
    strengths: [
      "Builds on linguistic self-reflection",
      "Improves success rate over iterations",
      "Works without code execution in some variants",
    ],
    weaknesses: [
      "Requires meaningful feedback signals",
      "May not overcome fundamental capability gaps",
      "Iteration overhead adds latency",
    ],
  },
  {
    id: "code-cot",
    name: "Code Chain-of-Thought & Planning",
    category: "Code Generation & Reasoning",
    shortDescription:
      "Plans solution architecture step-by-step before writing code, improving structure and correctness.",
    strengths: [
      "Produces well-organized code",
      "Reduces logic errors through planning",
      "Makes code generation more predictable",
    ],
    weaknesses: [
      "Planning may not match execution needs",
      "Adds overhead for simple tasks",
      "Plans can become outdated mid-generation",
    ],
  },

  // Mathematical Reasoning
  {
    id: "minerva",
    name: "Chain-of-Thought with Specialized Training (Minerva-style)",
    category: "Mathematical Reasoning",
    shortDescription: "Fine-tuned models that combine chain-of-thought with deep mathematical training data.",
    strengths: [
      "State-of-the-art on math benchmarks",
      "Handles symbolic and numerical reasoning",
      "Trained on curated math corpora",
    ],
    weaknesses: [
      "Requires specialized model training",
      "May not generalize to novel problem types",
      "Limited by training data coverage",
    ],
  },
  {
    id: "math-self-consistency",
    name: "Self-Consistency & Voting in Math",
    category: "Mathematical Reasoning",
    shortDescription: "Samples multiple solution paths for math problems and selects answers via majority voting.",
    strengths: [
      "Significantly boosts math accuracy",
      "Identifies reliable vs uncertain answers",
      "Works with any CoT-capable model",
    ],
    weaknesses: [
      "High token and compute cost",
      "Voting may fail if most paths err similarly",
      "Doesn't improve underlying capabilities",
    ],
  },
  {
    id: "pal-math",
    name: "Program-Aided Math Solving (PAL)",
    category: "Mathematical Reasoning",
    shortDescription: "Translates math word problems into executable code for precise numerical computation.",
    strengths: [
      "Eliminates arithmetic errors",
      "Handles complex calculations reliably",
      "Interpretable solution via code",
    ],
    weaknesses: [
      "Problem must be code-expressible",
      "Code generation errors possible",
      "Requires safe execution sandbox",
    ],
  },
  {
    id: "tot-puzzle",
    name: "Tree-of-Thought for Puzzle Solving",
    category: "Mathematical Reasoning",
    shortDescription:
      "Applies tree search to mathematical puzzles, exploring and evaluating multiple solution branches.",
    strengths: [
      "Excels at constraint satisfaction problems",
      "Enables systematic exploration",
      "Can solve puzzles requiring backtracking",
    ],
    weaknesses: ["Computationally expensive", "Complex implementation", "May not scale to very large search spaces"],
  },
  {
    id: "least-to-most",
    name: "Least-to-Most Decomposition",
    category: "Mathematical Reasoning",
    shortDescription:
      "Breaks complex problems into simpler subproblems, solving them incrementally from easiest to hardest.",
    strengths: [
      "Handles compositional reasoning well",
      "Reduces cognitive load per step",
      "Generalizes to unseen problem structures",
    ],
    weaknesses: [
      "Decomposition itself can be error-prone",
      "May miss holistic solution strategies",
      "Adds overhead for already simple problems",
    ],
  },

  // Commonsense & Logical Reasoning
  {
    id: "cot-commonsense",
    name: "CoT + Self-Consistency (Commonsense QA)",
    category: "Commonsense & Logical Reasoning",
    shortDescription:
      "Combines chain-of-thought with self-consistency voting for robust commonsense question answering.",
    strengths: [
      "Improves commonsense benchmark scores",
      "Reduces random errors via voting",
      "Transparent reasoning process",
    ],
    weaknesses: [
      "May not overcome fundamental knowledge gaps",
      "Expensive for simple questions",
      "Commonsense failures can be systematic",
    ],
  },
  {
    id: "decomposition",
    name: "Decomposition Prompting (Least-to-Most)",
    category: "Commonsense & Logical Reasoning",
    shortDescription: "Decomposes complex questions into simpler sub-questions answered sequentially.",
    strengths: [
      "Handles multi-hop reasoning",
      "Makes complex questions tractable",
      "Improves accuracy on compositional tasks",
    ],
    weaknesses: [
      "Decomposition errors propagate",
      "May lose context across sub-questions",
      "Overhead for straightforward queries",
    ],
  },
  {
    id: "ircot",
    name: "Iterative Retrieval + CoT (IRCoT)",
    category: "Commonsense & Logical Reasoning",
    shortDescription: "Interleaves retrieval steps with chain-of-thought reasoning for knowledge-intensive tasks.",
    strengths: [
      "Grounds reasoning in retrieved facts",
      "Reduces hallucination in knowledge tasks",
      "Adapts retrieval to reasoning needs",
    ],
    weaknesses: ["Dependent on retrieval quality", "Retrieval latency adds up", "Complex pipeline to orchestrate"],
  },
  {
    id: "lot",
    name: "Logic-Augmented Prompting (LoT)",
    category: "Commonsense & Logical Reasoning",
    shortDescription: "Incorporates formal logic structures into prompting to enhance logical reasoning capabilities.",
    strengths: ["Improves logical consistency", "Handles deductive reasoning well", "Reduces contradictions in output"],
    weaknesses: [
      "Requires logical formalization",
      "May be rigid for fuzzy problems",
      "Added complexity in prompt design",
    ],
  },
  {
    id: "neuro-symbolic",
    name: "Hybrid Neuro-Symbolic Solvers",
    category: "Commonsense & Logical Reasoning",
    shortDescription: "Combines neural language models with symbolic reasoning engines for robust logical inference.",
    strengths: [
      "Best of both neural and symbolic worlds",
      "Provably correct logical inferences",
      "Handles complex rule-based reasoning",
    ],
    weaknesses: ["Complex system integration", "Symbol grounding challenges", "May require domain-specific solvers"],
  },

  // Multi-Modal Reasoning
  {
    id: "multimodal-cot",
    name: "Multimodal Chain-of-Thought",
    category: "Multi-Modal Reasoning",
    shortDescription: "Extends chain-of-thought reasoning to vision-language tasks with step-by-step visual analysis.",
    strengths: [
      "Improves visual question answering",
      "Makes visual reasoning interpretable",
      "Handles complex image-text tasks",
    ],
    weaknesses: [
      "Requires multimodal model capabilities",
      "Visual reasoning steps can be imprecise",
      "Increases response latency",
    ],
  },
  {
    id: "palm-e",
    name: "Embodied Multimodal Models (PaLM-E-style)",
    category: "Multi-Modal Reasoning",
    shortDescription: "Integrates vision, language, and embodied reasoning for robotics and real-world task planning.",
    strengths: [
      "Enables real-world robotic applications",
      "Transfers knowledge across modalities",
      "Handles complex embodied tasks",
    ],
    weaknesses: [
      "Requires specialized training",
      "Computationally very expensive",
      "Limited to specific embodied domains",
    ],
  },
  {
    id: "tool-visual",
    name: "Tool-Augmented Visual Reasoning",
    category: "Multi-Modal Reasoning",
    shortDescription: "Uses external vision tools (OCR, object detection, etc.) to augment LLM visual reasoning.",
    strengths: [
      "Leverages specialized vision models",
      "Improves accuracy on specific visual tasks",
      "Modular and extensible",
    ],
    weaknesses: ["Pipeline complexity", "Tool integration overhead", "Errors can compound across tools"],
  },
  {
    id: "vlm-cot",
    name: "Large Vision-Language Models with CoT",
    category: "Multi-Modal Reasoning",
    shortDescription: "State-of-the-art VLMs prompted with chain-of-thought for complex visual understanding tasks.",
    strengths: [
      "End-to-end multimodal reasoning",
      "Strong performance on visual benchmarks",
      "Unified architecture simplicity",
    ],
    weaknesses: [
      "Large model size and compute needs",
      "May hallucinate visual details",
      "Training data biases in visual understanding",
    ],
  },
]

export function getMethodsByCategory(category: ReasoningCategory): ReasoningMethodData[] {
  return REASONING_METHODS.filter((method) => method.category === category)
}

export function getMethodById(id: string): ReasoningMethodData | undefined {
  return REASONING_METHODS.find((method) => method.id === id)
}
