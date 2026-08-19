export type NoCardCampaignLandingConfig = {
  slug: string
  campaignPath: string
  analyticsSource: string
  autocoStoragePrefix: string
  billingToggleId: string
  heroImageSrc: string
  heroImageAlt: string
  metaTitle: string
  metaDescription: string
}

export const NO_CARD_CAMPAIGN_LANDINGS: NoCardCampaignLandingConfig[] = [
  {
    slug: "350-models-free",
    campaignPath: "/landing/350-models-free",
    analyticsSource: "landing_350_models_free",
    autocoStoragePrefix: "llmhive_350_models_free_autoco_v1",
    billingToggleId: "billing-toggle-350-models-free",
    heroImageSrc: "/campaigns/hero-free/350-models-one-platform.png",
    heroImageAlt: "350+ AI models in one platform — LLMHive",
    metaTitle: "LLMHive — 350+ AI models, one platform",
    metaDescription:
      "ChatGPT, Claude, Gemini, Grok, and hundreds more in one place. Start a 7-day Standard free trial ($0 today, no card required).",
  },
  {
    slug: "one-platform-free",
    campaignPath: "/landing/one-platform-free",
    analyticsSource: "landing_one_platform_free",
    autocoStoragePrefix: "llmhive_one_platform_free_autoco_v1",
    billingToggleId: "billing-toggle-one-platform-free",
    heroImageSrc: "/campaigns/hero-free/one-platform-less-switching.png",
    heroImageAlt: "One AI platform — less switching, less spending",
    metaTitle: "LLMHive — One AI platform, less switching",
    metaDescription:
      "350+ AI models from $10/month. Start a 7-day Standard free trial ($0 today, no card required).",
  },
  {
    slug: "one-question-free",
    campaignPath: "/landing/one-question-free",
    analyticsSource: "landing_one_question_free",
    autocoStoragePrefix: "llmhive_one_question_free_autoco_v1",
    billingToggleId: "billing-toggle-one-question-free",
    heroImageSrc: "/campaigns/hero-free/stop-asking-five-times.png",
    heroImageAlt: "Stop asking the same question five times — ask LLMHive once",
    metaTitle: "LLMHive — One question, one refined answer",
    metaDescription:
      "Compare AI responses behind the scenes and get one refined answer. 7-day Standard free trial, no card required.",
  },
  {
    slug: "which-ai-free",
    campaignPath: "/landing/which-ai-free",
    analyticsSource: "landing_which_ai_free",
    autocoStoragePrefix: "llmhive_which_ai_free_autoco_v1",
    billingToggleId: "billing-toggle-which-ai-free",
    heroImageSrc: "/campaigns/hero-free/which-ai-should-you-use.png",
    heroImageAlt: "Which AI should you use? LLMHive picks the best model",
    metaTitle: "LLMHive — Which AI should you use?",
    metaDescription:
      "Let LLMHive select the best AI models for every question. 7-day Standard free trial ($0 today, no card required).",
  },
  {
    slug: "stop-paying-free",
    campaignPath: "/landing/stop-paying-free",
    analyticsSource: "landing_stop_paying_free",
    autocoStoragePrefix: "llmhive_stop_paying_free_autoco_v1",
    billingToggleId: "billing-toggle-stop-paying-free",
    heroImageSrc: "/campaigns/hero-free/stop-paying-multiple-subscriptions.png",
    heroImageAlt: "Stop paying for multiple AI subscriptions",
    metaTitle: "LLMHive — Stop paying for multiple AI subscriptions",
    metaDescription:
      "350+ AI models from $10/month instead of stacked subscriptions. 7-day Standard free trial, no card required.",
  },
]

export function getNoCardCampaignLanding(slug: string): NoCardCampaignLandingConfig | undefined {
  return NO_CARD_CAMPAIGN_LANDINGS.find((entry) => entry.slug === slug)
}
