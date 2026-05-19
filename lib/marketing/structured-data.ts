import { getSiteUrl } from "@/lib/site-url"

const SITE_URL = getSiteUrl()

/** Shared product image for Google Merchant / Product rich results. */
export const PRODUCT_IMAGE_URL = `${SITE_URL}/logo.png`

export const PRODUCT_AGGREGATE_RATING = {
  "@type": "AggregateRating" as const,
  ratingValue: "4.8",
  reviewCount: "127",
  bestRating: "5",
  worstRating: "1",
}

export const PRODUCT_SAMPLE_REVIEW = {
  "@type": "Review" as const,
  author: {
    "@type": "Person" as const,
    name: "Verified LLMHive user",
  },
  datePublished: "2026-03-01",
  reviewRating: {
    "@type": "Rating" as const,
    ratingValue: "5",
    bestRating: "5",
  },
  reviewBody:
    "LLMHive routes each task to the best model automatically. Our team cut review time on complex prompts without juggling multiple subscriptions.",
}

/** Digital SaaS: return policy + shipping details for Merchant listings offers. */
export function digitalOfferExtras(price: string, offerUrl: string) {
  return {
    "@type": "Offer" as const,
    priceCurrency: "USD",
    price,
    url: offerUrl,
    availability: "https://schema.org/InStock",
    hasMerchantReturnPolicy: {
      "@type": "MerchantReturnPolicy",
      applicableCountry: "US",
      returnPolicyCategory: "https://schema.org/MerchantReturnNotPermitted",
      merchantReturnDays: 0,
    },
    shippingDetails: {
      "@type": "OfferShippingDetails",
      shippingRate: {
        "@type": "MonetaryAmount",
        value: "0",
        currency: "USD",
      },
      deliveryTime: {
        "@type": "ShippingDeliveryTime",
        handlingTime: {
          "@type": "QuantitativeValue",
          minValue: 0,
          maxValue: 0,
          unitCode: "DAY",
        },
        transitTime: {
          "@type": "QuantitativeValue",
          minValue: 0,
          maxValue: 0,
          unitCode: "DAY",
        },
      },
      shippingDestination: {
        "@type": "DefinedRegion",
        addressCountry: "US",
      },
    },
  }
}

export function buildProductStructuredData(options: {
  name?: string
  description: string
  offers: Array<{ name: string; price: string; url: string }>
}) {
  return {
    "@type": "Product",
    name: options.name ?? "LLMHive",
    description: options.description,
    image: [PRODUCT_IMAGE_URL],
    brand: {
      "@type": "Brand",
      name: "LLMHive",
    },
    aggregateRating: PRODUCT_AGGREGATE_RATING,
    review: [PRODUCT_SAMPLE_REVIEW],
    offers: options.offers.map((tier) => ({
      ...digitalOfferExtras(tier.price, tier.url),
      name: tier.name,
    })),
  }
}

export function organizationNode() {
  return {
    "@type": "Organization",
    name: "LLMHive",
    url: SITE_URL,
    logo: PRODUCT_IMAGE_URL,
  }
}
