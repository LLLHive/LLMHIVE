#!/usr/bin/env python3
"""Export OpenAPI specification from FastAPI application.

Usage:
    python scripts/export_openapi.py > docs/openapi.json
    python scripts/export_openapi.py --yaml > docs/openapi.yaml
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llmhive.app.main import app


def export_openapi(format: str = "json") -> str:
    """Export OpenAPI spec from FastAPI app."""
    openapi_schema = app.openapi()
    
    # Add examples to improve documentation
    enhance_openapi_schema(openapi_schema)
    
    if format == "yaml":
        try:
            import yaml
            return yaml.dump(openapi_schema, default_flow_style=False, sort_keys=False)
        except ImportError:
            print("PyYAML not installed. Use: pip install pyyaml", file=sys.stderr)
            sys.exit(1)
    else:
        return json.dumps(openapi_schema, indent=2)


def enhance_openapi_schema(schema: dict) -> None:
    """Add additional examples and descriptions to the schema."""
    # Add server information
    schema["servers"] = [
        {"url": "http://localhost:8080", "description": "Local development"},
        {"url": "https://api.llmhive.ai", "description": "Production API"},
    ]
    
    # Add tags descriptions
    schema["tags"] = [
        {
            "name": "chat",
            "description": "Chat orchestration endpoints for multi-model LLM interactions"
        },
        {
            "name": "agents",
            "description": "Available LLM models and their capabilities"
        },
        {
            "name": "execute",
            "description": "Code execution in sandboxed environment"
        },
        {
            "name": "reasoning",
            "description": "Reasoning mode configuration"
        },
        {
            "name": "stubs",
            "description": "Placeholder endpoints for future features"
        },
    ]
    
    # Add security scheme
    schema["components"] = schema.get("components", {})
    schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for authentication"
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "description": "JWT token authentication"
        }
    }
    
    # Add global security requirement
    schema["security"] = [
        {"ApiKeyAuth": []},
        {"BearerAuth": []}
    ]


def main():
    parser = argparse.ArgumentParser(description="Export OpenAPI specification")
    parser.add_argument(
        "--yaml", 
        action="store_true", 
        help="Export as YAML instead of JSON"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file path (default: stdout)"
    )
    
    args = parser.parse_args()
    
    format = "yaml" if args.yaml else "json"
    output = export_openapi(format)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"OpenAPI spec exported to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
