/**
 * Email Service - Transactional Emails using Resend
 * 
 * Handles all outbound emails:
 * - Welcome emails after signup
 * - Subscription confirmations
 * - Payment receipts
 * - Support ticket confirmations
 */

// Email configuration
const RESEND_API_KEY = process.env.RESEND_API_KEY
const EMAIL_FROM = process.env.EMAIL_FROM || "LLMHive <noreply@contact.llmhive.ai>"
const APP_URL = process.env.NEXT_PUBLIC_APP_URL || "https://llmhive.ai"

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
 * Welcome Email - Sent after user signs up
 */
export async function sendWelcomeEmail(options: {
  to: string
  name: string
}): Promise<EmailResult> {
  const { to, name } = options
  const firstName = name.split(" ")[0] || "there"

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
          <!-- Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #C48E48 0%, #8B6914 100%); padding: 32px; text-align: center;">
              <h1 style="margin: 0; color: #0a0a0a; font-size: 28px; font-weight: 700;">🐝 LLMHive</h1>
              <p style="margin: 8px 0 0 0; color: #0a0a0a; font-size: 14px; opacity: 0.8;">Elite Multi-Model AI Orchestration</p>
            </td>
          </tr>
          
          <!-- Content -->
          <tr>
            <td style="padding: 40px 32px;">
              <h2 style="margin: 0 0 16px 0; color: #f5f5f5; font-size: 24px;">Welcome, ${firstName}! 🎉</h2>
              
              <p style="margin: 0 0 24px 0; color: #a3a3a3; font-size: 16px; line-height: 1.6;">
                You've just unlocked access to the most powerful AI orchestration platform available. 
                LLMHive combines the best AI models to deliver consistently superior results.
              </p>
              
              <!-- Features -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin: 24px 0;">
                <tr>
                  <td style="padding: 16px; background-color: #262626; border-radius: 8px; margin-bottom: 12px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="40" style="vertical-align: top;">
                          <span style="font-size: 24px;">🧠</span>
                        </td>
                        <td style="padding-left: 12px;">
                          <h4 style="margin: 0 0 4px 0; color: #f5f5f5; font-size: 14px;">Multi-Model Intelligence</h4>
                          <p style="margin: 0; color: #737373; font-size: 13px;">GPT-4, Claude, Gemini, and more working together</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr><td style="height: 12px;"></td></tr>
                <tr>
                  <td style="padding: 16px; background-color: #262626; border-radius: 8px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="40" style="vertical-align: top;">
                          <span style="font-size: 24px;">⚡</span>
                        </td>
                        <td style="padding-left: 12px;">
                          <h4 style="margin: 0 0 4px 0; color: #f5f5f5; font-size: 14px;">ELITE Mode Orchestration</h4>
                          <p style="margin: 0; color: #737373; font-size: 13px;">Advanced reasoning with HRM, DeepConf, and ensemble methods</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr><td style="height: 12px;"></td></tr>
                <tr>
                  <td style="padding: 16px; background-color: #262626; border-radius: 8px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="40" style="vertical-align: top;">
                          <span style="font-size: 24px;">🏆</span>
                        </td>
                        <td style="padding-left: 12px;">
                          <h4 style="margin: 0 0 4px 0; color: #f5f5f5; font-size: 14px;">Top-Ranked Performance</h4>
                          <p style="margin: 0; color: #737373; font-size: 13px;">Outperforming single models across all categories</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
              
              <!-- CTA Button -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin: 32px 0;">
                <tr>
                  <td align="center">
                    <a href="${APP_URL}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #C48E48 0%, #A67C3D 100%); color: #0a0a0a; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px;">
                      Start Your First Chat →
                    </a>
                  </td>
                </tr>
              </table>
              
              <p style="margin: 24px 0 0 0; color: #737373; font-size: 14px; line-height: 1.6;">
                Need help getting started? Check out our <a href="${APP_URL}/help" style="color: #C48E48;">Help Center</a> 
                or reply to this email – we're here to help!
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
Welcome to LLMHive, ${firstName}!

You've just unlocked access to the most powerful AI orchestration platform available.

What you can do:
- Multi-Model Intelligence: GPT-4, Claude, Gemini, and more working together
- ELITE Mode Orchestration: Advanced reasoning with HRM, DeepConf, and ensemble methods  
- Top-Ranked Performance: Outperforming single models across all categories

Get started: ${APP_URL}

Need help? Visit our Help Center: ${APP_URL}/help

© ${new Date().getFullYear()} LLMHive
  `.trim()

  return sendEmail({
    to,
    subject: "Welcome to LLMHive 🐝 – Your AI Journey Begins",
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
    lite: ["500 queries/month", "Standard orchestration", "Email support"],
    pro: ["5,000 queries/month", "ELITE orchestration", "Priority support", "Advanced analytics"],
    enterprise: ["Unlimited queries", "ELITE orchestration", "Dedicated support", "Custom integrations", "Team management"],
    maximum: ["Unlimited everything", "ELITE orchestration", "24/7 support", "White-glove onboarding", "Custom model training"],
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
