import {
  GA_MEASUREMENT_ID,
  isGoogleAnalyticsEnabled,
} from "@/lib/marketing/google-analytics"

export function GoogleAnalyticsHead() {
  if (!isGoogleAnalyticsEnabled()) return null

  return (
    <>
      <script
        async
        src={`https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`}
      />
      <script
        dangerouslySetInnerHTML={{
          __html: `
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', '${GA_MEASUREMENT_ID}', {
              anonymize_ip: true,
            });
          `,
        }}
      />
    </>
  )
}
