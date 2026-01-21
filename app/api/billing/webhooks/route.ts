import { NextRequest, NextResponse } from "next/server";
import Stripe from "stripe";
import { sendSubscriptionNotification } from "@/lib/slack";

// Lazy initialize Stripe
function getStripe(): Stripe | null {
  if (!process.env.STRIPE_SECRET_KEY) {
    return null;
  }
  return new Stripe(process.env.STRIPE_SECRET_KEY);
}

const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;

// Subscription tier mapping from Stripe price IDs
// Note: "Lite" tier uses BASIC env vars for backwards compatibility
const PRICE_TO_TIER: Record<string, string> = {
  [process.env.STRIPE_PRICE_ID_BASIC_MONTHLY || ""]: "lite",
  [process.env.STRIPE_PRICE_ID_BASIC_ANNUAL || ""]: "lite",
  [process.env.STRIPE_PRICE_ID_PRO_MONTHLY || ""]: "pro",
  [process.env.STRIPE_PRICE_ID_PRO_ANNUAL || ""]: "pro",
  [process.env.STRIPE_PRICE_ID_ENTERPRISE_MONTHLY || ""]: "enterprise",
  [process.env.STRIPE_PRICE_ID_ENTERPRISE_ANNUAL || ""]: "enterprise",
  [process.env.STRIPE_PRICE_ID_MAXIMUM_MONTHLY || ""]: "maximum",
  [process.env.STRIPE_PRICE_ID_MAXIMUM_ANNUAL || ""]: "maximum",
};

// Map Stripe status to our status
const STATUS_MAP: Record<string, string> = {
  active: "active",
  canceled: "cancelled",
  past_due: "past_due",
  trialing: "trialing",
  unpaid: "expired",
  incomplete: "pending",
  incomplete_expired: "expired",
};

interface SubscriptionData {
  userId: string;
  stripeCustomerId: string;
  stripeSubscriptionId: string;
  tier: string;
  status: string;
  billingCycle: "monthly" | "annual";
  currentPeriodStart: Date;
  currentPeriodEnd: Date;
  cancelAtPeriodEnd: boolean;
  seats?: number;
  updatedAt: Date;
}

/**
 * Store/update subscription in your database
 * This should be replaced with your actual database calls
 */
async function upsertSubscription(data: SubscriptionData): Promise<void> {
  // In production, this would update Firestore, your database, or Clerk metadata
  // For now, we'll make a call to the backend API
  const backendUrl = process.env.LLMHIVE_BACKEND_URL || "http://localhost:8000";
  
  try {
    const response = await fetch(`${backendUrl}/api/v1/billing/subscription/sync`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${process.env.API_KEY || ""}`,
      },
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      console.error("Failed to sync subscription to backend:", await response.text());
    }
  } catch (error) {
    console.error("Error syncing subscription:", error);
    // Don't throw - we don't want to fail the webhook
  }
}

/**
 * Handle checkout.session.completed
 * User has successfully subscribed
 */
async function handleCheckoutCompleted(
  stripe: Stripe,
  session: Stripe.Checkout.Session
): Promise<void> {
  const userId = session.client_reference_id || session.metadata?.user_id;
  
  if (!userId) {
    console.error("No user_id found in checkout session:", session.id);
    return;
  }
  
  if (!session.subscription) {
    console.error("No subscription in checkout session:", session.id);
    return;
  }
  
  // Retrieve the full subscription object
  const subscription = await stripe.subscriptions.retrieve(
    session.subscription as string
  );
  
  const priceId = subscription.items.data[0]?.price.id;
  const tier = session.metadata?.tier || PRICE_TO_TIER[priceId] || "pro";
  const billingCycle = session.metadata?.billing_cycle || 
    (subscription.items.data[0]?.price.recurring?.interval === "year" ? "annual" : "monthly");
  const seats = subscription.items.data[0]?.quantity || 1;
  
  // Access period fields safely
  const subAny = subscription as unknown as Record<string, unknown>;
  const periodStart = subAny.current_period_start as number;
  const periodEnd = subAny.current_period_end as number;
  
  await upsertSubscription({
    userId,
    stripeCustomerId: subscription.customer as string,
    stripeSubscriptionId: subscription.id,
    tier,
    status: "active",
    billingCycle: billingCycle as "monthly" | "annual",
    currentPeriodStart: new Date(periodStart * 1000),
    currentPeriodEnd: new Date(periodEnd * 1000),
    cancelAtPeriodEnd: subscription.cancel_at_period_end,
    seats,
    updatedAt: new Date(),
  });
  
  console.log(`Subscription created for user ${userId}: ${tier} (${billingCycle})`);
  
  // Send Slack notification for new subscription
  sendSubscriptionNotification({
    type: "new",
    email: session.customer_email || session.customer_details?.email || userId,
    tier,
  }).catch((err) => console.error("[Webhook] Slack notification error:", err));
}

/**
 * Handle customer.subscription.created
 */
async function handleSubscriptionCreated(subscription: Stripe.Subscription): Promise<void> {
  // Most logic is in checkout.session.completed
  // This is a backup handler
  console.log("Subscription created:", subscription.id);
}

/**
 * Handle customer.subscription.updated
 * Subscription was modified (upgrade, downgrade, renewal, etc.)
 */
async function handleSubscriptionUpdated(subscription: Stripe.Subscription): Promise<void> {
  const metadata = subscription.metadata || {};
  const userId = metadata.user_id;
  
  if (!userId) {
    // Try to find user by customer ID - would need database lookup
    console.warn("No user_id in subscription metadata:", subscription.id);
    return;
  }
  
  const priceId = subscription.items.data[0]?.price.id;
  const tier = metadata.tier || PRICE_TO_TIER[priceId] || "pro";
  const status = STATUS_MAP[subscription.status] || "active";
  const seats = subscription.items.data[0]?.quantity || 1;
  
  // Access period fields safely
  const subAny = subscription as unknown as Record<string, unknown>;
  const periodStart = subAny.current_period_start as number;
  const periodEnd = subAny.current_period_end as number;
  
  await upsertSubscription({
    userId,
    stripeCustomerId: subscription.customer as string,
    stripeSubscriptionId: subscription.id,
    tier,
    status,
    billingCycle: subscription.items.data[0]?.price.recurring?.interval === "year" ? "annual" : "monthly",
    currentPeriodStart: new Date(periodStart * 1000),
    currentPeriodEnd: new Date(periodEnd * 1000),
    cancelAtPeriodEnd: subscription.cancel_at_period_end,
    seats,
    updatedAt: new Date(),
  });
  
  console.log(`Subscription updated for user ${userId}: ${tier}, status: ${status}`);
}

/**
 * Handle customer.subscription.deleted
 * Subscription was cancelled
 */
async function handleSubscriptionDeleted(subscription: Stripe.Subscription): Promise<void> {
  const metadata = subscription.metadata || {};
  const userId = metadata.user_id;
  
  if (!userId) {
    console.warn("No user_id in deleted subscription:", subscription.id);
    return;
  }
  
  // Access period fields safely
  const subAny = subscription as unknown as Record<string, unknown>;
  const periodStart = subAny.current_period_start as number;
  const periodEnd = subAny.current_period_end as number;
  
  await upsertSubscription({
    userId,
    stripeCustomerId: subscription.customer as string,
    stripeSubscriptionId: subscription.id,
    tier: "free", // Downgrade to free
    status: "cancelled",
    billingCycle: "monthly",
    currentPeriodStart: new Date(periodStart * 1000),
    currentPeriodEnd: new Date(periodEnd * 1000),
    cancelAtPeriodEnd: true,
    updatedAt: new Date(),
  });
  
  console.log(`Subscription cancelled for user ${userId}`);
  
  // Send Slack notification for cancellation
  const priceId = subscription.items.data[0]?.price.id;
  const previousTier = subscription.metadata?.tier || PRICE_TO_TIER[priceId] || "unknown";
  sendSubscriptionNotification({
    type: "cancel",
    email: userId, // Would need customer email lookup in production
    tier: previousTier,
  }).catch((err) => console.error("[Webhook] Slack notification error:", err));
}

/**
 * Handle invoice.payment_succeeded
 * Renewal payment was successful
 */
async function handlePaymentSucceeded(invoice: Stripe.Invoice): Promise<void> {
  console.log("Payment succeeded for invoice:", invoice.id);
  // Update usage reset timestamps, send receipt email, etc.
}

/**
 * Handle invoice.payment_failed
 * Payment failed - subscription may become past_due
 */
async function handlePaymentFailed(
  stripe: Stripe,
  invoice: Stripe.Invoice
): Promise<void> {
  console.log("Payment failed for invoice:", invoice.id);
  // Send notification to user, update status, etc.
  
  const invoiceAny = invoice as unknown as Record<string, unknown>;
  const subscriptionId = invoiceAny.subscription as string | null;
  
  if (subscriptionId) {
    const subscription = await stripe.subscriptions.retrieve(subscriptionId);
    
    const metadata = subscription.metadata || {};
    const userId = metadata.user_id;
    
    if (userId) {
      const subAny = subscription as unknown as Record<string, unknown>;
      const periodStart = subAny.current_period_start as number;
      const periodEnd = subAny.current_period_end as number;
      
      await upsertSubscription({
        userId,
        stripeCustomerId: subscription.customer as string,
        stripeSubscriptionId: subscription.id,
        tier: metadata.tier || "pro",
        status: "past_due",
        billingCycle: subscription.items.data[0]?.price.recurring?.interval === "year" ? "annual" : "monthly",
        currentPeriodStart: new Date(periodStart * 1000),
        currentPeriodEnd: new Date(periodEnd * 1000),
        cancelAtPeriodEnd: subscription.cancel_at_period_end,
        updatedAt: new Date(),
      });
    }
  }
}

/**
 * Stripe Webhook Handler
 * Processes Stripe webhook events for subscription lifecycle
 */
export async function POST(request: NextRequest) {
  const stripe = getStripe();
  
  if (!stripe) {
    console.error("Stripe not configured");
    return NextResponse.json(
      { error: "Stripe not configured" },
      { status: 500 }
    );
  }
  
  if (!webhookSecret) {
    console.error("STRIPE_WEBHOOK_SECRET not configured");
    return NextResponse.json(
      { error: "Webhook secret not configured" },
      { status: 500 }
    );
  }

  const body = await request.text();
  const signature = request.headers.get("stripe-signature");

  if (!signature) {
    return NextResponse.json(
      { error: "Missing stripe-signature header" },
      { status: 400 }
    );
  }

  let event: Stripe.Event;

  try {
    event = stripe.webhooks.constructEvent(body, signature, webhookSecret);
  } catch (err) {
    console.error("Webhook signature verification failed:", err);
    return NextResponse.json(
      { error: "Invalid signature" },
      { status: 400 }
    );
  }

  console.log(`Processing webhook event: ${event.type}`);

  try {
    switch (event.type) {
      case "checkout.session.completed":
        await handleCheckoutCompleted(stripe, event.data.object as Stripe.Checkout.Session);
        break;
        
      case "customer.subscription.created":
        await handleSubscriptionCreated(event.data.object as Stripe.Subscription);
        break;
        
      case "customer.subscription.updated":
        await handleSubscriptionUpdated(event.data.object as Stripe.Subscription);
        break;
        
      case "customer.subscription.deleted":
        await handleSubscriptionDeleted(event.data.object as Stripe.Subscription);
        break;
        
      case "invoice.payment_succeeded":
        await handlePaymentSucceeded(event.data.object as Stripe.Invoice);
        break;
        
      case "invoice.payment_failed":
        await handlePaymentFailed(stripe, event.data.object as Stripe.Invoice);
        break;
        
      default:
        console.log(`Unhandled event type: ${event.type}`);
    }

    return NextResponse.json({ 
      received: true, 
      processed: true,
      event_type: event.type 
    });
  } catch (error) {
    console.error("Error processing webhook:", error);
    return NextResponse.json(
      { error: "Webhook processing failed" },
      { status: 500 }
    );
  }
}

// Disable body parsing - Stripe requires raw body for signature verification
export const dynamic = "force-dynamic";
