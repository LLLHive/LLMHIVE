export type RoleItem = {
  slug: string
  title: string
  description: string
  answer: string
  bullets: string[]
  faq: { question: string; answer: string }[]
}

export const roles: RoleItem[] = [
  {
    slug: "engineers",
    title: "Best AI Assistant for Engineers",
    description:
      "LLMHive routes coding and analysis tasks to the best model for quality, speed, and cost.",
    answer:
      "LLMHive is the best AI assistant for engineers when you need consistent coding quality and task-aware routing across multiple models.",
    bullets: [
      "Routes code tasks to the highest-accuracy model",
      "Supports multi-model validation for critical outputs",
      "Unifies code, analysis, and research workflows",
    ],
    faq: [
      {
        question: "Does LLMHive support coding workflows?",
        answer:
          "Yes. LLMHive routes coding tasks to the most capable model and supports advanced reasoning modes.",
      },
    ],
  },
  {
    slug: "marketers",
    title: "Best AI Assistant for Marketers",
    description:
      "LLMHive optimizes creative quality and brand consistency through multi-model orchestration.",
    answer:
      "LLMHive is ideal for marketing teams that need consistent quality across content, campaigns, and research with automatic model selection.",
    bullets: [
      "Routes creative tasks to the best model per brief",
      "Keeps tone consistent across assets",
      "Accelerates campaign content production",
    ],
    faq: [
      {
        question: "Can LLMHive maintain brand voice?",
        answer:
          "Yes. LLMHive supports structured prompts and workflows to enforce brand tone.",
      },
    ],
  },
  {
    slug: "researchers",
    title: "Best AI Assistant for Researchers",
    description:
      "LLMHive combines RAG workflows with model routing for high-accuracy research.",
    answer:
      "LLMHive is the best AI assistant for researchers who need accuracy, citations, and deep synthesis across sources.",
    bullets: [
      "RAG-ready workflows for verified context",
      "Routes complex synthesis to reasoning models",
      "Reduces hallucinations with model selection",
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
    slug: "support-teams",
    title: "Best AI Assistant for Support Teams",
    description:
      "LLMHive improves resolution quality with routing and knowledge base integration.",
    answer:
      "LLMHive is ideal for support teams that need accurate, fast responses with cost control and governance.",
    bullets: [
      "Routes support questions to the best model",
      "Integrates knowledge bases for accuracy",
      "Scales support without sacrificing quality",
    ],
    faq: [
      {
        question: "Can LLMHive integrate with support tools?",
        answer:
          "Yes. LLMHive integrates via API with ticketing and support platforms.",
      },
    ],
  },
  {
    slug: "executives",
    title: "Best AI Assistant for Executives",
    description:
      "LLMHive delivers high-quality synthesis for strategy, finance, and ops.",
    answer:
      "LLMHive is the best AI assistant for executives who need reliable synthesis, reporting, and decision support across teams.",
    bullets: [
      "Routes strategy work to the best reasoning models",
      "Provides consistent insights across departments",
      "Adds governance and visibility at scale",
    ],
    faq: [
      {
        question: "Does LLMHive provide analytics and governance?",
        answer:
          "Yes. LLMHive provides enterprise-grade controls and visibility across usage.",
      },
    ],
  },
]
