export type IndustryFaqItem = {
  slug: string
  title: string
  description: string
  faqs: { question: string; answer: string }[]
}

export const industryFaqs: IndustryFaqItem[] = [
  {
    slug: "legal",
    title: "Legal AI FAQ",
    description: "Common questions about AI orchestration for legal teams.",
    faqs: [
      {
        question: "Is LLMHive suitable for legal research?",
        answer:
          "Yes. LLMHive routes legal research to high-accuracy models and supports governance for sensitive workflows.",
      },
      {
        question: "Can LLMHive help with contract review?",
        answer:
          "LLMHive supports routing and analysis workflows for contract review and summarization.",
      },
      {
        question: "How does LLMHive handle compliance?",
        answer:
          "LLMHive provides enterprise controls and auditability to support compliance requirements.",
      },
      {
        question: "Does LLMHive support case law analysis?",
        answer:
          "Yes. LLMHive routes complex legal analysis to reasoning-optimized models.",
      },
      {
        question: "Can LLMHive help with legal drafting?",
        answer:
          "Yes. LLMHive supports drafting workflows and model routing for higher accuracy.",
      },
      {
        question: "Is LLMHive secure for privileged data?",
        answer:
          "Enterprise plans include access controls and audit logs to protect sensitive legal data.",
      },
      {
        question: "Can LLMHive integrate with legal document systems?",
        answer:
          "Yes. LLMHive integrates via API with document repositories and knowledge bases.",
      },
      {
        question: "How does LLMHive reduce review time?",
        answer:
          "LLMHive routes tasks to optimal models and supports parallel evaluation to improve efficiency.",
      },
      {
        question: "Can LLMHive provide citations?",
        answer:
          "LLMHive supports RAG workflows and citation-ready outputs when connected to sources.",
      },
      {
        question: "Does LLMHive support multi-jurisdiction workflows?",
        answer:
          "Yes. Multi-model routing helps adapt to jurisdictional complexity and task type.",
      },
    ],
  },
  {
    slug: "finance",
    title: "Finance AI FAQ",
    description: "Common questions about AI orchestration for finance teams.",
    faqs: [
      {
        question: "Is LLMHive accurate for financial analysis?",
        answer:
          "LLMHive routes finance tasks to models optimized for precision and reasoning.",
      },
      {
        question: "Can LLMHive support reporting workflows?",
        answer:
          "Yes. LLMHive supports analysis, reporting, and data synthesis with routing controls.",
      },
      {
        question: "Does LLMHive provide governance for finance?",
        answer:
          "Enterprise plans include governance, audit logs, and usage visibility.",
      },
      {
        question: "Can LLMHive analyze earnings and filings?",
        answer:
          "Yes. LLMHive routes document analysis to high-accuracy models and supports RAG workflows.",
      },
      {
        question: "Does LLMHive support forecasting workflows?",
        answer:
          "LLMHive supports scenario analysis and routing to models suited for forecasting tasks.",
      },
      {
        question: "How does LLMHive control AI costs in finance?",
        answer:
          "LLMHive selects the lowest-cost model that meets the quality threshold for each task.",
      },
      {
        question: "Can LLMHive integrate with finance data sources?",
        answer:
          "Yes. LLMHive integrates with data sources via API for RAG and analysis.",
      },
      {
        question: "Is LLMHive suitable for risk analysis?",
        answer:
          "Yes. LLMHive routes risk analysis to models optimized for reasoning and precision.",
      },
      {
        question: "Does LLMHive support auditability?",
        answer:
          "Enterprise plans include audit logs and usage visibility for governance.",
      },
      {
        question: "Can LLMHive standardize reporting across teams?",
        answer:
          "Yes. Model routing and templates help produce consistent reporting outputs.",
      },
    ],
  },
  {
    slug: "healthcare",
    title: "Healthcare AI FAQ",
    description: "Common questions about AI orchestration for healthcare teams.",
    faqs: [
      {
        question: "Can LLMHive support clinical documentation?",
        answer:
          "Yes. LLMHive routes clinical tasks to models optimized for accuracy and compliance.",
      },
      {
        question: "Does LLMHive support research workflows?",
        answer:
          "LLMHive supports RAG and knowledge base workflows for healthcare research.",
      },
      {
        question: "Is LLMHive secure for healthcare data?",
        answer:
          "LLMHive provides enterprise-grade controls and governance for sensitive data.",
      },
      {
        question: "Can LLMHive assist with clinical summaries?",
        answer:
          "Yes. LLMHive routes summarization tasks to high-accuracy models.",
      },
      {
        question: "Does LLMHive support medical terminology?",
        answer:
          "Yes. LLMHive includes domain packs that optimize medical vocabulary.",
      },
      {
        question: "Can LLMHive integrate with EHR systems?",
        answer:
          "LLMHive integrates via API and can connect to healthcare data sources.",
      },
      {
        question: "Is LLMHive suitable for compliance workflows?",
        answer:
          "Enterprise controls and audit logs support compliance requirements.",
      },
      {
        question: "Can LLMHive reduce documentation time?",
        answer:
          "Yes. Routing and automation reduce manual effort while preserving accuracy.",
      },
      {
        question: "Does LLMHive support patient education content?",
        answer:
          "Yes. LLMHive routes content tasks to models optimized for clarity and tone.",
      },
      {
        question: "Can LLMHive support operational workflows?",
        answer:
          "Yes. LLMHive supports routing for ops and administrative tasks.",
      },
    ],
  },
  {
    slug: "support",
    title: "Customer Support AI FAQ",
    description: "Common questions about AI orchestration for support teams.",
    faqs: [
      {
        question: "Can LLMHive integrate with support platforms?",
        answer:
          "Yes. LLMHive integrates via API with ticketing and support tools.",
      },
      {
        question: "Will LLMHive reduce escalations?",
        answer:
          "LLMHive routes support tasks to the best model and integrates knowledge bases for accuracy.",
      },
      {
        question: "How does LLMHive control costs?",
        answer:
          "LLMHive selects the most cost-effective model that meets quality requirements.",
      },
      {
        question: "Does LLMHive support multilingual support?",
        answer:
          "Yes. LLMHive routes translation and multilingual tasks to appropriate models.",
      },
      {
        question: "Can LLMHive use knowledge bases for accuracy?",
        answer:
          "Yes. LLMHive supports RAG workflows with knowledge bases.",
      },
      {
        question: "Does LLMHive improve response time?",
        answer:
          "Yes. Routing to fast models reduces time-to-first-response.",
      },
      {
        question: "Can LLMHive enforce support policies?",
        answer:
          "Enterprise controls allow policy enforcement and governance.",
      },
      {
        question: "Is LLMHive suitable for enterprise support teams?",
        answer:
          "Yes. LLMHive provides governance, analytics, and routing at scale.",
      },
      {
        question: "Can LLMHive integrate with CRM data?",
        answer:
          "Yes. LLMHive integrates via API with CRM and support systems.",
      },
      {
        question: "Does LLMHive reduce agent workload?",
        answer:
          "Yes. Automation and routing reduce manual effort and improve consistency.",
      },
    ],
  },
  {
    slug: "saas",
    title: "SaaS AI FAQ",
    description: "Common questions about AI orchestration for SaaS teams.",
    faqs: [
      {
        question: "Can LLMHive help with onboarding workflows?",
        answer:
          "Yes. LLMHive supports onboarding content, support automation, and product workflows.",
      },
      {
        question: "Does LLMHive integrate with SaaS tools?",
        answer:
          "LLMHive integrates via API to connect with SaaS platforms and data sources.",
      },
      {
        question: "Is LLMHive suitable for cross-team use?",
        answer:
          "Yes. LLMHive provides governance and model routing across teams.",
      },
      {
        question: "Can LLMHive improve product adoption?",
        answer:
          "Yes. LLMHive supports onboarding guidance and product education workflows.",
      },
      {
        question: "Does LLMHive support sales enablement?",
        answer:
          "Yes. LLMHive can route sales and enablement tasks to optimal models.",
      },
      {
        question: "Can LLMHive integrate with analytics tools?",
        answer:
          "Yes. LLMHive can integrate via API with analytics platforms.",
      },
      {
        question: "Is LLMHive suitable for scaling operations?",
        answer:
          "Yes. LLMHive supports routing and governance for growing teams.",
      },
      {
        question: "Does LLMHive support customer success workflows?",
        answer:
          "Yes. LLMHive can route customer success tasks to optimal models.",
      },
      {
        question: "Can LLMHive reduce AI tooling sprawl?",
        answer:
          "Yes. LLMHive centralizes AI usage across teams and tools.",
      },
      {
        question: "Does LLMHive provide usage analytics?",
        answer:
          "Enterprise plans include visibility and analytics for usage governance.",
      },
    ],
  },
]
