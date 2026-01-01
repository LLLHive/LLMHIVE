#!/usr/bin/env python3
"""
Stripe Setup Script for LLMHive

This script creates all necessary Stripe products and prices for LLMHive subscriptions.
Run this once to set up your Stripe account, then copy the price IDs to your environment variables.

Usage:
    # Set your Stripe secret key first
    export STRIPE_SECRET_KEY=sk_live_...  # or sk_test_... for testing
    
    # Run the script
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


# Configuration - these match the pricing in pricing.py
PRODUCTS = [
    {
        "name": "LLMHive Pro",
        "description": "For professionals and small teams. 10,000 requests/month, 10M tokens, advanced orchestration features.",
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
        "name": "LLMHive Enterprise",
        "description": "For large organizations. Unlimited requests and tokens, SSO, SLA, dedicated support.",
        "prices": [
            {
                "nickname": "Enterprise Monthly",
                "unit_amount": 19999,  # $199.99 in cents
                "currency": "usd",
                "recurring": {"interval": "month"},
                "env_var": "STRIPE_PRICE_ID_ENTERPRISE_MONTHLY",
            },
            {
                "nickname": "Enterprise Annual",
                "unit_amount": 199999,  # $1,999.99 in cents
                "currency": "usd",
                "recurring": {"interval": "year"},
                "env_var": "STRIPE_PRICE_ID_ENTERPRISE_ANNUAL",
            },
        ],
    },
]


def setup_stripe():
    """Set up Stripe products and prices."""
    
    # Check for API key
    api_key = os.getenv("STRIPE_SECRET_KEY")
    if not api_key:
        print("Error: STRIPE_SECRET_KEY environment variable not set.")
        print("Run: export STRIPE_SECRET_KEY=sk_live_... (or sk_test_... for testing)")
        sys.exit(1)
    
    stripe.api_key = api_key
    
    # Determine environment
    is_test = api_key.startswith("sk_test_")
    env_type = "TEST" if is_test else "PRODUCTION"
    
    print(f"\n{'='*60}")
    print(f"  LLMHive Stripe Setup - {env_type} Environment")
    print(f"{'='*60}\n")
    
    if not is_test:
        print("⚠️  WARNING: You are using PRODUCTION keys!")
        confirm = input("Type 'yes' to continue: ")
        if confirm.lower() != "yes":
            print("Aborted.")
            sys.exit(0)
    
    created_prices = {}
    
    for product_config in PRODUCTS:
        print(f"\n📦 Creating product: {product_config['name']}")
        
        # Check if product already exists
        existing_products = stripe.Product.search(
            query=f"name:'{product_config['name']}'",
            limit=1,
        )
        
        if existing_products.data:
            product = existing_products.data[0]
            print(f"   ✓ Product already exists: {product.id}")
        else:
            # Create the product
            product = stripe.Product.create(
                name=product_config["name"],
                description=product_config["description"],
                metadata={
                    "app": "llmhive",
                    "created_by": "stripe_setup.py",
                },
            )
            print(f"   ✓ Created product: {product.id}")
        
        # Create prices for this product
        for price_config in product_config["prices"]:
            print(f"\n   💰 Creating price: {price_config['nickname']}")
            
            # Check if price already exists for this product
            existing_prices = stripe.Price.list(
                product=product.id,
                active=True,
                limit=100,
            )
            
            # Find matching price
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
                # Create the price
                price = stripe.Price.create(
                    product=product.id,
                    nickname=price_config["nickname"],
                    unit_amount=price_config["unit_amount"],
                    currency=price_config["currency"],
                    recurring=price_config["recurring"],
                    metadata={
                        "app": "llmhive",
                        "tier": price_config["nickname"].split()[0].lower(),  # "pro" or "enterprise"
                        "interval": price_config["recurring"]["interval"],
                    },
                )
                print(f"      ✓ Created price: {price.id}")
                created_prices[price_config["env_var"]] = price.id
    
    # Create webhook endpoint suggestion
    print(f"\n{'='*60}")
    print("  Setup Complete!")
    print(f"{'='*60}\n")
    
    print("📋 Add these environment variables to Vercel:\n")
    print("-" * 50)
    for env_var, price_id in created_prices.items():
        print(f"{env_var}={price_id}")
    print("-" * 50)
    
    print("\n\n🔗 Webhook Setup Required:")
    print("-" * 50)
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
    print("-" * 50)
    
    print("\n\n🔐 Also add your Stripe API keys to Vercel:")
    print("-" * 50)
    print(f"STRIPE_SECRET_KEY={api_key[:12]}...")
    print(f"STRIPE_PUBLISHABLE_KEY=pk_{'test' if is_test else 'live'}_...")
    print("-" * 50)
    
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

