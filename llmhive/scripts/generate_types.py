#!/usr/bin/env python3
"""Generate TypeScript types from Pydantic models.

Usage:
    python scripts/generate_types.py > ../lib/api-types.ts
    python scripts/generate_types.py --output ../lib/api-types.ts
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, get_args, get_origin

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pydantic import BaseModel
from enum import Enum

# Import all Pydantic models from the app
from llmhive.app.models.orchestration import (
    ReasoningMode,
    ReasoningMethod,
    DomainPack,
    AgentMode,
    EliteStrategy,
    TuningOptions,
    CriteriaSettings,
    ChatMetadata,
    OrchestrationSettings,
    ChatRequest,
    AgentTrace,
    ChatResponse,
)

# Import router models
from llmhive.app.routers.agents import AgentInfo, AgentsResponse
from llmhive.app.routers.execute import ExecuteRequest, ExecuteResponse
from llmhive.app.routers.stubs import (
    FileAnalysisRequest, FileAnalysisResponse,
    ImageGenerationRequest, ImageGenerationResponse,
    DataVisualizationRequest, DataVisualizationResponse,
    CollaborationRequest, CollaborationResponse,
)
from llmhive.app.routers.reasoning_config import (
    ReasoningConfigRequest,
    ReasoningConfigResponse,
    ReasoningConfigSaveResponse,
)


def python_type_to_ts(python_type: Any) -> str:
    """Convert Python type annotation to TypeScript type."""
    import types
    from typing import Union
    
    origin = get_origin(python_type)
    args = get_args(python_type)
    
    # Handle Optional
    if origin is type(None):
        return "null"
    
    # Handle Union (including Optional) - check for UnionType as well
    is_union = origin is Union or (hasattr(types, 'UnionType') and isinstance(python_type, types.UnionType))
    if is_union and args:
        # Filter out NoneType
        non_none_args = [a for a in args if a is not type(None)]
        has_none = len(non_none_args) < len(args)
        
        if len(non_none_args) == 1:
            base_type = python_type_to_ts(non_none_args[0])
            return f"{base_type} | null" if has_none else base_type
        else:
            ts_types = [python_type_to_ts(a) for a in non_none_args]
            result = " | ".join(ts_types)
            return f"{result} | null" if has_none else result
    
    # Handle List
    if origin is list:
        if args:
            return f"Array<{python_type_to_ts(args[0])}>"
        return "Array<unknown>"
    
    # Handle Dict
    if origin is dict:
        if args and len(args) == 2:
            key_type = python_type_to_ts(args[0])
            value_type = python_type_to_ts(args[1])
            return f"Record<{key_type}, {value_type}>"
        return "Record<string, unknown>"
    
    # Handle basic types
    type_map = {
        str: "string",
        int: "number",
        float: "number",
        bool: "boolean",
        type(None): "null",
        Any: "unknown",
    }
    
    if python_type in type_map:
        return type_map[python_type]
    
    # Handle string type names
    if isinstance(python_type, str):
        # Handle Optional[X] as string representation
        if python_type.startswith("Optional["):
            inner = python_type[9:-1]  # Extract inner type
            return f"{python_type_to_ts(inner)} | null"
        if python_type == "str":
            return "string"
        if python_type in ("int", "float"):
            return "number"
        if python_type == "bool":
            return "boolean"
        if python_type.startswith("List[") or python_type.startswith("list["):
            inner = python_type[5:-1]
            return f"Array<{python_type_to_ts(inner)}>"
        if python_type.startswith("Dict[") or python_type.startswith("dict["):
            return "Record<string, unknown>"
        return python_type
    
    # Handle Pydantic models
    if isinstance(python_type, type) and issubclass(python_type, BaseModel):
        return python_type.__name__
    
    # Handle Enums
    if isinstance(python_type, type) and issubclass(python_type, Enum):
        return python_type.__name__
    
    # Default
    return "unknown"


def generate_enum(enum_class: type) -> str:
    """Generate TypeScript enum from Python Enum."""
    lines = [f"export type {enum_class.__name__} ="]
    values = [f'  | "{member.value}"' for member in enum_class]
    return lines[0] + "\n" + "\n".join(values)


def generate_interface(model_class: type) -> str:
    """Generate TypeScript interface from Pydantic model."""
    lines = [f"export interface {model_class.__name__} {{"]
    
    # Get field annotations
    annotations = {}
    for cls in model_class.__mro__:
        if hasattr(cls, "__annotations__"):
            annotations.update(cls.__annotations__)
    
    # Get field info for defaults
    model_fields = getattr(model_class, "model_fields", {})
    
    for field_name, field_type in annotations.items():
        if field_name.startswith("_"):
            continue
        
        ts_type = python_type_to_ts(field_type)
        field_info = model_fields.get(field_name)
        
        # Check if optional
        origin = get_origin(field_type)
        is_optional = origin is type(None) or (
            hasattr(field_info, "default") and field_info.default is not None
        )
        
        optional_marker = "?" if is_optional else ""
        
        # Get description if available
        description = ""
        if field_info and hasattr(field_info, "description") and field_info.description:
            description = f"  /** {field_info.description} */\n"
        
        lines.append(f"{description}  {field_name}{optional_marker}: {ts_type}")
    
    lines.append("}")
    return "\n".join(lines)


def generate_typescript_types() -> str:
    """Generate all TypeScript types."""
    output = []
    
    # Header
    output.append("""/**
 * Auto-generated TypeScript types from Pydantic models.
 * 
 * DO NOT EDIT MANUALLY - regenerate with:
 *   cd llmhive && python scripts/generate_types.py -o ../lib/api-types.ts
 * 
 * Generated from: llmhive/src/llmhive/app/models/orchestration.py
 */

/* eslint-disable @typescript-eslint/no-explicit-any */
""")
    
    # Generate enums
    enums = [
        ReasoningMode,
        ReasoningMethod,
        DomainPack,
        AgentMode,
        EliteStrategy,
    ]
    
    output.append("// ============================================================")
    output.append("// Enums")
    output.append("// ============================================================\n")
    
    for enum_class in enums:
        output.append(generate_enum(enum_class))
        output.append("")
    
    # Generate interfaces - orchestration models
    output.append("// ============================================================")
    output.append("// Orchestration Models")
    output.append("// ============================================================\n")
    
    orchestration_models = [
        TuningOptions,
        CriteriaSettings,
        ChatMetadata,
        OrchestrationSettings,
        AgentTrace,
        ChatRequest,
        ChatResponse,
    ]
    
    for model_class in orchestration_models:
        output.append(generate_interface(model_class))
        output.append("")
    
    # Generate interfaces - agent models
    output.append("// ============================================================")
    output.append("// Agent Models")
    output.append("// ============================================================\n")
    
    agent_models = [
        AgentInfo,
        AgentsResponse,
    ]
    
    for model_class in agent_models:
        output.append(generate_interface(model_class))
        output.append("")
    
    # Generate interfaces - execute models
    output.append("// ============================================================")
    output.append("// Execute Models")
    output.append("// ============================================================\n")
    
    execute_models = [
        ExecuteRequest,
        ExecuteResponse,
    ]
    
    for model_class in execute_models:
        output.append(generate_interface(model_class))
        output.append("")
    
    # Generate interfaces - stub models
    output.append("// ============================================================")
    output.append("// Stub/Feature Models")
    output.append("// ============================================================\n")
    
    stub_models = [
        FileAnalysisRequest,
        FileAnalysisResponse,
        ImageGenerationRequest,
        ImageGenerationResponse,
        DataVisualizationRequest,
        DataVisualizationResponse,
        CollaborationRequest,
        CollaborationResponse,
    ]
    
    for model_class in stub_models:
        output.append(generate_interface(model_class))
        output.append("")
    
    # Generate interfaces - reasoning config models
    output.append("// ============================================================")
    output.append("// Reasoning Config Models")
    output.append("// ============================================================\n")
    
    reasoning_models = [
        ReasoningConfigRequest,
        ReasoningConfigResponse,
        ReasoningConfigSaveResponse,
    ]
    
    for model_class in reasoning_models:
        output.append(generate_interface(model_class))
        output.append("")
    
    # Add error response type
    output.append("// ============================================================")
    output.append("// Error Response")
    output.append("// ============================================================\n")
    
    output.append("""export interface ErrorResponse {
  error: {
    code: string
    message: string
    details: Record<string, unknown>
    recoverable: boolean
  }
  correlation_id: string
  request_id: string | null
  timestamp: string
}
""")
    
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Generate TypeScript types from Pydantic models")
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file path (default: stdout)"
    )
    
    args = parser.parse_args()
    
    output = generate_typescript_types()
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"TypeScript types exported to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
