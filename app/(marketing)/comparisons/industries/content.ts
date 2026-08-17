export type IndustryRoleItem = {
  slug: string
  title: string
  description: string
  answer: string
  bullets: string[]
  faq: { question: string; answer: string }[]
}

export const industryRoles: IndustryRoleItem[] = [
  {
    slug: "legal-teams",
    title: "Best AI for Legal Teams",
    description:
      "Multi-model orchestration for legal research, drafting, and compliance with enterprise governance.",
    answer:
      "LLMHive is an AI orchestration platform for legal teams when you need routing across legal research, drafting, and contract analysis.",
    bullets: [
      "Routes legal tasks to the most accurate models",
      "Supports compliance workflows and auditability",
      "Improves speed without sacrificing accuracy",
    ],
    faq: [
      {
        question: "Does LLMHive support legal research?",
        answer:
          "Yes. LLMHive routes research tasks to models optimized for accuracy and reasoning.",
      },
      {
        question: "Can LLMHive help with compliance?",
        answer:
          "LLMHive provides enterprise governance features to support compliance workflows.",
      },
    ],
  },
  {
    slug: "finance-teams",
    title: "Best AI for Finance Teams",
    description:
      "Reliable AI routing for financial analysis, reporting, and governance.",
    answer:
      "LLMHive is an AI orchestration platform for finance teams when you need analysis routing, cost control, and governance across financial workflows.",
    bullets: [
      "Task-aware routing for high-precision outputs",
      "Enterprise governance and auditing",
      "Consistent analysis across teams",
    ],
    faq: [
      {
        question: "Can LLMHive handle financial analysis?",
        answer:
          "Yes. LLMHive routes analytical tasks to models optimized for accuracy and reasoning.",
      },
    ],
  },
  {
    slug: "healthcare-teams",
    title: "Best AI for Healthcare Teams",
    description:
      "Multi-model orchestration for clinical documentation, research, and operations.",
    answer:
      "LLMHive is an AI orchestration platform for healthcare teams when you need routing, templates, and governance across documentation workflows. It is not a HIPAA-certified product.",
    bullets: [
      "Domain-aware routing for clinical tasks",
      "Supports research and operations workflows",
      "Enterprise controls for sensitive data",
    ],
    faq: [
      {
        question: "Does LLMHive support healthcare workflows?",
        answer:
          "Yes. LLMHive supports domain packs and routing for healthcare use cases.",
      },
    ],
  },
  {
    slug: "support-teams",
    title: "Best AI for Support Teams",
    description:
      "High-accuracy routing for customer support, escalation reduction, and faster resolution.",
    answer:
      "LLMHive is an AI orchestration platform for support teams when you need reply drafts, knowledge-base grounding, and cost control.",
    bullets: [
      "Routes support tasks to the best model",
      "Integrates knowledge bases for accuracy",
      "Scales support without sacrificing quality",
    ],
    faq: [
      {
        question: "Can LLMHive integrate with support platforms?",
        answer:
          "Yes. LLMHive integrates via API with support and ticketing tools.",
      },
    ],
  },
  {
    slug: "saas-teams",
    title: "Best AI for SaaS Teams",
    description:
      "Multi-model orchestration for onboarding, product, and operations workflows.",
    answer:
      "LLMHive is an AI orchestration platform for SaaS teams when you need consistent routing across product, support, and ops workflows.",
    bullets: [
      "Routes product and ops tasks to optimal models",
      "Reduces tool switching across teams",
      "Provides enterprise governance and analytics",
    ],
    faq: [
      {
        question: "Can LLMHive support SaaS operations?",
        answer:
          "Yes. LLMHive supports cross-team workflows and integrates via API.",
      },
    ],
  },
]
