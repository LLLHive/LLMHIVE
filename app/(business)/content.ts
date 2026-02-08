type PageSection = {
  title: string
  description?: string
  items?: string[]
}

type PageContent = {
  title: string
  subtitle: string
  sections: PageSection[]
  ctaLabel?: string
  ctaHref?: string
}

export const businessPages: Record<string, PageContent> = {
  security: {
    title: "Security",
    subtitle:
      "Enterprise-grade security controls designed to protect customer data, model usage, and access across every tier.",
    sections: [
      {
        title: "Security Principles",
        items: [
          "Zero-trust access model with least-privilege policies.",
          "Encryption in transit and at rest for all customer data.",
          "Continuous vulnerability scanning and dependency monitoring.",
        ],
      },
      {
        title: "Infrastructure Controls",
        items: [
          "Isolated environments for production and evaluation workloads.",
          "Automated backup strategies and incident response playbooks.",
          "Strict audit logging with immutable retention options.",
        ],
      },
    ],
    ctaLabel: "Request Security Review",
    ctaHref: "/contact",
  },
  compliance: {
    title: "Compliance",
    subtitle:
      "Compliance readiness for regulated teams with documentation, controls, and audit trails.",
    sections: [
      {
        title: "Compliance Coverage",
        items: [
          "SOC 2 Type II controls mapped to operational practices.",
          "GDPR-aligned data handling and privacy obligations.",
          "Vendor risk management and third-party attestations.",
        ],
      },
      {
        title: "Governance",
        items: [
          "Policy ownership with quarterly reviews.",
          "Change management for model and infrastructure updates.",
          "Evidence collection for customer and regulator audits.",
        ],
      },
    ],
  },
  status: {
    title: "System Status",
    subtitle:
      "Live operational status across API, orchestration, and data services.",
    sections: [
      {
        title: "Status Coverage",
        items: [
          "Core API availability and latency targets.",
          "Model routing, orchestration, and tool service health.",
          "Planned maintenance windows and release notes.",
        ],
      },
      {
        title: "Incident Management",
        items: [
          "Automated alerting with dedicated on-call rotation.",
          "Customer-facing incident reports and timelines.",
          "Post-incident review with preventive actions.",
        ],
      },
    ],
  },
  sla: {
    title: "Service Level Agreement (SLA)",
    subtitle:
      "Clear uptime commitments and response time targets for mission-critical workloads.",
    sections: [
      {
        title: "Uptime Commitments",
        items: [
          "99.5% availability for ELITE orchestration.",
          "Service credit policy tied to monthly uptime.",
          "Transparent maintenance communications.",
        ],
      },
      {
        title: "Support Response",
        items: [
          "Priority response paths for enterprise teams.",
          "Escalation SLAs for high-severity incidents.",
          "Dedicated technical account ownership.",
        ],
      },
    ],
  },
  changelog: {
    title: "Changelog",
    subtitle:
      "Track product releases, model updates, and security improvements.",
    sections: [
      {
        title: "Release Notes",
        items: [
          "Model routing improvements and new providers.",
          "Benchmark upgrades and evaluation pipeline changes.",
          "UI enhancements and workflow improvements.",
        ],
      },
      {
        title: "Security Updates",
        items: [
          "Dependency patches and runtime hardening.",
          "Audit log expansion and new admin controls.",
          "Compliance documentation refreshes.",
        ],
      },
    ],
  },
  roadmap: {
    title: "Roadmap",
    subtitle:
      "Planned investments to expand orchestration, enterprise controls, and automation.",
    sections: [
      {
        title: "Near Term",
        items: [
          "Advanced routing for multi-agent workflows.",
          "Expanded benchmarking coverage and reporting.",
          "New integrations for finance and CRM.",
        ],
      },
      {
        title: "Mid Term",
        items: [
          "Enterprise workflow automation and governance.",
          "Cost optimization recommendations at query level.",
          "Organization-wide analytics dashboards.",
        ],
      },
    ],
  },
  "press-kit": {
    title: "Press Kit",
    subtitle:
      "Brand assets, logos, and approved product messaging for media use.",
    sections: [
      {
        title: "Brand Assets",
        items: [
          "Primary and secondary logos in light/dark variants.",
          "Product screenshots and platform overview slides.",
          "Approved brand colors and typography guidelines.",
        ],
      },
      {
        title: "Media Resources",
        items: [
          "Company boilerplate and executive bios.",
          "Press-approved product positioning statements.",
          "Contact information for press inquiries.",
        ],
      },
    ],
    ctaLabel: "Contact Press",
    ctaHref: "/contact",
  },
  "responsible-ai": {
    title: "Responsible AI & Safety",
    subtitle:
      "Policies and safeguards for safe, trustworthy, and compliant AI usage.",
    sections: [
      {
        title: "Safety Controls",
        items: [
          "Tool-based verification for factual accuracy.",
          "Prompt and output guardrails for sensitive tasks.",
          "Human oversight recommendations for high-risk flows.",
        ],
      },
      {
        title: "Transparency",
        items: [
          "Clear disclosure of model usage and routing decisions.",
          "Risk assessments for new model integrations.",
          "Ongoing monitoring for drift and regressions.",
        ],
      },
    ],
  },
  dpa: {
    title: "Data Processing Addendum (DPA)",
    subtitle:
      "Contractual commitments on data handling, privacy, and subprocessors.",
    sections: [
      {
        title: "Data Handling",
        items: [
          "Customer data used only for service delivery.",
          "Retention controls aligned to subscription tiers.",
          "Subprocessor disclosure and contract flow-downs.",
        ],
      },
      {
        title: "Privacy Rights",
        items: [
          "Data access, correction, and deletion workflows.",
          "Regional data residency options where available.",
          "Incident notification timelines and obligations.",
        ],
      },
    ],
  },
  docs: {
    title: "Documentation",
    subtitle:
      "Guides, recipes, and onboarding workflows for LLMHive teams.",
    sections: [
      {
        title: "Getting Started",
        items: [
          "Account setup and API key management.",
          "First orchestration and routing workflow.",
          "Benchmarking and evaluation overview.",
        ],
      },
      {
        title: "Operational Guides",
        items: [
          "Monitoring, budgets, and usage limits.",
          "Team permissions and audit readiness.",
          "Incident response and escalation.",
        ],
      },
    ],
  },
  guides: {
    title: "Guides",
    subtitle:
      "Deep dives on orchestration strategies, integrations, and advanced workflows.",
    sections: [
      {
        title: "Orchestration Playbooks",
        items: [
          "Consensus workflows for high-stakes tasks.",
          "Tool augmentation for accuracy and verification.",
          "Cost-aware routing patterns.",
        ],
      },
      {
        title: "Integration Patterns",
        items: [
          "CRM enrichment pipelines.",
          "Finance operations with automated approvals.",
          "Customer support automation flows.",
        ],
      },
    ],
  },
  "api-reference": {
    title: "API Reference",
    subtitle:
      "Endpoint definitions, schemas, and response formats for LLMHive APIs.",
    sections: [
      {
        title: "Core APIs",
        items: [
          "Chat & orchestration endpoints.",
          "Usage and billing reporting.",
          "Model metadata and routing policies.",
        ],
      },
      {
        title: "Security",
        items: [
          "Authentication and API key rotation.",
          "Rate limits, quotas, and error handling.",
          "Audit logging and compliance hooks.",
        ],
      },
    ],
  },
  troubleshooting: {
    title: "Troubleshooting",
    subtitle:
      "Diagnostics and steps for resolving common platform issues.",
    sections: [
      {
        title: "Common Issues",
        items: [
          "Latency spikes or rate limiting.",
          "Model routing unexpected behavior.",
          "Integration failures and webhook retries.",
        ],
      },
      {
        title: "Support Escalation",
        items: [
          "Collect logs and request IDs.",
          "Open support tickets with severity tags.",
          "Engage on-call support for production incidents.",
        ],
      },
    ],
  },
  faq: {
    title: "FAQ",
    subtitle:
      "Frequently asked questions about LLMHive features, billing, and usage.",
    sections: [
      {
        title: "Product",
        items: [
          "How orchestration selects the right model.",
          "What happens after ELITE query limits.",
          "How to use tool verification features.",
        ],
      },
      {
        title: "Billing",
        items: [
          "Invoice delivery and payment schedules.",
          "Tax/VAT handling by region.",
          "How to upgrade or change plans.",
        ],
      },
    ],
  },
  "case-studies": {
    title: "Case Studies",
    subtitle:
      "Customer success stories showcasing measurable performance gains.",
    sections: [
      {
        title: "Operational Impact",
        items: [
          "Reduced support response times by 45%.",
          "Improved research accuracy with multi-model validation.",
          "Lowered AI spend by optimizing model routing.",
        ],
      },
      {
        title: "Industry Highlights",
        items: [
          "Finance: audit-ready compliance workflows.",
          "Healthcare: reliable summarization and QA.",
          "Retail: personalized engagement at scale.",
        ],
      },
    ],
  },
  testimonials: {
    title: "Testimonials",
    subtitle:
      "What teams say about LLMHive orchestration and reliability.",
    sections: [
      {
        title: "Customer Voice",
        items: [
          "“Our accuracy jumped while costs dropped.”",
          "“The orchestration layer simplified everything.”",
          "“The benchmarks proved ROI quickly.”",
        ],
      },
      {
        title: "Proof Points",
        items: [
          "Higher quality outputs in benchmarked tasks.",
          "Lower operational overhead with unified routing.",
          "Fast integration with existing workflows.",
        ],
      },
    ],
  },
  competitors: {
    title: "Competitor Comparisons",
    subtitle:
      "Side-by-side comparisons across benchmark categories and cost.",
    sections: [
      {
        title: "Benchmark Coverage",
        items: [
          "Industry-standard datasets and evaluation methods.",
          "Transparent scoring and cost per attempt.",
          "Reproducible results with strict mode.",
        ],
      },
      {
        title: "Why LLMHive",
        items: [
          "Multi-model orchestration beats single-model systems.",
          "Tool verification reduces hallucinations.",
          "Flexible tiers for teams and enterprises.",
        ],
      },
    ],
  },
  "roi-calculator": {
    title: "ROI Calculator",
    subtitle:
      "Estimate cost savings and productivity gains from LLMHive orchestration.",
    sections: [
      {
        title: "Inputs",
        items: [
          "Monthly query volume and average cost.",
          "Time saved per workflow.",
          "Projected error reduction.",
        ],
      },
      {
        title: "Outputs",
        items: [
          "Projected annual savings.",
          "Cost per successful outcome.",
          "Quality improvement benchmarks.",
        ],
      },
    ],
    ctaLabel: "Talk to Sales",
    ctaHref: "/contact",
  },
}
