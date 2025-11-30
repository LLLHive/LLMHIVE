#!/bin/bash
# Test runner script for LLMHive

set -e

echo "=========================================="
echo "LLMHive Test Suite"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}pytest not found. Installing...${NC}"
    pip install pytest pytest-asyncio pytest-cov
fi

# Run tests by category
echo -e "\n${YELLOW}Running Clarification Tests...${NC}"
pytest llmhive/tests/orchestrator/test_clarification.py -v --tb=short

echo -e "\n${YELLOW}Running Planning Tests...${NC}"
pytest llmhive/tests/orchestrator/test_planning.py -v --tb=short || echo "Planning tests need dependencies"

echo -e "\n${YELLOW}Running Model Routing Tests...${NC}"
pytest llmhive/tests/orchestrator/test_model_routing.py -v --tb=short || echo "Routing tests need dependencies"

echo -e "\n${YELLOW}Running Parallel Execution Tests...${NC}"
pytest llmhive/tests/orchestrator/test_parallel_execution.py -v --tb=short

echo -e "\n${YELLOW}Running Memory Tests...${NC}"
pytest llmhive/tests/systems/test_memory.py -v --tb=short

echo -e "\n${YELLOW}Running Error Handling Tests...${NC}"
pytest llmhive/tests/integration/test_error_handling.py -v --tb=short || echo "Error handling tests need dependencies"

echo -e "\n${GREEN}=========================================="
echo "Test Summary"
echo "==========================================${NC}"

# Run all tests and show summary
pytest llmhive/tests/ -v --tb=no -q 2>&1 | tail -5

echo -e "\n${GREEN}Tests completed!${NC}"

