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
    title: "Legal Ops: Contract Review Acceleration",
    slug: "legal-ops-contract-review",
    industry: "Legal",
    summary:
      "A legal operations team standardized contract review with multi-model routing and governance.",
    challenge:
      "The team needed faster turnaround without sacrificing accuracy or compliance review steps.",
    solution:
      "LLMHive routed drafting, clause extraction, and risk scoring to specialized models with audit trails.",
    highlights: [
      "Routing policies for sensitive clauses",
      "Automated redline summaries",
      "Centralized audit logs for compliance review",
    ],
    outcomes: [
      "Shorter contract review cycles",
      "Improved consistency across reviewers",
      "Reduced rework from missed clauses",
    ],
    metrics: ["42% faster review time", "28% fewer escalations", "99% audit-ready logs"],
    timeline: ["Week 1: workflow mapping", "Week 2: model routing setup", "Week 4: rollout"],
    faq: [
      {
        question: "How were sensitive documents handled?",
        answer:
          "Routing policies restricted model access and enforced audit logging for every task.",
      },
      {
        question: "Did the team replace existing tools?",
        answer:
          "No. LLMHive connected to existing document systems and added orchestration on top.",
      },
    ],
  },
  {
    title: "Finance: Analyst Reporting at Scale",
    slug: "finance-analyst-reporting",
    industry: "Finance",
    summary:
      "A finance team automated recurring analysis with deterministic routing and governance controls.",
    challenge:
      "Analysts were spending too much time on repetitive reporting with inconsistent outputs.",
    solution:
      "LLMHive routed forecasting, narrative generation, and validation checks to role-optimized models.",
    highlights: [
      "Model allowlists for regulated outputs",
      "Automated variance explanations",
      "Consistent reporting templates",
    ],
    outcomes: [
      "Faster monthly reporting cycles",
      "Higher confidence in narrative quality",
      "Reduced manual QA hours",
    ],
    metrics: ["35% faster close cycles", "22% reduction in QA time", "100% traceable outputs"],
    timeline: ["Week 1: data source alignment", "Week 3: routing policy setup", "Week 6: expand to full team"],
    faq: [
      {
        question: "How did compliance teams validate outputs?",
        answer:
          "Audit logs and routing policies ensured outputs were reviewable and traceable.",
      },
      {
        question: "Were reports still customizable?",
        answer:
          "Yes. Analysts kept control of templates and prompt parameters.",
      },
    ],
  },
  {
    title: "Healthcare: Clinical Summaries with Governance",
    slug: "healthcare-clinical-summaries",
    industry: "Healthcare",
    summary:
      "A healthcare provider reduced documentation time while maintaining compliance controls.",
    challenge:
      "Clinicians needed faster documentation workflows without risking compliance issues.",
    solution:
      "LLMHive routed transcription, summarization, and coding suggestions through compliant workflows.",
    highlights: [
      "HIPAA-aligned routing policies",
      "Clinical template enforcement",
      "Human-in-the-loop review steps",
    ],
    outcomes: [
      "More time for patient care",
      "Higher consistency in documentation",
      "Clear audit trails for compliance",
    ],
    metrics: ["31% reduction in documentation time", "18% fewer revisions", "100% policy adherence"],
    timeline: ["Week 1: workflow discovery", "Week 2: routing policy design", "Week 5: staged deployment"],
    faq: [
      {
        question: "How was data governance handled?",
        answer:
          "LLMHive enforced routing rules and access controls for protected health information.",
      },
      {
        question: "Could clinicians override summaries?",
        answer:
          "Yes. Clinicians retained final approval with edit controls.",
      },
    ],
  },
  {
    title: "Support: Tier-1 Deflection with Quality Controls",
    slug: "support-tier1-deflection",
    industry: "Support",
    summary:
      "A support organization improved response quality while deflecting tier-1 tickets.",
    challenge:
      "Support agents needed consistent answers with minimal escalation risks.",
    solution:
      "LLMHive routed ticket summaries and responses to the best model with knowledge base context.",
    highlights: [
      "Knowledge base grounding for responses",
      "Escalation triggers for low-confidence outputs",
      "Quality checks by ticket category",
    ],
    outcomes: [
      "Higher first-contact resolution",
      "Lower backlog of repeat questions",
      "Reduced escalation volume",
    ],
    metrics: ["26% higher FCR", "19% fewer escalations", "30% faster response time"],
    timeline: ["Week 1: knowledge base ingestion", "Week 2: routing setup", "Week 4: production rollout"],
    faq: [
      {
        question: "How were low-confidence responses handled?",
        answer:
          "LLMHive triggered escalations and routed the ticket to senior agents.",
      },
      {
        question: "Did this change agent workflows?",
        answer:
          "Agents kept their tools while LLMHive handled drafting and routing.",
      },
    ],
  },
  {
    title: "SaaS: Product Enablement at Enterprise Scale",
    slug: "saas-product-enablement",
    industry: "SaaS",
    summary:
      "A SaaS organization standardized enablement across teams with multi-model orchestration.",
    challenge:
      "Teams needed consistent enablement content and insights across product lines.",
    solution:
      "LLMHive routed onboarding, release notes, and training content to specialized models.",
    highlights: [
      "Cross-team content governance",
      "Release note automation",
      "Role-specific enablement templates",
    ],
    outcomes: [
      "Faster onboarding cycles",
      "More consistent product messaging",
      "Reduced manual content overhead",
    ],
    metrics: ["40% faster onboarding", "25% reduction in content creation time", "Unified enablement playbooks"],
    timeline: ["Week 1: content audit", "Week 3: routing setup", "Week 6: global enablement rollout"],
    faq: [
      {
        question: "How was content quality ensured?",
        answer:
          "LLMHive enforced templates and routed outputs through evaluation checks.",
      },
      {
        question: "Could teams customize outputs?",
        answer:
          "Yes. Teams could adapt templates while keeping governance rules intact.",
      },
    ],
  },
]
