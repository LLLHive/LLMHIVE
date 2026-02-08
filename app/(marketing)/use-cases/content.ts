export type UseCaseItem = {
  slug: string
  title: string
  description: string
  answer: string
  outcomes: string[]
  sections: { title: string; points: string[] }[]
  faq: { question: string; answer: string }[]
}

export const useCases: UseCaseItem[] = [
  {
    slug: "enterprise-ai",
    title: "Enterprise AI Orchestration",
    description:
      "Unify AI usage across teams with governance, routing transparency, and cost controls.",
    answer:
      "LLMHive centralizes AI operations so enterprises can route each request to the best model while maintaining compliance and visibility across teams.",
    outcomes: [
      "Consistent quality across departments",
      "Centralized governance and auditability",
      "Reduced AI spend with task-aware routing",
    ],
    sections: [
      {
        title: "Governance",
        points: [
          "SSO, access control, and audit logs",
          "Centralized policy enforcement across models",
          "Usage analytics for leadership visibility",
        ],
      },
      {
        title: "Routing Quality",
        points: [
          "Best model per task selection",
          "Multi-model evaluation for critical tasks",
          "Consistent outcomes across teams",
        ],
      },
    ],
    faq: [
      {
        question: "Is LLMHive compliant for enterprise use?",
        answer:
          "LLMHive supports enterprise-grade security and governance. Contact sales for compliance requirements.",
      },
    ],
  },
  {
    slug: "engineering-and-product",
    title: "Engineering & Product",
    description:
      "Route coding, analysis, and product research to the best model automatically.",
    answer:
      "LLMHive delivers higher code quality and faster product insights by selecting the optimal model for each engineering and product task.",
    outcomes: [
      "Higher-quality code and reviews",
      "Faster product research cycles",
      "Reduced model switching",
    ],
    sections: [
      {
        title: "Coding Quality",
        points: [
          "Model routing optimized for coding tasks",
          "Consistent results across languages",
          "Tooling support for verification and analysis",
        ],
      },
      {
        title: "Product Research",
        points: [
          "Model selection based on task complexity",
          "RAG support for internal documentation",
          "Reliable outputs for decision-making",
        ],
      },
    ],
    faq: [
      {
        question: "Does LLMHive support code review workflows?",
        answer:
          "Yes. LLMHive routes code tasks to the models best suited for accuracy and reasoning.",
      },
    ],
  },
  {
    slug: "research-and-knowledge",
    title: "Research & Knowledge Work",
    description:
      "Improve accuracy with multi-model routing and RAG-ready workflows.",
    answer:
      "LLMHive enables research teams to retrieve accurate context and route tasks to the best model for deep analysis and synthesis.",
    outcomes: [
      "Higher accuracy and fewer hallucinations",
      "Faster synthesis of complex sources",
      "Enterprise-grade knowledge workflows",
    ],
    sections: [
      {
        title: "RAG Workflows",
        points: [
          "Connect knowledge bases and data sources",
          "Route to models optimized for retrieval tasks",
          "Maintain citations and traceability",
        ],
      },
      {
        title: "Analysis",
        points: [
          "Use reasoning models for synthesis",
          "Balance speed and depth based on task",
          "Improve reliability across domains",
        ],
      },
    ],
    faq: [
      {
        question: "Does LLMHive support RAG?",
        answer:
          "Yes. LLMHive supports retrieval-augmented generation and knowledge bases.",
      },
    ],
  },
  {
    slug: "marketing-and-content",
    title: "Marketing & Content",
    description:
      "Generate high-quality content with multi-model routing and brand-safe workflows.",
    answer:
      "LLMHive routes content tasks to the best model for tone, creativity, and compliance while keeping quality consistent across campaigns.",
    outcomes: [
      "Higher content quality",
      "Faster campaign execution",
      "Consistent brand voice",
    ],
    sections: [
      {
        title: "Content Quality",
        points: [
          "Model selection based on creative tasks",
          "Built-in formatting and refinement",
          "Consistent tone across assets",
        ],
      },
      {
        title: "Scale",
        points: [
          "Generate multiple variants quickly",
          "Reduce manual editing time",
          "Standardize workflows across teams",
        ],
      },
    ],
    faq: [
      {
        question: "Can LLMHive enforce brand guidelines?",
        answer:
          "Yes. LLMHive supports structured prompts and workflows to maintain brand consistency.",
      },
    ],
  },
  {
    slug: "customer-support",
    title: "Customer Support",
    description:
      "Automate support with multi-model routing and high accuracy for complex issues.",
    answer:
      "LLMHive improves support outcomes by routing tickets to the best model and integrating knowledge bases for accurate responses.",
    outcomes: [
      "Higher resolution accuracy",
      "Lower response times",
      "Better customer satisfaction",
    ],
    sections: [
      {
        title: "Resolution Quality",
        points: [
          "Select models optimized for support tasks",
          "Use RAG to reference internal docs",
          "Reduce escalation rates",
        ],
      },
      {
        title: "Efficiency",
        points: [
          "Automate repetitive questions",
          "Balance cost and quality automatically",
          "Scale support without adding headcount",
        ],
      },
    ],
    faq: [
      {
        question: "Can LLMHive integrate with support tools?",
        answer:
          "Yes. LLMHive integrates via API with support platforms and knowledge bases.",
      },
    ],
  },
]
