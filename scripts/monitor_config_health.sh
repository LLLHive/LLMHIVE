#!/bin/bash

################################################################################
# Config Health Monitoring Script
#
# Monitors the /api/v1/status/diagnostics/config endpoint for 48 hours
# to verify zero "API key not found" errors after Pydantic BaseSettings fix.
#
# Usage:
#   ./scripts/monitor_config_health.sh [URL] [INTERVAL_SECONDS] [DURATION_HOURS]
#
# Examples:
#   ./scripts/monitor_config_health.sh https://staging.llmhive.ai 300 48
#   ./scripts/monitor_config_health.sh http://localhost:8000 60 1
################################################################################

set -euo pipefail

# Configuration
TARGET_URL="${1:-https://staging.llmhive.ai}"
CHECK_INTERVAL="${2:-300}"  # Default: 5 minutes
DURATION_HOURS="${3:-48}"   # Default: 48 hours
LOG_DIR="logs"
LOG_FILE="$LOG_DIR/config_monitoring_$(date +%Y%m%d_%H%M%S).log"
ALERT_FILE="$LOG_DIR/config_alerts_$(date +%Y%m%d_%H%M%S).log"

# Create logs directory
mkdir -p "$LOG_DIR"

# Calculate total checks
TOTAL_CHECKS=$((DURATION_HOURS * 3600 / CHECK_INTERVAL))

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

################################################################################
# Helper Functions
################################################################################

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}$*${NC}"
    log "INFO" "$*"
}

log_success() {
    echo -e "${GREEN}$*${NC}"
    log "SUCCESS" "$*"
}

log_warning() {
    echo -e "${YELLOW}$*${NC}"
    log "WARNING" "$*"
}

log_error() {
    echo -e "${RED}$*${NC}"
    log "ERROR" "$*"
    echo "[$timestamp] $*" >> "$ALERT_FILE"
}

check_dependencies() {
    local missing=0
    
    if ! command -v curl &> /dev/null; then
        log_error "curl is not installed"
        missing=1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_error "jq is not installed (brew install jq)"
        missing=1
    fi
    
    if [ $missing -eq 1 ]; then
        exit 1
    fi
}

################################################################################
# Main Monitoring Loop
################################################################################

main() {
    log_info "========================================================================"
    log_info "Config Health Monitoring Started"
    log_info "========================================================================"
    log_info "Target URL: $TARGET_URL"
    log_info "Check Interval: ${CHECK_INTERVAL}s"
    log_info "Duration: ${DURATION_HOURS}h"
    log_info "Total Checks: $TOTAL_CHECKS"
    log_info "Log File: $LOG_FILE"
    log_info "Alert File: $ALERT_FILE"
    log_info "========================================================================"
    
    # Check dependencies
    check_dependencies
    
    # Statistics
    local total_checks=0
    local successful_checks=0
    local failed_checks=0
    local zero_provider_incidents=0
    
    # Start monitoring
    for ((i=1; i<=TOTAL_CHECKS; i++)); do
        timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        
        log_info "Check $i/$TOTAL_CHECKS..."
        
        # Make request to health check endpoint
        response=$(curl -s -w "\n%{http_code}" "$TARGET_URL/api/v1/status/diagnostics/config" 2>&1 || echo -e '{"error":"request_failed"}\n000')
        
        # Split response and HTTP code
        http_code=$(echo "$response" | tail -n1)
        response_body=$(echo "$response" | head -n-1)
        
        total_checks=$((total_checks + 1))
        
        # Check HTTP code
        if [ "$http_code" != "200" ]; then
            failed_checks=$((failed_checks + 1))
            log_error "HTTP $http_code - Request failed"
            continue
        fi
        
        # Parse response
        provider_count=$(echo "$response_body" | jq -r '.provider_count // 0' 2>/dev/null || echo "0")
        config_ok=$(echo "$response_body" | jq -r '.validation.is_valid // false' 2>/dev/null || echo "false")
        warnings=$(echo "$response_body" | jq -r '.validation.warnings_count // 0' 2>/dev/null || echo "0")
        config_system=$(echo "$response_body" | jq -r '.config_system // "unknown"' 2>/dev/null || echo "unknown")
        
        # Check if we're using Pydantic BaseSettings
        if [[ "$config_system" != *"Pydantic BaseSettings"* ]]; then
            log_warning "Config system: $config_system (expected Pydantic BaseSettings)"
        fi
        
        # Log result
        if [ "$provider_count" -eq 0 ]; then
            # CRITICAL: Zero providers = API key error!
            zero_provider_incidents=$((zero_provider_incidents + 1))
            failed_checks=$((failed_checks + 1))
            log_error "❌ ZERO PROVIDERS - API Key Error Detected!"
            log_error "   Timestamp: $timestamp"
            log_error "   HTTP Code: $http_code"
            log_error "   Response: $response_body"
            
            # Try to get more details
            warnings_detail=$(echo "$response_body" | jq -r '.validation.warnings[]' 2>/dev/null || echo "")
            if [ -n "$warnings_detail" ]; then
                log_error "   Warnings: $warnings_detail"
            fi
            
        else
            # Success
            successful_checks=$((successful_checks + 1))
            log_success "✓ OK - Providers: $provider_count, Valid: $config_ok, Warnings: $warnings"
        fi
        
        # Print progress
        success_rate=$(echo "scale=2; $successful_checks / $total_checks * 100" | bc)
        log_info "Progress: $i/$TOTAL_CHECKS ($success_rate% success rate)"
        
        # Sleep until next check (unless it's the last one)
        if [ $i -lt $TOTAL_CHECKS ]; then
            sleep "$CHECK_INTERVAL"
        fi
    done
    
    # Final summary
    log_info "========================================================================"
    log_info "Monitoring Complete"
    log_info "========================================================================"
    log_info "Duration: ${DURATION_HOURS}h"
    log_info "Total Checks: $total_checks"
    log_success "Successful: $successful_checks"
    log_error "Failed: $failed_checks"
    log_error "Zero Provider Incidents: $zero_provider_incidents"
    
    if [ $total_checks -gt 0 ]; then
        success_rate=$(echo "scale=2; $successful_checks / $total_checks * 100" | bc)
        log_info "Success Rate: $success_rate%"
    fi
    
    # Verdict
    if [ $zero_provider_incidents -eq 0 ]; then
        log_success "========================================================================"
        log_success "✅ SUCCESS: Zero API key errors detected!"
        log_success "Pydantic BaseSettings fix is working perfectly."
        log_success "Safe to deploy to production."
        log_success "========================================================================"
        exit 0
    else
        log_error "========================================================================"
        log_error "❌ FAILURE: $zero_provider_incidents API key error(s) detected"
        log_error "Review logs: $LOG_FILE"
        log_error "Review alerts: $ALERT_FILE"
        log_error "DO NOT deploy to production until resolved."
        log_error "========================================================================"
        exit 1
    fi
}

# Run main function
main
