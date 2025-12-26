#!/usr/bin/env python3
"""
LLMHive ModelDB Import Script - Backwards-compatible wrapper.

This script wraps the pipeline script for direct Firestore/Pinecone import.
Use this if you only want to import an existing Excel without updating it.

For the full workflow (update + import), use: run_modeldb_refresh.py

Usage:
    python llmhive_modeldb_import.py --excel path/to/models.xlsx
    python llmhive_modeldb_import.py --excel path/to/models.xlsx --dry-run
    python llmhive_modeldb_import.py --excel path/to/models.xlsx --firestore-only
"""
from __future__ import annotations

import sys
from pathlib import Path

# Import the pipeline module
script_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(script_dir))

from llmhive_modeldb_pipeline import main

if __name__ == "__main__":
    main()

