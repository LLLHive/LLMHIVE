#!/bin/bash

LOG_FILE="/Users/camilodiaz/LLMHIVE/benchmark_baseline_verification.log"

while true; do
    clear
    echo "======================================================================="
    echo "BASELINE VERIFICATION BENCHMARK - LIVE PROGRESS"
    echo "======================================================================="
    echo "Started: $(date)"
    echo ""
    
    # Check if process is still running
    if ps aux | grep -q "[r]un_category_benchmarks.py"; then
        echo "Status: ✅ RUNNING"
    else
        echo "Status: ⏹️  COMPLETED or STOPPED"
    fi
    
    echo ""
    echo "Latest Progress:"
    echo "-----------------------------------------------------------------------"
    tail -20 "$LOG_FILE" | grep -E "(CATEGORY|✅|❌|Category.*Score|Total Cost|Overall)" || echo "No progress yet..."
    echo ""
    echo "======================================================================="
    echo "Press Ctrl+C to stop monitoring (benchmark continues in background)"
    echo "Log file: $LOG_FILE"
    echo "======================================================================="
    
    sleep 30
done
