#!/usr/bin/env python3
"""
LLMHive Techniques Knowledge Base Importer

Reads the seed file at:
  kb/llmhive_techniques_kb/seed/LLMHive_Techniques_KB_v1_seed.txt

Extracts CSV blocks, validates schema, and writes:
  kb/llmhive_techniques_kb/LLMHive_Techniques_KB_v1.json (required)
  kb/llmhive_techniques_kb/LLMHive_Techniques_KB_v1.xlsx (optional)

Usage:
    python scripts/import_llmhive_kb.py
    python scripts/import_llmhive_kb.py --validate-only
    python scripts/import_llmhive_kb.py --force
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Script directory
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent

# KB paths
KB_DIR = REPO_ROOT / "kb" / "llmhive_techniques_kb"
SEED_DIR = KB_DIR / "seed"
SEED_FILE = SEED_DIR / "LLMHive_Techniques_KB_v1_seed.txt"
OUTPUT_JSON = KB_DIR / "LLMHive_Techniques_KB_v1.json"
OUTPUT_XLSX = KB_DIR / "LLMHive_Techniques_KB_v1.xlsx"

# Required sections in seed file
REQUIRED_SECTIONS = [
    "README",
    "techniques",
    "architectures",
    "benchmarks",
    "benchmark_results",
    "evaluation_rubric",
    "rankings",
    "sources",
]

# Section schemas (required columns) - flexible to match actual data
SECTION_SCHEMAS = {
    "techniques": ["technique_id", "name"],  # category is optional
    "architectures": ["architecture_id", "pattern_name"],  # or "name"
    "benchmarks": ["benchmark_id", "name"],
    "benchmark_results": ["result_id", "benchmark_id", "technique_id"],
    "evaluation_rubric": ["rubric_id", "name"],  # rubric_id not criterion_id
    "rankings": ["ranking_id", "benchmark_id"],  # benchmark_id not category
    "sources": ["source_id", "title_or_reference"],  # title_or_reference not title
}

# Column name aliases (map expected -> actual)
COLUMN_ALIASES = {
    "name": ["name", "pattern_name", "title_or_reference"],
    "category": ["category", "benchmark_id"],
    "criterion_id": ["criterion_id", "rubric_id"],
}

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("kb_import")


def clean_text(text: str) -> str:
    """Remove contentReference artifacts and clean text."""
    if not text or not isinstance(text, str):
        return text or ""
    
    # Remove contentReference[oaicite:...] artifacts
    text = re.sub(r'contentReference\[oaicite:[^\]]+\]', '', text)
    
    # Remove other common artifacts
    text = re.sub(r'\[oaicite:[^\]]+\]', '', text)
    
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def parse_csv_block(content: str) -> List[Dict[str, str]]:
    """Parse a CSV block into list of dictionaries."""
    content = content.strip()
    if not content:
        return []
    
    # Use csv reader
    reader = csv.DictReader(io.StringIO(content))
    rows = []
    for row in reader:
        # Clean all values
        cleaned_row = {k: clean_text(v) for k, v in row.items()}
        rows.append(cleaned_row)
    
    return rows


def extract_sections(seed_content: str) -> Dict[str, Any]:
    """Extract CSV sections from seed file content."""
    sections = {}
    
    # Pattern to find section headers (e.g., "# techniques" or "## techniques" or just "techniques")
    section_pattern = r'^#{0,3}\s*(\w+)\s*$'
    
    lines = seed_content.split('\n')
    current_section = None
    current_content = []
    
    for line in lines:
        # Check for section header
        match = re.match(section_pattern, line.strip())
        if match:
            section_name = match.group(1).lower()
            
            # Save previous section if any
            if current_section and current_content:
                content = '\n'.join(current_content)
                if current_section == "readme":
                    sections[current_section] = content
                else:
                    sections[current_section] = parse_csv_block(content)
            
            current_section = section_name
            current_content = []
        else:
            if current_section:
                current_content.append(line)
    
    # Save last section
    if current_section and current_content:
        content = '\n'.join(current_content)
        if current_section == "readme":
            sections[current_section] = content
        else:
            sections[current_section] = parse_csv_block(content)
    
    return sections


def validate_section_schema(section_name: str, rows: List[Dict], schema: List[str]) -> List[str]:
    """Validate that a section has required columns."""
    errors = []
    
    if not rows:
        return [f"Section '{section_name}' is empty"]
    
    first_row_keys = set(rows[0].keys())
    missing_cols = set(schema) - first_row_keys
    
    if missing_cols:
        errors.append(f"Section '{section_name}' missing columns: {sorted(missing_cols)}")
    
    return errors


def generate_technique_source_map(techniques: List[Dict], sources: List[Dict]) -> List[Dict]:
    """Generate technique_source_map from techniques canonical_sources."""
    source_ids = {s.get("source_id") for s in sources if s.get("source_id")}
    technique_source_map = []
    map_id = 0
    
    for tech in techniques:
        technique_id = tech.get("technique_id")
        canonical_sources = tech.get("canonical_sources", "")
        
        if not technique_id:
            continue
        
        # Parse comma-separated source IDs
        if canonical_sources:
            for src_id in re.findall(r'SRC_\d+', canonical_sources):
                if src_id in source_ids:
                    map_id += 1
                    technique_source_map.append({
                        "map_id": f"TSM_{map_id:04d}",
                        "technique_id": technique_id,
                        "source_id": src_id,
                        "claim_supported": "canonical",
                    })
        
        # Also check summary_long for source references
        summary_long = tech.get("summary_long", "")
        for src_id in re.findall(r'SRC_\d+', summary_long):
            if src_id in source_ids:
                # Check if already added
                existing = [m for m in technique_source_map 
                           if m["technique_id"] == technique_id and m["source_id"] == src_id]
                if not existing:
                    map_id += 1
                    technique_source_map.append({
                        "map_id": f"TSM_{map_id:04d}",
                        "technique_id": technique_id,
                        "source_id": src_id,
                        "claim_supported": "evidence",
                    })
    
    return technique_source_map


def fix_missing_sources(sections: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Fix missing source references with placeholders."""
    fixes = []
    sources = sections.get("sources", [])
    source_ids = {s.get("source_id") for s in sources if s.get("source_id")}
    
    # Get max source ID
    max_src_id = 0
    for src_id in source_ids:
        match = re.match(r'SRC_(\d+)', src_id)
        if match:
            max_src_id = max(max_src_id, int(match.group(1)))
    
    # Fix techniques with missing canonical_sources
    techniques = sections.get("techniques", [])
    for tech in techniques:
        technique_id = tech.get("technique_id")
        canonical_sources = tech.get("canonical_sources", "")
        
        if not canonical_sources or not re.search(r'SRC_\d+', canonical_sources):
            max_src_id += 1
            new_src_id = f"SRC_{max_src_id:04d}"
            sources.append({
                "source_id": new_src_id,
                "title": f"TODO: canonical source for {tech.get('name', technique_id)}",
                "type": "placeholder",
                "url": "",
                "notes": f"TODO: add canonical source for technique {technique_id}",
            })
            source_ids.add(new_src_id)
            tech["canonical_sources"] = new_src_id
            fixes.append(f"Created placeholder source {new_src_id} for technique {technique_id}")
    
    # Fix benchmarks with missing source_id
    benchmarks = sections.get("benchmarks", [])
    for bench in benchmarks:
        benchmark_id = bench.get("benchmark_id")
        src_id = bench.get("source_id", "")
        
        if not src_id:
            max_src_id += 1
            new_src_id = f"SRC_{max_src_id:04d}"
            sources.append({
                "source_id": new_src_id,
                "title": f"TODO: benchmark definition for {bench.get('name', benchmark_id)}",
                "type": "placeholder",
                "url": "",
                "notes": f"TODO: add official benchmark definition source for {benchmark_id}",
            })
            source_ids.add(new_src_id)
            bench["source_id"] = new_src_id
            fixes.append(f"Created placeholder source {new_src_id} for benchmark {benchmark_id}")
    
    sections["sources"] = sources
    return sections, fixes


def validate_data_integrity(sections: Dict[str, Any]) -> List[str]:
    """Validate data integrity rules."""
    errors = []
    
    # Check every benchmark_results has source_id and date_reported
    benchmark_results = sections.get("benchmark_results", [])
    for result in benchmark_results:
        result_id = result.get("result_id", "unknown")
        if not result.get("source_id"):
            errors.append(f"benchmark_results {result_id} missing source_id")
        if not result.get("date_reported"):
            errors.append(f"benchmark_results {result_id} missing date_reported")
    
    return errors


def load_seed_file() -> Optional[str]:
    """Load and return seed file content."""
    if not SEED_FILE.exists():
        return None
    
    with open(SEED_FILE, "r", encoding="utf-8") as f:
        return f.read()


def save_json(data: Dict[str, Any], path: Path) -> None:
    """Save data as JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_xlsx(data: Dict[str, Any], path: Path) -> bool:
    """Save data as Excel (optional, requires openpyxl)."""
    try:
        import pandas as pd
        
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            for section_name, section_data in data.items():
                if section_name == "metadata":
                    continue
                if isinstance(section_data, list) and section_data:
                    df = pd.DataFrame(section_data)
                    df.to_excel(writer, sheet_name=section_name[:31], index=False)
                elif isinstance(section_data, str):
                    df = pd.DataFrame([{"content": section_data}])
                    df.to_excel(writer, sheet_name=section_name[:31], index=False)
        
        return True
    except ImportError:
        logger.warning("openpyxl/pandas not available, skipping Excel output")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="LLMHive Techniques Knowledge Base Importer"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate, don't write output files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output files",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose logging",
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Ensure KB directory exists
    KB_DIR.mkdir(parents=True, exist_ok=True)
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check for seed file
    seed_content = load_seed_file()
    if seed_content is None:
        logger.error("=" * 70)
        logger.error("SEED FILE NOT FOUND")
        logger.error("=" * 70)
        logger.error("")
        logger.error(f"Expected seed file at: {SEED_FILE}")
        logger.error("")
        logger.error("To fix, create the seed file with KB data in CSV format:")
        logger.error(f"  1. Create: {SEED_FILE}")
        logger.error("  2. Add sections: README, techniques, architectures, benchmarks, etc.")
        logger.error("  3. Re-run this script")
        logger.error("")
        logger.error("The seed file should contain sections like:")
        logger.error("  # README")
        logger.error("  <readme content>")
        logger.error("")
        logger.error("  # techniques")
        logger.error("  technique_id,name,category,subcategory,...")
        logger.error("  TECH_0001,Plan-Then-Execute,agentic_planning,...")
        logger.error("")
        
        # Write an empty scaffold JSON so the KB service can still initialize
        empty_kb = {
            "metadata": {
                "version": "1.0.0",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "empty",
                "error": "Seed file not found",
                "seed_file_path": str(SEED_FILE),
            },
            "README": "Seed file not found. Please add the KB seed file.",
            "techniques": [],
            "architectures": [],
            "benchmarks": [],
            "benchmark_results": [],
            "evaluation_rubric": [],
            "rankings": [],
            "sources": [],
            "technique_source_map": [],
        }
        save_json(empty_kb, OUTPUT_JSON)
        logger.info(f"Wrote empty scaffold JSON: {OUTPUT_JSON}")
        
        sys.exit(1)
    
    logger.info(f"Loaded seed file: {SEED_FILE} ({len(seed_content)} bytes)")
    
    # Extract sections
    sections = extract_sections(seed_content)
    logger.info(f"Extracted {len(sections)} sections: {list(sections.keys())}")
    
    # Check for missing required sections
    missing_sections = set(REQUIRED_SECTIONS) - set(sections.keys())
    if missing_sections:
        logger.warning(f"Missing sections (will be empty): {sorted(missing_sections)}")
        for section in missing_sections:
            sections[section] = [] if section != "README" else ""
    
    # Validate schemas
    errors = []
    for section_name, schema in SECTION_SCHEMAS.items():
        section_data = sections.get(section_name, [])
        if isinstance(section_data, list) and section_data:
            errors.extend(validate_section_schema(section_name, section_data, schema))
    
    if errors:
        logger.error("Schema validation errors:")
        for err in errors:
            logger.error(f"  - {err}")
    
    # Fix missing sources
    sections, fixes = fix_missing_sources(sections)
    if fixes:
        logger.info(f"Applied {len(fixes)} placeholder fixes:")
        for fix in fixes[:10]:
            logger.info(f"  - {fix}")
        if len(fixes) > 10:
            logger.info(f"  ... and {len(fixes) - 10} more")
    
    # Validate data integrity
    integrity_errors = validate_data_integrity(sections)
    if integrity_errors:
        logger.error("Data integrity errors:")
        for err in integrity_errors:
            logger.error(f"  - {err}")
        if not args.force:
            logger.error("Use --force to proceed despite errors")
            sys.exit(1)
    
    # Generate technique_source_map
    technique_source_map = generate_technique_source_map(
        sections.get("techniques", []),
        sections.get("sources", []),
    )
    sections["technique_source_map"] = technique_source_map
    logger.info(f"Generated {len(technique_source_map)} technique-source mappings")
    
    # Add metadata
    sections["metadata"] = {
        "version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "imported",
        "seed_file": str(SEED_FILE.name),
        "sections": list(sections.keys()),
        "row_counts": {
            k: len(v) if isinstance(v, list) else 1
            for k, v in sections.items()
            if k != "metadata"
        },
        "placeholder_fixes": len(fixes),
    }
    
    if args.validate_only:
        logger.info("Validation complete (--validate-only, no files written)")
        print(json.dumps(sections["metadata"], indent=2))
        sys.exit(0 if not integrity_errors else 1)
    
    # Check for existing output
    if OUTPUT_JSON.exists() and not args.force:
        logger.warning(f"Output file exists: {OUTPUT_JSON}")
        logger.warning("Use --force to overwrite")
        sys.exit(1)
    
    # Save JSON
    save_json(sections, OUTPUT_JSON)
    logger.info(f"Wrote JSON: {OUTPUT_JSON}")
    
    # Save Excel (optional)
    if save_xlsx(sections, OUTPUT_XLSX):
        logger.info(f"Wrote Excel: {OUTPUT_XLSX}")
    
    # Print summary
    print("")
    print("=" * 70)
    print("KB IMPORT COMPLETE")
    print("=" * 70)
    print(f"Sections: {len(sections) - 1}")  # -1 for metadata
    for name, data in sections.items():
        if name == "metadata":
            continue
        count = len(data) if isinstance(data, list) else 1
        print(f"  {name}: {count} rows")
    print(f"Placeholder fixes: {len(fixes)}")
    print(f"Output: {OUTPUT_JSON}")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
