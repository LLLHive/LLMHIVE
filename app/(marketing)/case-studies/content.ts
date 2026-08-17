export type CaseStudy = {
  title: string
  slug: string
  industry: string
  summary: string
  challenge: string
  solution: string
  highlights: string[]
  outcomes: string[]
  metrics: string[]
  timeline: string[]
  faq: { question: string; answer: string }[]
}

export const caseStudies: CaseStudy[] = [
  {
    title: "Legal Ops: Contract Review Workflows",
    slug: "legal-ops-contract-review",
    industry: "Legal",
    summary:
      "Example workflow for routing contract drafting, clause extraction, and risk notes through LLMHive with audit logs.",
    challenge:
      "Legal teams often need faster review without losing a record of what was asked and which model answered.",
    solution:
      "LLMHive can route drafting, clause extraction, and risk scoring to specialized models and keep task-level logs.",
    highlights: [
      "Routing policies for sensitive clauses",
      "Redline and summary drafts in one chat",
      "Audit logs for compliance review",
    ],
    outcomes: [
      "One interface instead of switching models by hand",
      "Consistent templates for reviewers",
      "A recorded trail of routing and outputs",
    ],
    metrics: [],
    timeline: ["Week 1: workflow mapping", "Week 2: model routing setup", "Week 4: rollout"],
    faq: [
      {
        question: "How were sensitive documents handled?",
        answer:
          "Routing policies can restrict model access and keep audit logging for every task.",
      },
      {
        question: "Did the team replace existing tools?",
        answer:
          "No. LLMHive can sit alongside existing document systems and add orchestration on top.",
      },
    ],
  },
  {
    title: "Finance: Analyst Reporting Workflows",
    slug: "finance-analyst-reporting",
    industry: "Finance",
    summary:
      "Example workflow for recurring analysis with model allowlists, templates, and reviewable outputs.",
    challenge:
      "Analysts often spend time on repetitive reporting where model choice and wording drift from cycle to cycle.",
    solution:
      "LLMHive can route forecasting, narrative generation, and validation checks to role-optimized models with templates.",
    highlights: [
      "Model allowlists for regulated outputs",
      "Automated variance explanations",
      "Consistent reporting templates",
    ],
    outcomes: [
      "Repeatable reporting templates",
      "Reviewable routing for each report",
      "Less manual switching between model vendors",
    ],
    metrics: [],
    timeline: ["Week 1: data source alignment", "Week 3: routing policy setup", "Week 6: expand to full team"],
    faq: [
      {
        question: "How did compliance teams validate outputs?",
        answer:
          "Audit logs and routing policies make outputs reviewable and traceable.",
      },
      {
        question: "Were reports still customizable?",
        answer:
          "Yes. Analysts keep control of templates and prompt parameters.",
      },
    ],
  },
  {
    title: "Healthcare: Clinical Summary Workflows",
    slug: "healthcare-clinical-summaries",
    industry: "Healthcare",
    summary:
      "Example workflow for documentation drafts with templates, human review, and logged routing. LLMHive is not a certified HIPAA product.",
    challenge:
      "Clinicians often need faster documentation drafts while keeping a human in the loop.",
    solution:
      "LLMHive can route transcription, summarization, and coding suggestions through templates with a required reviewer step.",
    highlights: [
      "Human-in-the-loop review steps",
      "Clinical template enforcement",
      "Access controls and audit logs",
    ],
    outcomes: [
      "Drafts that clinicians can edit before use",
      "More consistent documentation templates",
      "A logged record of routing and edits",
    ],
    metrics: [],
    timeline: ["Week 1: workflow discovery", "Week 2: routing policy design", "Week 5: staged deployment"],
    faq: [
      {
        question: "How was data governance handled?",
        answer:
          "LLMHive can enforce routing rules and access controls. This example is not a claim of HIPAA certification.",
      },
      {
        question: "Could clinicians override summaries?",
        answer:
          "Yes. Clinicians retain final approval with edit controls.",
      },
    ],
  },
  {
    title: "Support: Tier-1 Drafting Workflows",
    slug: "support-tier1-deflection",
    industry: "Support",
    summary:
      "Example workflow for ticket summaries and reply drafts with knowledge-base grounding and escalation routing.",
    challenge:
      "Support agents often need consistent drafts without sending low-confidence answers to customers.",
    solution:
      "LLMHive can route ticket summaries and responses with knowledge-base context and hand off low-confidence work.",
    highlights: [
      "Knowledge base grounding for responses",
      "Escalation triggers for low-confidence outputs",
      "Quality checks by ticket category",
    ],
    outcomes: [
      "Draft replies in the agent's existing tools",
      "A path to escalate weak answers",
      "One routing layer for common ticket types",
    ],
    metrics: [],
    timeline: ["Week 1: knowledge base ingestion", "Week 2: routing setup", "Week 4: production rollout"],
    faq: [
      {
        question: "How were low-confidence responses handled?",
        answer:
          "LLMHive can trigger escalations and route the ticket to senior agents.",
      },
      {
        question: "Did this change agent workflows?",
        answer:
          "Agents can keep their tools while LLMHive handles drafting and routing.",
      },
    ],
  },
  {
    title: "SaaS: Product Enablement Workflows",
    slug: "saas-product-enablement",
    industry: "SaaS",
    summary:
      "Example workflow for onboarding copy, release notes, and training drafts with shared templates.",
    challenge:
      "Teams often need consistent enablement content across product lines without a new tool per team.",
    solution:
      "LLMHive can route onboarding, release notes, and training content to specialized models with shared templates.",
    highlights: [
      "Cross-team content templates",
      "Release note drafts",
      "Role-specific enablement prompts",
    ],
    outcomes: [
      "Shared templates across teams",
      "More consistent product messaging",
      "Less manual switching between AI vendors",
    ],
    metrics: [],
    timeline: ["Week 1: content audit", "Week 3: routing setup", "Week 6: global enablement rollout"],
    faq: [
      {
        question: "How was content quality ensured?",
        answer:
          "LLMHive can enforce templates and route outputs through review steps.",
      },
      {
        question: "Could teams customize outputs?",
        answer:
          "Yes. Teams can adapt templates while keeping governance rules intact.",
      },
    ],
  },
]
