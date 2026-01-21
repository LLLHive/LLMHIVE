/**
 * Slack Integration Utilities
 * 
 * Provides functions to send notifications to Slack via webhooks.
 * Requires SLACK_WEBHOOK_URL environment variable to be set.
 */

export interface SlackMessage {
  text?: string
  blocks?: SlackBlock[]
  attachments?: SlackAttachment[]
}

export interface SlackBlock {
  type: "section" | "header" | "divider" | "context" | "actions"
  text?: {
    type: "plain_text" | "mrkdwn"
    text: string
    emoji?: boolean
  }
  fields?: Array<{
    type: "plain_text" | "mrkdwn"
    text: string
  }>
  elements?: Array<{
    type: string
    text?: { type: string; text: string; emoji?: boolean }
    url?: string
    action_id?: string
  }>
}

export interface SlackAttachment {
  color?: string
  title?: string
  text?: string
  fields?: Array<{
    title: string
    value: string
    short?: boolean
  }>
  footer?: string
  ts?: number
}

const SLACK_WEBHOOK_URL = process.env.SLACK_WEBHOOK_URL

/**
 * Send a message to Slack via webhook
 */
export async function sendSlackMessage(message: SlackMessage): Promise<boolean> {
  if (!SLACK_WEBHOOK_URL) {
    console.log("[Slack] SLACK_WEBHOOK_URL not configured, skipping notification")
    return false
  }

  try {
    const response = await fetch(SLACK_WEBHOOK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(message),
    })

    if (!response.ok) {
      console.error("[Slack] Failed to send message:", response.status, response.statusText)
      return false
    }

    console.log("[Slack] Message sent successfully")
    return true
  } catch (error) {
    console.error("[Slack] Error sending message:", error)
    return false
  }
}

/**
 * Send a simple text alert
 */
export async function sendSlackAlert(text: string): Promise<boolean> {
  return sendSlackMessage({ text })
}

/**
 * Priority colors for Slack attachments
 */
const PRIORITY_COLORS: Record<string, string> = {
  urgent: "#dc2626", // red
  high: "#f97316",   // orange
  medium: "#eab308", // yellow
  low: "#22c55e",    // green
}

/**
 * Send a support ticket notification to Slack
 */
export async function sendSupportTicketNotification(ticket: {
  id: string
  name: string
  email: string
  subject: string
  message: string
  type: string
  priority: string
}): Promise<boolean> {
  const priorityEmoji = {
    urgent: "🚨",
    high: "🔴",
    medium: "🟡",
    low: "🟢",
  }[ticket.priority] || "⚪"

  const message: SlackMessage = {
    blocks: [
      {
        type: "header",
        text: {
          type: "plain_text",
          text: `${priorityEmoji} New Support Ticket`,
          emoji: true,
        },
      },
      {
        type: "section",
        fields: [
          { type: "mrkdwn", text: `*Ticket ID:*\n\`${ticket.id}\`` },
          { type: "mrkdwn", text: `*Priority:*\n${ticket.priority.toUpperCase()}` },
          { type: "mrkdwn", text: `*From:*\n${ticket.name}` },
          { type: "mrkdwn", text: `*Email:*\n<mailto:${ticket.email}|${ticket.email}>` },
          { type: "mrkdwn", text: `*Type:*\n${ticket.type}` },
        ],
      },
      {
        type: "section",
        text: {
          type: "mrkdwn",
          text: `*Subject:*\n${ticket.subject}`,
        },
      },
      {
        type: "section",
        text: {
          type: "mrkdwn",
          text: `*Message:*\n${ticket.message.substring(0, 500)}${ticket.message.length > 500 ? "..." : ""}`,
        },
      },
      {
        type: "divider",
      },
      {
        type: "actions",
        elements: [
          {
            type: "button",
            text: {
              type: "plain_text",
              text: "View in Dashboard",
              emoji: true,
            },
            url: `${process.env.NEXT_PUBLIC_APP_URL || "https://llmhive.ai"}/admin/support`,
            action_id: "view_dashboard",
          },
          {
            type: "button",
            text: {
              type: "plain_text",
              text: "Reply via Email",
              emoji: true,
            },
            url: `mailto:${ticket.email}?subject=Re: ${encodeURIComponent(ticket.subject)}`,
            action_id: "reply_email",
          },
        ],
      },
    ],
    attachments: [
      {
        color: PRIORITY_COLORS[ticket.priority] || "#6b7280",
        footer: "LLMHive Support System",
        ts: Math.floor(Date.now() / 1000),
      },
    ],
  }

  return sendSlackMessage(message)
}

/**
 * Send a subscription notification to Slack
 */
export async function sendSubscriptionNotification(event: {
  type: "new" | "upgrade" | "downgrade" | "cancel"
  email: string
  tier: string
  previousTier?: string
  amount?: number
}): Promise<boolean> {
  const emoji = {
    new: "🎉",
    upgrade: "⬆️",
    downgrade: "⬇️",
    cancel: "👋",
  }[event.type]

  const title = {
    new: "New Subscription",
    upgrade: "Subscription Upgrade",
    downgrade: "Subscription Downgrade",
    cancel: "Subscription Cancelled",
  }[event.type]

  const color = {
    new: "#22c55e",
    upgrade: "#22c55e",
    downgrade: "#f97316",
    cancel: "#dc2626",
  }[event.type]

  const message: SlackMessage = {
    blocks: [
      {
        type: "header",
        text: {
          type: "plain_text",
          text: `${emoji} ${title}`,
          emoji: true,
        },
      },
      {
        type: "section",
        fields: [
          { type: "mrkdwn", text: `*Customer:*\n${event.email}` },
          { type: "mrkdwn", text: `*Tier:*\n${event.tier.toUpperCase()}` },
          ...(event.previousTier ? [{ type: "mrkdwn" as const, text: `*Previous:*\n${event.previousTier.toUpperCase()}` }] : []),
          ...(event.amount ? [{ type: "mrkdwn" as const, text: `*Amount:*\n$${(event.amount / 100).toFixed(2)}` }] : []),
        ],
      },
    ],
    attachments: [
      {
        color,
        footer: "LLMHive Billing",
        ts: Math.floor(Date.now() / 1000),
      },
    ],
  }

  return sendSlackMessage(message)
}
