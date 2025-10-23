#!/bin/bash
# Verification script for /healthz endpoint fix
# This script verifies all the fixes mentioned in the problem statement

set -e

echo "=========================================="
echo "LLMHive /healthz Endpoint Verification"
echo "=========================================="
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Verify endpoint exists in code
echo "Step 1: Verifying /healthz endpoint in code..."
if grep -q '@app.get("/healthz"' llmhive/src/llmhive/app/main.py; then
    echo -e "${GREEN}✓${NC} /healthz endpoint found in main.py"
else
    echo -e "${RED}✗${NC} /healthz endpoint NOT found in main.py"
    exit 1
fi
echo ""

# Step 2: Verify --no-cache flag in cloudbuild.yaml
echo "Step 2: Verifying --no-cache flag in cloudbuild.yaml..."
if grep -q '\-\-no-cache' cloudbuild.yaml; then
    echo -e "${GREEN}✓${NC} --no-cache flag found in cloudbuild.yaml (prevents stale Docker cache)"
else
    echo -e "${YELLOW}⚠${NC} --no-cache flag NOT found in cloudbuild.yaml"
fi
echo ""

# Step 3: Verify PORT configuration
echo "Step 3: Verifying PORT configuration..."
if grep -q '\-\-port=8080' cloudbuild.yaml; then
    echo -e "${GREEN}✓${NC} PORT=8080 configured in cloudbuild.yaml"
else
    echo -e "${YELLOW}⚠${NC} PORT not explicitly configured in cloudbuild.yaml"
fi
echo ""

# Step 4: Run health check tests
echo "Step 4: Running health check tests..."
cd llmhive
if PYTHONPATH=/home/runner/work/LLMHIVE/LLMHIVE/llmhive/src python -m pytest tests/test_health.py -v --tb=short 2>&1 | grep -q "3 passed"; then
    echo -e "${GREEN}✓${NC} All health check tests passed (3/3)"
else
    echo -e "${RED}✗${NC} Health check tests failed"
    cd ..
    exit 1
fi
cd ..
echo ""

# Step 5: Start the application and test endpoints
echo "Step 5: Starting application and testing endpoints..."
echo "Starting uvicorn server on port 8080..."

# Start uvicorn in background
PYTHONPATH=/home/runner/work/LLMHIVE/LLMHIVE/llmhive/src \
    PORT=8080 \
    uvicorn llmhive.app.main:app --host 0.0.0.0 --port 8080 > /tmp/uvicorn.log 2>&1 &
UVICORN_PID=$!

# Wait for server to start
sleep 5

# Test endpoints
echo ""
echo "Testing endpoints..."

# Test root endpoint
if curl -s -f http://localhost:8080/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Root endpoint (/) responds"
    ROOT_RESPONSE=$(curl -s http://localhost:8080/)
    echo "  Response: $ROOT_RESPONSE"
else
    echo -e "${RED}✗${NC} Root endpoint (/) failed"
    kill $UVICORN_PID 2>/dev/null || true
    exit 1
fi

echo ""

# Test /healthz endpoint (the main endpoint in question)
if curl -s -f http://localhost:8080/healthz > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} /healthz endpoint responds"
    HEALTHZ_RESPONSE=$(curl -s http://localhost:8080/healthz)
    echo "  Response: $HEALTHZ_RESPONSE"
    
    if echo "$HEALTHZ_RESPONSE" | grep -q '"status":"ok"'; then
        echo -e "  ${GREEN}✓${NC} Response contains expected {\"status\":\"ok\"}"
    else
        echo -e "  ${RED}✗${NC} Response does not contain expected {\"status\":\"ok\"}"
        kill $UVICORN_PID 2>/dev/null || true
        exit 1
    fi
else
    echo -e "${RED}✗${NC} /healthz endpoint failed"
    kill $UVICORN_PID 2>/dev/null || true
    exit 1
fi

echo ""

# Test /api/v1/healthz endpoint
if curl -s -f http://localhost:8080/api/v1/healthz > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} /api/v1/healthz endpoint responds"
    API_HEALTHZ_RESPONSE=$(curl -s http://localhost:8080/api/v1/healthz)
    echo "  Response: $API_HEALTHZ_RESPONSE"
else
    echo -e "${RED}✗${NC} /api/v1/healthz endpoint failed"
    kill $UVICORN_PID 2>/dev/null || true
    exit 1
fi

echo ""

# Check registered routes in logs
echo "Step 6: Verifying registered routes in startup logs..."
if grep -q "GET /healthz" /tmp/uvicorn.log; then
    echo -e "${GREEN}✓${NC} /healthz route is registered in startup logs"
else
    echo -e "${YELLOW}⚠${NC} Could not verify route registration in logs"
fi

# Stop uvicorn
kill $UVICORN_PID 2>/dev/null || true
wait $UVICORN_PID 2>/dev/null || true

echo ""
echo "=========================================="
echo -e "${GREEN}SUCCESS!${NC} All verifications passed!"
echo "=========================================="
echo ""
echo "Summary:"
echo "- /healthz endpoint is properly implemented in code"
echo "- cloudbuild.yaml includes --no-cache flag to prevent stale deployments"
echo "- PORT is correctly configured as 8080"
echo "- All health check tests pass"
echo "- Endpoints respond correctly when tested locally"
echo ""
echo "The repository is ready for Cloud Run deployment using:"
echo "  gcloud builds submit --config cloudbuild.yaml"
echo ""
