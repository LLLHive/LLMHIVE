#!/bin/bash
# Fix GROK_API_KEY → GROQ_API_KEY typo in .env.local

echo "🔧 Fixing API key typo in .env.local..."
echo ""

cd "$(dirname "$0")/.." || exit 1

if [ ! -f .env.local ]; then
    echo "❌ Error: .env.local not found"
    exit 1
fi

# Check if GROK_API_KEY exists
if grep -q "^GROK_API_KEY=" .env.local; then
    echo "✅ Found GROK_API_KEY (typo)"
    
    # Create backup
    cp .env.local .env.local.backup
    echo "✅ Created backup: .env.local.backup"
    
    # Fix the typo
    sed -i.tmp 's/^GROK_API_KEY=/GROQ_API_KEY=/' .env.local
    rm .env.local.tmp 2>/dev/null
    
    echo "✅ Renamed GROK_API_KEY → GROQ_API_KEY"
    echo ""
    
    # Verify
    if grep -q "^GROQ_API_KEY=" .env.local; then
        echo "✅ Verification successful!"
        echo ""
        echo "GROQ_API_KEY is now set correctly in .env.local"
    else
        echo "❌ Verification failed - restoring backup"
        mv .env.local.backup .env.local
        exit 1
    fi
else
    echo "⚠️  GROK_API_KEY not found in .env.local"
    
    # Check if GROQ_API_KEY already exists
    if grep -q "^GROQ_API_KEY=" .env.local; then
        echo "✅ GROQ_API_KEY already exists (correct spelling)"
    else
        echo "❌ Neither GROK_API_KEY nor GROQ_API_KEY found"
        echo ""
        echo "Please add your Groq API key manually:"
        echo "  echo 'GROQ_API_KEY=your_key_here' >> .env.local"
    fi
fi

echo ""
echo "---"
echo "Next step: Test the multi-provider system"
echo "  python3 scripts/test_multi_provider.py"
