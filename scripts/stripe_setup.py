#!/usr/bin/env python3
"""
Stripe Setup Script for LLMHive - Quota-Based Pricing (Jan 2026)

This script creates all necessary Stripe products and prices for LLMHive subscriptions.
Run this once to set up your Stripe account, then copy the price IDs to your environment variables.

PRICING STRUCTURE (All tiers get #1 ELITE quality with quota):
- Free Trial: 50 ELITE queries (marketing cost)
- Lite ($9.99): 100 ELITE + 400 BUDGET = 500 total
- Pro ($29.99): 400 ELITE + 600 STANDARD = 1,000 total
- Team ($49.99): 500 ELITE + 1,500 STANDARD = 2,000 total (pooled)
- Enterprise ($25/seat): 300 ELITE + 200 STANDARD = 500/seat
- Enterprise+ ($45/seat): 800 ELITE + 700 STANDARD = 1,500/seat
- Maximum ($499): 200 MAXIMUM + 500 ELITE = 700 total

Usage:
    export STRIPE_SECRET_KEY=sk_live_... (or sk_test_... for testing)
    python scripts/stripe_setup.py

Requirements:
    pip install stripe
"""

import os
import sys

try:
    import stripe
except ImportError:
    print("Error: stripe package not installed. Run: pip install stripe")
    sys.exit(1)


# Quota-based pricing structure
PRODUCTS = [
    {
        "name": "LLMHive Lite",
        "description": "#1 AI quality at $9.99/month. 100 ELITE queries (#1 in ALL), then 400 BUDGET queries (#1 in 6).",
        "metadata": {
            "tier": "lite",
            "elite_queries": "100",
            "budget_queries": "400",
            "total_queries": "500",
        },
        "prices": [
            {
                "nickname": "Lite Monthly",
                "unit_amount": 999,  # $9.99 in cents
                "currency": "usd",
                "recurring": {"interval": "month"},
                "env_var": "STRIPE_PRICE_ID_LITE_MONTHLY",
            },
            {
                "nickname": "Lite Annual",
                "unit_amount": 9999,  # $99.99 in cents
                "currency": "usd",
                "recurring": {"interval": "year"},
                "env_var": "STRIPE_PRICE_ID_LITE_ANNUAL",
            },
        ],
    },
    {
        "name": "LLMHive Pro",
        "description": "Power user plan with API access. 400 ELITE queries (#1 in ALL), then 600 STANDARD queries (#1 in 8).",
        "metadata": {
            "tier": "pro",
            "elite_queries": "400",
            "standard_queries": "600",
            "total_queries": "1000",
        },
        "prices": [
            {
                "nickname": "Pro Monthly",
                "unit_amount": 2999,  # $29.99 in cents
                "currency": "usd",
                "recurring": {"interval": "month"},
                "env_var": "STRIPE_PRICE_ID_PRO_MONTHLY",
            },
            {
                "nickname": "Pro Annual",
                "unit_amount": 29999,  # $299.99 in cents
                "currency": "usd",
                "recurring": {"interval": "year"},
                "env_var": "STRIPE_PRICE_ID_PRO_ANNUAL",
            },
        ],
    },
    {
        "name": "LLMHive Team",
        "description": "Team workspace with pooled queries. 500 ELITE pooled, then 1,500 STANDARD queries.",
        "metadata": {
            "tier": "team",
            "elite_queries": "500",
            "standard_queries": "1500",
            "total_queries": "2000",
            "team_members": "3",
        },
        "prices": [
            {
                "nickname": "Team Monthly",
                "unit_amount": 4999,  # $49.99 in cents
                "currency": "usd",
                "recurring": {"interval": "month"},
                "env_var": "STRIPE_PRICE_ID_TEAM_MONTHLY",
            },
            {
                "nickname": "Team Annual",
                "unit_amount": 49999,  # $499.99 in cents
                "currency": "usd",
                "recurring": {"interval": "year"},
                "env_var": "STRIPE_PRICE_ID_TEAM_ANNUAL",
            },
        ],
    },
    {
        "name": "LLMHive Enterprise",
        "description": "Enterprise with SSO & compliance. 300 ELITE per seat, then 200 STANDARD per seat.",
        "metadata": {
            "tier": "enterprise",
            "elite_queries_per_seat": "300",
            "standard_queries_per_seat": "200",
            "total_queries_per_seat": "500",
            "min_seats": "5",
        },
        "prices": [
            {
                "nickname": "Enterprise Monthly (per seat)",
                "unit_amount": 2500,  # $25.00 per seat in cents
                "currency": "usd",
                "recurring": {"interval": "month"},
                "env_var": "STRIPE_PRICE_ID_ENTERPRISE_MONTHLY",
            },
            {
                "nickname": "Enterprise Annual (per seat)",
                "unit_amount": 25000,  # $250.00 per seat in cents
                "currency": "usd",
                "recurring": {"interval": "year"},
                "env_var": "STRIPE_PRICE_ID_ENTERPRISE_ANNUAL",
            },
        ],
    },
    {
        "name": "LLMHive Enterprise Plus",
        "description": "Enterprise Plus with custom routing & dedicated support. 800 ELITE per seat.",
        "metadata": {
            "tier": "enterprise_plus",
            "elite_queries_per_seat": "800",
            "standard_queries_per_seat": "700",
            "total_queries_per_seat": "1500",
            "min_seats": "5",
        },
        "prices": [
            {
                "nickname": "Enterprise Plus Monthly (per seat)",
                "unit_amount": 4500,  # $45.00 per seat in cents
                "currency": "usd",
                "recurring": {"interval": "month"},
                "env_var": "STRIPE_PRICE_ID_ENTERPRISE_PLUS_MONTHLY",
            },
            {
                "nickname": "Enterprise Plus Annual (per seat)",
                "unit_amount": 45000,  # $450.00 per seat in cents
                "currency": "usd",
                "recurring": {"interval": "year"},
                "env_var": "STRIPE_PRICE_ID_ENTERPRISE_PLUS_ANNUAL",
            },
        ],
    },
    {
        "name": "LLMHive Maximum",
        "description": "BEATS competition by +5%. 200 MAXIMUM queries + 500 ELITE. Mission-critical support.",
        "metadata": {
            "tier": "maximum",
            "maximum_queries": "200",
            "elite_queries": "500",
            "total_queries": "700",
        },
        "prices": [
            {
                "nickname": "Maximum Monthly",
                "unit_amount": 49900,  # $499.00 in cents
                "currency": "usd",
                "recurring": {"interval": "month"},
                "env_var": "STRIPE_PRICE_ID_MAXIMUM_MONTHLY",
            },
            {
                "nickname": "Maximum Annual",
                "unit_amount": 499000,  # $4,990.00 in cents
                "currency": "usd",
                "recurring": {"interval": "year"},
                "env_var": "STRIPE_PRICE_ID_MAXIMUM_ANNUAL",
            },
        ],
    },
]


def setup_stripe():
    """Set up Stripe products and prices."""
    
    api_key = os.getenv("STRIPE_SECRET_KEY")
    if not api_key:
        print("Error: STRIPE_SECRET_KEY environment variable not set.")
        print("Run: export STRIPE_SECRET_KEY=sk_live_... (or sk_test_... for testing)")
        sys.exit(1)
    
    stripe.api_key = api_key
    
    is_test = api_key.startswith("sk_test_")
    env_type = "TEST" if is_test else "PRODUCTION"
    
    print(f"\n{'='*70}")
    print(f"  LLMHive Stripe Setup - {env_type} Environment")
    print(f"  Quota-Based Pricing (Jan 2026)")
    print(f"{'='*70}\n")
    
    if not is_test:
        print("⚠️  WARNING: You are using PRODUCTION keys!")
        confirm = input("Type 'yes' to continue: ")
        if confirm.lower() != "yes":
            print("Aborted.")
            sys.exit(0)
    
    created_prices = {}
    
    for product_config in PRODUCTS:
        print(f"\n📦 Creating product: {product_config['name']}")
        
        existing_products = stripe.Product.search(
            query=f"name:'{product_config['name']}'",
            limit=1,
        )
        
        if existing_products.data:
            product = existing_products.data[0]
            print(f"   ✓ Product already exists: {product.id}")
            # Update metadata
            stripe.Product.modify(
                product.id,
                description=product_config["description"],
                metadata=product_config.get("metadata", {}),
            )
            print(f"   ✓ Updated product metadata")
        else:
            product = stripe.Product.create(
                name=product_config["name"],
                description=product_config["description"],
                metadata={
                    **product_config.get("metadata", {}),
                    "app": "llmhive",
                    "created_by": "stripe_setup.py",
                    "pricing_version": "quota_based_jan2026",
                },
            )
            print(f"   ✓ Created product: {product.id}")
        
        for price_config in product_config["prices"]:
            print(f"\n   💰 Creating price: {price_config['nickname']}")
            
            existing_prices = stripe.Price.list(
                product=product.id,
                active=True,
                limit=100,
            )
            
            matching_price = None
            for p in existing_prices.data:
                if (p.unit_amount == price_config["unit_amount"] and 
                    p.recurring and 
                    p.recurring.interval == price_config["recurring"]["interval"]):
                    matching_price = p
                    break
            
            if matching_price:
                print(f"      ✓ Price already exists: {matching_price.id}")
                created_prices[price_config["env_var"]] = matching_price.id
            else:
                price = stripe.Price.create(
                    product=product.id,
                    nickname=price_config["nickname"],
                    unit_amount=price_config["unit_amount"],
                    currency=price_config["currency"],
                    recurring=price_config["recurring"],
                    metadata={
                        "app": "llmhive",
                        "tier": product_config.get("metadata", {}).get("tier", "unknown"),
                        "interval": price_config["recurring"]["interval"],
                        "pricing_version": "quota_based_jan2026",
                    },
                )
                print(f"      ✓ Created price: {price.id}")
                created_prices[price_config["env_var"]] = price.id
    
    print(f"\n{'='*70}")
    print("  Setup Complete!")
    print(f"{'='*70}\n")
    
    print("📋 Add these environment variables to Vercel/Cloud Run:\n")
    print("-" * 60)
    for env_var, price_id in sorted(created_prices.items()):
        print(f"{env_var}={price_id}")
    print("-" * 60)
    
    print("\n\n🔗 Webhook Setup Required:")
    print("-" * 60)
    print("1. Go to: https://dashboard.stripe.com/webhooks")
    print("2. Click '+ Add endpoint'")
    print("3. Endpoint URL: https://YOUR_BACKEND_URL/api/v1/webhooks/stripe-webhook")
    print("4. Select events:")
    print("   - checkout.session.completed")
    print("   - customer.subscription.created")
    print("   - customer.subscription.updated")
    print("   - customer.subscription.deleted")
    print("   - invoice.payment_succeeded")
    print("   - invoice.payment_failed")
    print("5. Copy the 'Signing secret' and add to Vercel:")
    print("   STRIPE_WEBHOOK_SECRET=whsec_...")
    print("-" * 60)
    
    print("\n\n🔐 Also ensure these Stripe API keys are set:")
    print("-" * 60)
    print(f"STRIPE_SECRET_KEY={api_key[:12]}...")
    print(f"STRIPE_PUBLISHABLE_KEY=pk_{'test' if is_test else 'live'}_...")
    print("-" * 60)
    
    print("\n✅ Stripe setup complete! Copy the above values to your environment.\n")


def list_existing_products():
    """List existing Stripe products and prices."""
    api_key = os.getenv("STRIPE_SECRET_KEY")
    if not api_key:
        print("Error: STRIPE_SECRET_KEY environment variable not set.")
        sys.exit(1)
    
    stripe.api_key = api_key
    
    print("\n📦 Existing Products and Prices:\n")
    
    products = stripe.Product.list(active=True, limit=100)
    
    for product in products.data:
        print(f"Product: {product.name} ({product.id})")
        if product.metadata:
            print(f"  Metadata: {dict(product.metadata)}")
        
        prices = stripe.Price.list(product=product.id, active=True, limit=100)
        for price in prices.data:
            interval = price.recurring.interval if price.recurring else "one-time"
            amount = price.unit_amount / 100 if price.unit_amount else 0
            print(f"  └─ ${amount:.2f}/{interval} - {price.id} ({price.nickname or 'no nickname'})")
        print()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_existing_products()
    else:
        setup_stripe()
