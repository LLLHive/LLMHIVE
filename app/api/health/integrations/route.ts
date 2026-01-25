/**
 * Integration Health Check API
 * 
 * Checks the status of all external integrations:
 * - Slack webhook
 * - Resend email service
 * - Backend orchestrator API
 * 
 * Use this endpoint to verify all services are properly configured.
 */
import { NextResponse } from "next/server"

export async function GET() {
  const checks = {
    slack: {
      configured: !!process.env.SLACK_WEBHOOK_URL,
      url: process.env.SLACK_WEBHOOK_URL ? 
        `${process.env.SLACK_WEBHOOK_URL.substring(0, 30)}...` : 
        "NOT SET",
      status: "unknown",
    },
    resend: {
      configured: !!process.env.RESEND_API_KEY,
      apiKey: process.env.RESEND_API_KEY ? 
        `${process.env.RESEND_API_KEY.substring(0, 10)}...` : 
        "NOT SET",
      status: "unknown",
    },
    backend: {
      configured: !!process.env.ORCHESTRATOR_API_BASE_URL,
      url: process.env.ORCHESTRATOR_API_BASE_URL || "NOT SET",
      status: "unknown",
    },
  }

  // Test Slack webhook
  if (checks.slack.configured) {
    try {
      const response = await fetch(process.env.SLACK_WEBHOOK_URL!, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: "🔍 LLMHive Integration Health Check - Slack is working!"
        }),
      })
      checks.slack.status = response.ok ? "healthy" : `error: ${response.status}`
    } catch (error) {
      checks.slack.status = `error: ${error}`
    }
  } else {
    checks.slack.status = "not configured"
  }

  // Test Resend
  if (checks.resend.configured) {
    // Don't actually send an email, just verify the API key format
    checks.resend.status = process.env.RESEND_API_KEY?.startsWith("re_") ? 
      "configured (format valid)" : 
      "configured (format unknown)"
  } else {
    checks.resend.status = "not configured"
  }

  // Test Backend
  if (checks.backend.configured) {
    try {
      const response = await fetch(`${process.env.ORCHESTRATOR_API_BASE_URL}/health`, {
        method: "GET",
      })
      checks.backend.status = response.ok ? "healthy" : `error: ${response.status}`
    } catch (error) {
      checks.backend.status = `error: ${error}`
    }
  } else {
    checks.backend.status = "not configured"
  }

  // Determine overall health
  const allHealthy = 
    checks.slack.status === "healthy" &&
    (checks.resend.status === "configured (format valid)" || checks.resend.status === "healthy") &&
    checks.backend.status === "healthy"

  return NextResponse.json({
    overall: allHealthy ? "healthy" : "degraded",
    timestamp: new Date().toISOString(),
    checks,
    recommendations: {
      slack: !checks.slack.configured ? 
        "⚠️ SLACK_WEBHOOK_URL not set. Support tickets will not send Slack notifications." : 
        checks.slack.status !== "healthy" ? 
        "⚠️ Slack webhook test failed. Check the webhook URL in Vercel settings." : 
        "✅ Slack integration working",
      resend: !checks.resend.configured ? 
        "⚠️ RESEND_API_KEY not set. Email confirmations will not be sent." : 
        "✅ Resend API key configured",
      backend: !checks.backend.configured ? 
        "⚠️ ORCHESTRATOR_API_BASE_URL not set. Using default backend." : 
        checks.backend.status !== "healthy" ? 
        "⚠️ Backend health check failed. API calls may fail." : 
        "✅ Backend API healthy",
    },
  })
}
