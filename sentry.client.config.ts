// This file configures the initialization of Sentry on the client.
// The config you add here will be used whenever a users loads a page in their browser.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Setting this option to true will print useful information to the console while you're setting up Sentry.
  debug: false,

  // Adjust this value in production, or use tracesSampler for greater control
  tracesSampleRate: 1,

  // You can remove this option if you're not planning to use the Session Replay feature:
  replaysSessionSampleRate: 0.1,

  // If you don't want to use Session Replay, you can remove this entirely
  replaysOnErrorSampleRate: 1.0,

  // You can remove this option if you're not planning to use the Session Replay feature:
  integrations: [
    Sentry.replayIntegration({
      // Additional Replay configuration goes in here, for example:
      maskAllText: true,
      blockAllMedia: true,
    }),
  ],

  // Only enable in production
  enabled: process.env.NODE_ENV === "production",

  // Set environment
  environment: process.env.NODE_ENV,

  // Ignore certain errors
  ignoreErrors: [
    // Random plugins/extensions
    "top.GLOBALS",
    // Network errors
    "Network request failed",
    "Failed to fetch",
    "NetworkError",
    // Browser extensions
    /Extension context invalidated/,
  ],

  // Don't send events for localhost
  beforeSend(event) {
    if (typeof window !== "undefined" && window.location.hostname === "localhost") {
      return null;
    }
    return event;
  },
});

