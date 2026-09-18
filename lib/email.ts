/**
 * Email Service - Transactional Emails using Resend
 * 
 * Handles all outbound emails:
 * - Welcome emails after signup
 * - Subscription confirmations
 * - Payment receipts
 * - Support ticket confirmations
 */

import { BENCHMARK_CLAIM_SHORT } from "@/lib/benchmark-claim"
import { getSiteUrl } from "@/lib/site-url"

// Email configuration
const RESEND_API_KEY = process.env.RESEND_API_KEY
const EMAIL_FROM = process.env.EMAIL_FROM || "LLMHive <noreply@contact.llmhive.ai>"
const APP_URL = getSiteUrl()

export interface EmailResult {
  success: boolean
  id?: string
  error?: string
}

/**
 * Send an email using Resend API
 */
async function sendEmail(options: {
  to: string
  subject: string
  html: string
  text?: string
}): Promise<EmailResult> {
  if (!RESEND_API_KEY) {
    console.log("[Email] RESEND_API_KEY not configured, skipping email")
    console.log(`[Email] Would send to ${options.to}: ${options.subject}`)
    return { success: true, id: "skipped-no-api-key" }
  }

  try {
    const response = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${RESEND_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: EMAIL_FROM,
        to: options.to,
        subject: options.subject,
        html: options.html,
        text: options.text,
      }),
    })

    if (!response.ok) {
      const error = await response.text()
      console.error("[Email] Failed to send:", error)
      return { success: false, error }
    }

    const data = await response.json()
    console.log(`[Email] Sent successfully to ${options.to}: ${data.id}`)
    return { success: true, id: data.id }
  } catch (error) {
    console.error("[Email] Error:", error)
    return { success: false, error: String(error) }
  }
}

// ============================================================================
// Email Templates
// ============================================================================

/**
 * Welcome Email - Sent immediately after free/trial signup.
 *
 * Research-backed job: one activation CTA (first chat), outcome language,
 * under ~60s read. Avoids feature dumps / early upgrade pressure.
 */
export async function sendWelcomeEmail(options: {
  to: string
  name: string
  /** free | trial | default — soft framing only; CTA stays activation. */
  accountType?: "free" | "trial" | "default"
}): Promise<EmailResult> {
  const { to, name, accountType = "default" } = options
  const firstName = name.split(" ")[0] || "there"
  const isTrial = accountType === "trial"
  const planLine = isTrial
    ? "Your Standard trial is live. You already have access — the fastest way to see the difference is one real question."
    : "Your free account is ready. The fastest way to see why teams switch from single-model chat is one real question."

  const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Welcome to LLMHive</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0a0a0a; color: #e5e5e5;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0a0a; padding: 40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #171717; border-radius: 16px; overflow: hidden; border: 1px solid #262626;">
          <tr>
            <td style="background: linear-gradient(135deg, #C48E48 0%, #8B6914 100%); padding: 28px 32px; text-align: center;">
              <h1 style="margin: 0; color: #0a0a0a; font-size: 26px; font-weight: 700;">LLMHive</h1>
              <p style="margin: 8px 0 0 0; color: #0a0a0a; font-size: 14px; opacity: 0.85;">Better answers by routing the right models</p>
            </td>
          </tr>
          <tr>
            <td style="padding: 36px 32px;">
              <h2 style="margin: 0 0 12px 0; color: #f5f5f5; font-size: 22px;">Welcome, ${firstName}</h2>
              <p style="margin: 0 0 18px 0; color: #a3a3a3; font-size: 16px; line-height: 1.6;">
                ${planLine}
              </p>
              <p style="margin: 0 0 8px 0; color: #f5f5f5; font-size: 15px; font-weight: 600; line-height: 1.5;">
                Do this once (about 2 minutes):
              </p>
              <p style="margin: 0 0 24px 0; color: #a3a3a3; font-size: 15px; line-height: 1.6;">
                Ask a hard question you actually care about — coding, research, math, or a long document.
                LLMHive orchestrates specialist models so you get a stronger answer than any single chat alone.
                ${BENCHMARK_CLAIM_SHORT}.
              </p>
              <table width="100%" cellpadding="0" cellspacing="0" style="margin: 8px 0 28px 0;">
                <tr>
                  <td align="center">
                    <a href="${APP_URL}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #C48E48 0%, #A67C3D 100%); color: #0a0a0a; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px;">
                      Ask your first question →
                    </a>
                  </td>
                </tr>
              </table>
              <p style="margin: 0; color: #737373; font-size: 13px; line-height: 1.6;">
                Stuck? Reply to this email — a human reads it. Or skim the
                <a href="${APP_URL}/help" style="color: #C48E48;">Help Center</a>.
                ${isTrial ? `When your trial ends, Standard is $10/month if you want to keep going.` : `When you outgrow free, Standard is $10/month.`}
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding: 20px 32px; background-color: #0f0f0f; border-top: 1px solid #262626;">
              <p style="margin: 0; color: #525252; font-size: 12px; text-align: center;">
                © ${new Date().getFullYear()} LLMHive ·
                <a href="${APP_URL}/privacy" style="color: #737373;">Privacy</a> ·
                <a href="${APP_URL}/terms" style="color: #737373;">Terms</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
  `.trim()

  const text = `
Welcome to LLMHive, ${firstName}

${planLine}

Do this once (about 2 minutes):
Ask a hard question you actually care about — coding, research, math, or a long document.
LLMHive orchestrates specialist models for a stronger answer than any single chat alone.
${BENCHMARK_CLAIM_SHORT}.

Ask your first question: ${APP_URL}

Stuck? Reply to this email or visit ${APP_URL}/help
${isTrial ? "When your trial ends, Standard is $10/month if you want to keep going." : "When you outgrow free, Standard is $10/month."}

© ${new Date().getFullYear()} LLMHive
  `.trim()

  return sendEmail({
    to,
    subject: isTrial
      ? `${firstName}, your LLMHive trial is ready — ask one real question`
      : `${firstName}, your LLMHive account is ready — ask one real question`,
    html,
    text,
  })
}

/**
 * Trial ending tomorrow — offer Standard at $10/mo to continue.
 *
 * Best-practice structure (Postmark / Bento / SaaS conversion research):
 * exact deadline, what access ends, loss-framed value, transparent price,
 * one CTA, easy support reply. No fake scarcity / invented discounts.
 */
export async function sendTrialExpiringEmail(options: {
  to: string
  name: string
  trialEndIso: string
  priceMonthlyUsd?: number
}): Promise<EmailResult> {
  const { to, name, trialEndIso, priceMonthlyUsd = 10 } = options
  const firstName = name.split(" ")[0] || "there"
  const endDate = new Date(trialEndIso)
  const endLabel = Number.isFinite(endDate.getTime())
    ? endDate.toLocaleString("en-US", {
        weekday: "long",
        month: "long",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
        timeZoneName: "short",
      })
    : "tomorrow"
  const billingUrl = `${APP_URL}/billing`
  const price = `$${priceMonthlyUsd}/month`

  const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Your LLMHive trial ends tomorrow</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0a0a0a; color: #e5e5e5;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0a0a; padding: 40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #171717; border-radius: 16px; overflow: hidden; border: 1px solid #262626;">
          <tr>
            <td style="background: linear-gradient(135deg, #C48E48 0%, #8B6914 100%); padding: 28px 32px; text-align: center;">
              <h1 style="margin: 0; color: #0a0a0a; font-size: 24px; font-weight: 700;">Your trial ends tomorrow</h1>
              <p style="margin: 8px 0 0 0; color: #0a0a0a; font-size: 14px; opacity: 0.85;">Keep Standard access for ${price}</p>
            </td>
          </tr>
          <tr>
            <td style="padding: 36px 32px;">
              <p style="margin: 0 0 16px 0; color: #f5f5f5; font-size: 16px; line-height: 1.6;">
                Hi ${firstName},
              </p>
              <p style="margin: 0 0 16px 0; color: #a3a3a3; font-size: 16px; line-height: 1.6;">
                Your LLMHive Standard trial ends <strong style="color:#f5f5f5;">${endLabel}</strong>
                (about 24 hours from this note).
              </p>
              <p style="margin: 0 0 16px 0; color: #a3a3a3; font-size: 16px; line-height: 1.6;">
                After that, paid Standard features pause unless you continue.
                If orchestration has already saved you time on hard questions, the straightforward next step is Standard at
                <strong style="color:#C48E48;">${price}</strong> — cancel anytime from Billing.
              </p>
              <table width="100%" cellpadding="0" cellspacing="0" style="margin: 8px 0 24px 0; background-color: #262626; border-radius: 8px;">
                <tr>
                  <td style="padding: 16px 20px; color: #a3a3a3; font-size: 14px; line-height: 1.6;">
                    <strong style="color:#f5f5f5;">What you keep with Standard:</strong><br>
                    Multi-model orchestration · Premium Mode · conversation memory · the routing that made your trial answers stronger
                  </td>
                </tr>
              </table>
              <table width="100%" cellpadding="0" cellspacing="0" style="margin: 8px 0 28px 0;">
                <tr>
                  <td align="center">
                    <a href="${billingUrl}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #C48E48 0%, #A67C3D 100%); color: #0a0a0a; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px;">
                      Continue for ${price} →
                    </a>
                  </td>
                </tr>
              </table>
              <p style="margin: 0; color: #737373; font-size: 13px; line-height: 1.6;">
                Not ready? No hard feelings — you can return later at
                <a href="${APP_URL}/pricing" style="color: #C48E48;">llmhive.ai/pricing</a>.
                Need a hand or more time? Reply to this email.
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding: 20px 32px; background-color: #0f0f0f; border-top: 1px solid #262626;">
              <p style="margin: 0; color: #525252; font-size: 12px; text-align: center;">
                © ${new Date().getFullYear()} LLMHive ·
                <a href="${APP_URL}/billing" style="color: #737373;">Billing</a> ·
                <a href="${APP_URL}/privacy" style="color: #737373;">Privacy</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
  `.trim()

  const text = `
Hi ${firstName},

Your LLMHive Standard trial ends tomorrow — ${endLabel}.

After that, paid Standard features pause unless you continue.
Continue for ${price} (cancel anytime): ${billingUrl}

What you keep with Standard:
Multi-model orchestration, Premium Mode, conversation memory, and the routing that made your trial answers stronger.

Not ready? You can return later: ${APP_URL}/pricing
Need a hand or more time? Reply to this email.

© ${new Date().getFullYear()} LLMHive
  `.trim()

  return sendEmail({
    to,
    subject: `${firstName}, your LLMHive trial ends tomorrow — continue for ${price}`,
    html,
    text,
  })
}

/**
 * Subscription Confirmation Email - Sent after successful payment
 */
export async function sendSubscriptionEmail(options: {
  to: string
  name: string
  tier: string
  billingCycle: "monthly" | "annual"
  amount: number // in cents
  nextBillingDate: string
}): Promise<EmailResult> {
  const { to, name, tier, billingCycle, amount, nextBillingDate } = options
  const firstName = name.split(" ")[0] || "there"
  const formattedAmount = (amount / 100).toFixed(2)
  const tierDisplay = tier.charAt(0).toUpperCase() + tier.slice(1)

  const tierFeatures: Record<string, string[]> = {
    lite: ["Premium orchestration included", "90-day conversation memory", "Knowledge base access"],
    pro: ["Premium orchestration included", "90-day conversation memory", "Advanced orchestration"],
    enterprise: ["Unlimited queries", "Premium orchestration", "Dedicated support", "Custom integrations", "Team management"],
    maximum: ["Unlimited everything", "Premium orchestration", "24/7 support", "White-glove onboarding", "Custom model training"],
  }

  const features = tierFeatures[tier.toLowerCase()] || tierFeatures.pro

  const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Subscription Confirmed</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0a0a0a; color: #e5e5e5;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0a0a; padding: 40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #171717; border-radius: 16px; overflow: hidden; border: 1px solid #262626;">
          <!-- Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); padding: 32px; text-align: center;">
              <h1 style="margin: 0; color: white; font-size: 28px; font-weight: 700;">✓ Payment Confirmed</h1>
              <p style="margin: 8px 0 0 0; color: white; font-size: 14px; opacity: 0.9;">Your ${tierDisplay} subscription is now active</p>
            </td>
          </tr>
          
          <!-- Content -->
          <tr>
            <td style="padding: 40px 32px;">
              <h2 style="margin: 0 0 16px 0; color: #f5f5f5; font-size: 24px;">Thank you, ${firstName}! 🎉</h2>
              
              <p style="margin: 0 0 24px 0; color: #a3a3a3; font-size: 16px; line-height: 1.6;">
                Your subscription to <strong style="color: #C48E48;">${tierDisplay}</strong> has been confirmed. 
                You now have full access to all ${tierDisplay} features.
              </p>
              
              <!-- Order Summary -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin: 24px 0; background-color: #262626; border-radius: 8px; overflow: hidden;">
                <tr>
                  <td style="padding: 16px 20px; border-bottom: 1px solid #404040;">
                    <h4 style="margin: 0; color: #a3a3a3; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Order Summary</h4>
                  </td>
                </tr>
                <tr>
                  <td style="padding: 20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="color: #a3a3a3; font-size: 14px; padding-bottom: 8px;">Plan</td>
                        <td align="right" style="color: #f5f5f5; font-size: 14px; font-weight: 600; padding-bottom: 8px;">${tierDisplay} (${billingCycle})</td>
                      </tr>
                      <tr>
                        <td style="color: #a3a3a3; font-size: 14px; padding-bottom: 8px;">Amount</td>
                        <td align="right" style="color: #22c55e; font-size: 14px; font-weight: 600; padding-bottom: 8px;">$${formattedAmount}</td>
                      </tr>
                      <tr>
                        <td style="color: #a3a3a3; font-size: 14px;">Next billing date</td>
                        <td align="right" style="color: #f5f5f5; font-size: 14px;">${nextBillingDate}</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
              
              <!-- Features -->
              <h4 style="margin: 24px 0 12px 0; color: #f5f5f5; font-size: 14px;">Your ${tierDisplay} Features:</h4>
              <table width="100%" cellpadding="0" cellspacing="0">
                ${features.map(feature => `
                <tr>
                  <td style="padding: 8px 0; color: #a3a3a3; font-size: 14px;">
                    <span style="color: #22c55e; margin-right: 8px;">✓</span> ${feature}
                  </td>
                </tr>
                `).join("")}
              </table>
              
              <!-- CTA -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin: 32px 0;">
                <tr>
                  <td align="center">
                    <a href="${APP_URL}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #C48E48 0%, #A67C3D 100%); color: #0a0a0a; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px;">
                      Start Using LLMHive →
                    </a>
                  </td>
                </tr>
              </table>
              
              <p style="margin: 24px 0 0 0; color: #737373; font-size: 14px; line-height: 1.6;">
                Manage your subscription anytime at <a href="${APP_URL}/billing" style="color: #C48E48;">Billing Settings</a>.
              </p>
            </td>
          </tr>
          
          <!-- Footer -->
          <tr>
            <td style="padding: 24px 32px; background-color: #0f0f0f; border-top: 1px solid #262626;">
              <p style="margin: 0; color: #525252; font-size: 12px; text-align: center;">
                © ${new Date().getFullYear()} LLMHive. All rights reserved.<br>
                <a href="${APP_URL}/privacy" style="color: #737373;">Privacy Policy</a> · 
                <a href="${APP_URL}/terms" style="color: #737373;">Terms of Service</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
  `.trim()

  const text = `
Payment Confirmed - Thank you, ${firstName}!

Your ${tierDisplay} subscription is now active.

Order Summary:
- Plan: ${tierDisplay} (${billingCycle})
- Amount: $${formattedAmount}
- Next billing: ${nextBillingDate}

Your ${tierDisplay} Features:
${features.map(f => `✓ ${f}`).join("\n")}

Start using LLMHive: ${APP_URL}
Manage subscription: ${APP_URL}/billing

© ${new Date().getFullYear()} LLMHive
  `.trim()

  return sendEmail({
    to,
    subject: `✓ ${tierDisplay} Subscription Confirmed – LLMHive`,
    html,
    text,
  })
}

/**
 * Support Ticket Confirmation - Sent when user submits a ticket
 */
export async function sendTicketConfirmationEmail(options: {
  to: string
  name: string
  ticketId: string
  subject: string
  estimatedResponse: string
}): Promise<EmailResult> {
  const { to, name, ticketId, subject, estimatedResponse } = options
  const firstName = name.split(" ")[0] || "there"

  const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Support Ticket Received</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0a0a0a; color: #e5e5e5;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0a0a; padding: 40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #171717; border-radius: 16px; overflow: hidden; border: 1px solid #262626;">
          <!-- Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); padding: 32px; text-align: center;">
              <h1 style="margin: 0; color: white; font-size: 28px; font-weight: 700;">📬 Ticket Received</h1>
              <p style="margin: 8px 0 0 0; color: white; font-size: 14px; opacity: 0.9;">We'll get back to you soon</p>
            </td>
          </tr>
          
          <!-- Content -->
          <tr>
            <td style="padding: 40px 32px;">
              <h2 style="margin: 0 0 16px 0; color: #f5f5f5; font-size: 24px;">Hi ${firstName},</h2>
              
              <p style="margin: 0 0 24px 0; color: #a3a3a3; font-size: 16px; line-height: 1.6;">
                We've received your support request and our team is on it. Here's your ticket details:
              </p>
              
              <!-- Ticket Info -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin: 24px 0; background-color: #262626; border-radius: 8px; overflow: hidden;">
                <tr>
                  <td style="padding: 20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="color: #a3a3a3; font-size: 14px; padding-bottom: 12px;">Ticket ID</td>
                        <td align="right" style="padding-bottom: 12px;">
                          <code style="color: #C48E48; font-size: 14px; font-weight: 600; background-color: #1a1a1a; padding: 4px 8px; border-radius: 4px;">${ticketId}</code>
                        </td>
                      </tr>
                      <tr>
                        <td style="color: #a3a3a3; font-size: 14px; padding-bottom: 12px;">Subject</td>
                        <td align="right" style="color: #f5f5f5; font-size: 14px; padding-bottom: 12px;">${subject}</td>
                      </tr>
                      <tr>
                        <td style="color: #a3a3a3; font-size: 14px;">Expected response</td>
                        <td align="right" style="color: #22c55e; font-size: 14px; font-weight: 600;">${estimatedResponse}</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
              
              <p style="margin: 24px 0; color: #a3a3a3; font-size: 14px; line-height: 1.6;">
                You can track your ticket status anytime at <a href="${APP_URL}/support/tickets" style="color: #C48E48;">Support Tickets</a>.
              </p>
              
              <p style="margin: 0; color: #737373; font-size: 14px; line-height: 1.6;">
                In the meantime, you might find answers in our <a href="${APP_URL}/help" style="color: #C48E48;">Help Center</a>.
              </p>
            </td>
          </tr>
          
          <!-- Footer -->
          <tr>
            <td style="padding: 24px 32px; background-color: #0f0f0f; border-top: 1px solid #262626;">
              <p style="margin: 0; color: #525252; font-size: 12px; text-align: center;">
                © ${new Date().getFullYear()} LLMHive. All rights reserved.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
  `.trim()

  const text = `
Hi ${firstName},

We've received your support request. Here's your ticket details:

Ticket ID: ${ticketId}
Subject: ${subject}
Expected response: ${estimatedResponse}

Track your ticket: ${APP_URL}/support/tickets
Help Center: ${APP_URL}/help

© ${new Date().getFullYear()} LLMHive
  `.trim()

  return sendEmail({
    to,
    subject: `[${ticketId}] Support Request Received – LLMHive`,
    html,
    text,
  })
}
