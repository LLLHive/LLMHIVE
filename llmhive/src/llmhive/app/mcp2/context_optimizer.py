"""Context optimization for MCP 2.0.

This module handles filtering, summarizing, and optimizing data before
it's sent to the LLM, dramatically reducing token usage.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContextOptimizer:
    """Optimizes context by filtering and summarizing large outputs.
    
    Processes data in the sandbox and returns only concise summaries
    to the LLM, reducing token usage by up to 98%.
    """

    def __init__(self, max_output_tokens: int = 500):
        """Initialize context optimizer.
        
        Args:
            max_output_tokens: Maximum tokens to return to LLM (default: 500)
        """
        self.max_output_tokens = max_output_tokens
        # Rough estimate: 1 token ≈ 4 characters
        self.max_output_chars = max_output_tokens * 4
    
    def filter_large_output(
        self, data: Any, strategy: str = "summarize"
    ) -> str:
        """Filter large output to fit within token limits.
        
        Args:
            data: Data to filter (can be dict, list, string, etc.)
            strategy: Filtering strategy ("summarize", "truncate", "sample")
            
        Returns:
            Filtered/summarized data as string
        """
        data_str = self._serialize(data)
        
        if len(data_str) <= self.max_output_chars:
            return data_str
        
        if strategy == "summarize":
            return self._summarize(data, data_str)
        elif strategy == "truncate":
            return data_str[:self.max_output_chars] + "... [truncated]"
        elif strategy == "sample":
            return self._sample(data, data_str)
        else:
            return data_str[:self.max_output_chars] + "... [truncated]"
    
    def _serialize(self, data: Any) -> str:
        """Serialize data to string."""
        if isinstance(data, str):
            return data
        elif isinstance(data, (dict, list)):
            return json.dumps(data, indent=2)
        else:
            return str(data)
    
    def _summarize(self, data: Any, data_str: str) -> str:
        """Summarize large data structure.
        
        Args:
            data: Original data
            data_str: Serialized data string
            
        Returns:
            Summary string
        """
        if isinstance(data, list):
            if len(data) == 0:
                return "[]"
            
            # Show first few and last few items
            sample_size = min(3, len(data))
            first_items = data[:sample_size]
            last_items = data[-sample_size:] if len(data) > sample_size * 2 else []
            
            summary_parts = []
            summary_parts.append(f"List with {len(data)} items:")
            summary_parts.append(f"First {sample_size}: {json.dumps(first_items, indent=2)}")
            if last_items:
                summary_parts.append(f"Last {sample_size}: {json.dumps(last_items, indent=2)}")
            
            summary = "\n".join(summary_parts)
            if len(summary) > self.max_output_chars:
                return summary[:self.max_output_chars] + "... [truncated]"
            return summary
        
        elif isinstance(data, dict):
            # Show key count and sample entries
            key_count = len(data)
            sample_keys = list(data.keys())[:5]
            sample_dict = {k: data[k] for k in sample_keys}
            
            summary = f"Dictionary with {key_count} keys. Sample: {json.dumps(sample_dict, indent=2)}"
            if len(summary) > self.max_output_chars:
                return summary[:self.max_output_chars] + "... [truncated]"
            return summary
        
        else:
            # For strings, truncate intelligently
            if len(data_str) > self.max_output_chars:
                # Try to truncate at word boundary
                truncated = data_str[:self.max_output_chars]
                last_space = truncated.rfind(" ")
                if last_space > self.max_output_chars * 0.8:
                    truncated = truncated[:last_space]
                return truncated + "... [truncated]"
            return data_str
    
    def _sample(self, data: Any, data_str: str) -> str:
        """Sample data (e.g., first N rows of a table).
        
        Args:
            data: Original data
            data_str: Serialized data string
            
        Returns:
            Sampled data string
        """
        if isinstance(data, list):
            sample_size = min(10, len(data))
            sample = data[:sample_size]
            summary = f"Sample of {sample_size} items from {len(data)} total:\n"
            summary += json.dumps(sample, indent=2)
            if len(data) > sample_size:
                summary += f"\n... ({len(data) - sample_size} more items)"
            return summary
        
        # For other types, use summarize
        return self._summarize(data, data_str)
    
    def calculate_token_savings(
        self, original_size: int, filtered_size: int
    ) -> Dict[str, Any]:
        """Calculate token savings from filtering.
        
        Args:
            original_size: Original data size in characters
            filtered_size: Filtered data size in characters
            
        Returns:
            Dictionary with savings metrics
        """
        original_tokens = original_size // 4
        filtered_tokens = filtered_size // 4
        tokens_saved = original_tokens - filtered_tokens
        savings_percent = (tokens_saved / original_tokens * 100) if original_tokens > 0 else 0
        
        return {
            "original_tokens": original_tokens,
            "filtered_tokens": filtered_tokens,
            "tokens_saved": tokens_saved,
            "savings_percent": round(savings_percent, 2),
        }
    
    def optimize_multi_tool_workflow(
        self, tool_results: List[Dict[str, Any]]
    ) -> str:
        """Optimize results from a multi-tool workflow.
        
        Combines results from multiple tools and returns a concise summary.
        
        Args:
            tool_results: List of tool execution results
            
        Returns:
            Optimized summary string
        """
        if not tool_results:
            return "No results from tools."
        
        # Combine and summarize
        combined = {
            "tools_called": len(tool_results),
            "results": []
        }
        
        for result in tool_results:
            tool_name = result.get("tool", "unknown")
            status = result.get("status", "unknown")
            data = result.get("data", {})
            
            # Summarize each result
            data_summary = self.filter_large_output(data, strategy="summarize")
            
            combined["results"].append({
                "tool": tool_name,
                "status": status,
                "summary": data_summary[:200]  # Limit each summary
            })
        
        summary = json.dumps(combined, indent=2)
        
        # Ensure it fits within limits
        if len(summary) > self.max_output_chars:
            summary = self.filter_large_output(combined, strategy="summarize")
        
        return summary

