#!/usr/bin/env python3
"""
Stripe Setup Script for LLMHive - PAID TIERS ONLY (January 2026)

This script creates all necessary Stripe products and prices for LLMHive subscriptions.
Run this once to set up your Stripe account, then copy the price IDs to your environment variables.

PAID PRICING STRUCTURE:
- Standard ($10): elite orchestration while spend guard allows, then free
- Premium ($20): elite orchestration while spend guard allows, then free
- Enterprise ($35/seat, 1+ seats): 400 ELITE + 400 STANDARD = 800/seat
- Maximum ($499): UNLIMITED (never throttle)

NOTE: The FREE tier is permanent and handled outside Stripe.

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


# PAID TIERS ONLY (FREE tier is not billed)
PRODUCTS = [
    {
        "name": "LLMHive Standard",
        "description": "Standard plan at $10/month. Elite orchestration while the spend guard allows, then free orchestration.",
        "metadata": {
            "tier": "lite",
            "spend_guard": "enabled",
            "after_quota": "free",
        },
        "prices": [
            {
                "nickname": "Standard Monthly",
                "unit_amount": 1000,  # $10.00 in cents
                "currency": "usd",
                "recurring": {"interval": "month"},
                "env_var": "STRIPE_PRICE_ID_STANDARD_MONTHLY",
            },
            {
                "nickname": "Standard Annual",
                "unit_amount": 10000,  # $100.00 in cents
                "currency": "usd",
                "recurring": {"interval": "year"},
                "env_var": "STRIPE_PRICE_ID_STANDARD_ANNUAL",
            },
        ],
    },
    {
        "name": "LLMHive Premium",
        "description": "Premium plan at $20/month. Elite orchestration while the spend guard allows, then free orchestration.",
        "metadata": {
            "tier": "pro",
            "spend_guard": "enabled",
            "after_quota": "free",
        },
        "prices": [
            {
                "nickname": "Premium Monthly",
                "unit_amount": 2000,  # $20.00 in cents
                "currency": "usd",
                "recurring": {"interval": "month"},
                "env_var": "STRIPE_PRICE_ID_PREMIUM_MONTHLY",
            },
            {
                "nickname": "Premium Annual",
                "unit_amount": 20000,  # $200.00 in cents
                "currency": "usd",
                "recurring": {"interval": "year"},
                "env_var": "STRIPE_PRICE_ID_PREMIUM_ANNUAL",
            },
        ],
    },
    {
        "name": "LLMHive Enterprise",
        "description": "Enterprise plan at $35/seat/month. SSO, compliance, flagship model pick. Same spend guard as Standard and Premium. 400 ELITE + 400 STANDARD per seat.",
        "metadata": {
            "tier": "enterprise",
            "elite_queries_per_seat": "400",
            "standard_queries_per_seat": "400",
            "total_queries_per_seat": "800",
            "min_seats": "1",
            "spend_guard": "enabled",
        },
        "prices": [
            {
                "nickname": "Enterprise Monthly (per seat)",
                "unit_amount": 3500,  # $35.00 per seat in cents
                "currency": "usd",
                "recurring": {"interval": "month"},
                "env_var": "STRIPE_PRICE_ID_ENTERPRISE_MONTHLY",
            },
            {
                "nickname": "Enterprise Annual (per seat)",
                "unit_amount": 35000,  # $350.00 per seat in cents (~17% discount)
                "currency": "usd",
                "recurring": {"interval": "year"},
                "env_var": "STRIPE_PRICE_ID_ENTERPRISE_ANNUAL",
            },
        ],
    },
]


def setup_stripe():
    """Create all products and prices in Stripe."""
    api_key = os.environ.get("STRIPE_SECRET_KEY")
    if not api_key:
        print("Error: STRIPE_SECRET_KEY environment variable not set")
        print("Usage: export STRIPE_SECRET_KEY=sk_... && python scripts/stripe_setup.py")
        sys.exit(1)
    
    stripe.api_key = api_key
    
    print("=" * 70)
    print("LLMHive Stripe Setup - PAID TIERS ONLY (January 2026)")
    print("=" * 70)
    print()
    
    env_vars = {}
    
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
            product = stripe.Product.create(
                name=product_config["name"],
                description=product_config["description"],
                metadata=product_config["metadata"],
            )
            print(f"   ✓ Product created: {product.id}")
        
        # Create prices
        for price_config in product_config["prices"]:
            print(f"   💰 Creating price: {price_config['nickname']}")
            
            price = stripe.Price.create(
                product=product.id,
                nickname=price_config["nickname"],
                unit_amount=price_config["unit_amount"],
                currency=price_config["currency"],
                recurring=price_config["recurring"],
            )
            
            env_var = price_config["env_var"]
            env_vars[env_var] = price.id
            print(f"      ✓ Price created: {price.id}")
    
    # Print environment variables
    print("\n" + "=" * 70)
    print("✅ Setup complete! Add these to your .env file:")
    print("=" * 70)
    print()
    
    for var, value in env_vars.items():
        print(f"{var}={value}")
    
    print()
    print("=" * 70)
    print("PAID TIERS PRICING SUMMARY:")
    print("=" * 70)
    print("""
| Tier       | Monthly  | Annual    | ELITE Queries | After Quota  | Features            |
|------------|----------|-----------|---------------|--------------|---------------------|
| Lite       | $14.99   | $149.99   | 100           | → FREE       | Knowledge base      |
| Pro        | $29.99   | $299.99   | 500           | → FREE       | API + All features  |
| Enterprise | $35/seat | $350/seat | 400/seat      | → FREE       | SSO + Compliance    |

Enterprise is available from a single seat ($35/mo); add seats anytime in Stripe checkout.
FREE tier is permanent (no Stripe product) with 50 queries/month using free models.
    """)


if __name__ == "__main__":
    setup_stripe()
