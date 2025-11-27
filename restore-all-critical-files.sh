#!/bin/bash
# restore-all-critical-files.sh
# Restores all critical files that V0/Vercel might delete

set -e

echo "🔍 Checking for critical files..."

FILES_RESTORED=0

# Restore cloudbuild.yaml
if [ ! -f "cloudbuild.yaml" ]; then
    echo "❌ cloudbuild.yaml is missing! Restoring..."
    git checkout 896cc246 -- cloudbuild.yaml 2>/dev/null || \
    git checkout HEAD~10 -- cloudbuild.yaml 2>/dev/null || \
    echo "⚠️  Could not restore cloudbuild.yaml from git history"
    if [ -f "cloudbuild.yaml" ]; then
        git add cloudbuild.yaml
        FILES_RESTORED=$((FILES_RESTORED + 1))
        echo "✅ Restored cloudbuild.yaml"
    fi
else
    echo "✅ cloudbuild.yaml exists"
fi

# Restore Dockerfile
if [ ! -f "Dockerfile" ]; then
    echo "❌ Dockerfile is missing! Restoring..."
    git checkout 3bce4a1e -- Dockerfile 2>/dev/null || \
    git checkout HEAD~10 -- Dockerfile 2>/dev/null || \
    echo "⚠️  Could not restore Dockerfile from git history"
    if [ -f "Dockerfile" ]; then
        git add Dockerfile
        FILES_RESTORED=$((FILES_RESTORED + 1))
        echo "✅ Restored Dockerfile"
    fi
else
    echo "✅ Dockerfile exists"
fi

# Restore requirements.txt
if [ ! -f "llmhive/requirements.txt" ]; then
    echo "❌ llmhive/requirements.txt is missing! Restoring..."
    git checkout 3bce4a1e -- llmhive/requirements.txt 2>/dev/null || \
    git checkout HEAD~10 -- llmhive/requirements.txt 2>/dev/null || \
    echo "⚠️  Could not restore llmhive/requirements.txt from git history"
    if [ -f "llmhive/requirements.txt" ]; then
        git add llmhive/requirements.txt
        FILES_RESTORED=$((FILES_RESTORED + 1))
        echo "✅ Restored llmhive/requirements.txt"
    fi
else
    echo "✅ llmhive/requirements.txt exists"
fi

# Restore main.py
if [ ! -f "llmhive/src/llmhive/app/main.py" ]; then
    echo "❌ llmhive/src/llmhive/app/main.py is missing! Restoring..."
    git checkout 063aeed0 -- llmhive/src/llmhive/app/main.py 2>/dev/null || \
    git checkout 3bce4a1e -- llmhive/src/llmhive/app/main.py 2>/dev/null || \
    git checkout HEAD~10 -- llmhive/src/llmhive/app/main.py 2>/dev/null || \
    echo "⚠️  Could not restore llmhive/src/llmhive/app/main.py from git history"
    if [ -f "llmhive/src/llmhive/app/main.py" ]; then
        git add llmhive/src/llmhive/app/main.py
        FILES_RESTORED=$((FILES_RESTORED + 1))
        echo "✅ Restored llmhive/src/llmhive/app/main.py"
    fi
else
    echo "✅ llmhive/src/llmhive/app/main.py exists"
fi

if [ $FILES_RESTORED -gt 0 ]; then
    echo ""
    echo "✅ Restored $FILES_RESTORED file(s)"
    echo "💡 Run: git commit -m 'Restore critical files' && git push"
else
    echo ""
    echo "✅ All critical files are present"
fi

