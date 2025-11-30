"""Math Plugin for LLMHive.

Provides advanced mathematical computation capabilities.

Features:
- Scientific calculations
- Symbolic math (expressions, equations)
- Statistics and probability
- Unit conversions

Usage:
    plugin = MathPlugin()
    await plugin.activate()
    
    # Calculate expression
    result = await plugin.calculate("sin(pi/4) + sqrt(2)")
    
    # Statistics
    stats = await plugin.statistics([1, 2, 3, 4, 5])
"""
from __future__ import annotations

import ast
import logging
import math
import operator
import re
import statistics as stats_module
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from ..base import (
    Plugin,
    PluginConfig,
    PluginTool,
    PluginCapability,
    PluginTier,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Safe Math Evaluator
# ==============================================================================

class SafeMathEvaluator:
    """Safely evaluate mathematical expressions using AST parsing."""
    
    # Allowed operators
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }
    
    # Allowed math functions
    FUNCTIONS = {
        # Trigonometric
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "atan2": math.atan2,
        "sinh": math.sinh,
        "cosh": math.cosh,
        "tanh": math.tanh,
        # Exponential/logarithmic
        "exp": math.exp,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        # Power/root
        "sqrt": math.sqrt,
        "pow": pow,
        "abs": abs,
        # Rounding
        "floor": math.floor,
        "ceil": math.ceil,
        "round": round,
        # Other
        "factorial": math.factorial,
        "gcd": math.gcd,
        "degrees": math.degrees,
        "radians": math.radians,
        # Min/max
        "min": min,
        "max": max,
    }
    
    # Constants
    CONSTANTS = {
        "pi": math.pi,
        "e": math.e,
        "tau": math.tau,
        "inf": math.inf,
    }
    
    def evaluate(self, expression: str) -> float:
        """Safely evaluate a mathematical expression."""
        # Preprocess expression
        expr = self._preprocess(expression)
        
        try:
            tree = ast.parse(expr, mode="eval")
            return self._eval_node(tree.body)
        except Exception as e:
            raise ValueError(f"Invalid expression: {e}")
    
    def _preprocess(self, expr: str) -> str:
        """Preprocess expression for evaluation."""
        # Replace ^ with **
        expr = expr.replace("^", "**")
        # Replace common notations
        expr = re.sub(r"(\d+)!", r"factorial(\1)", expr)
        return expr
    
    def _eval_node(self, node: ast.AST) -> float:
        """Recursively evaluate AST node."""
        if isinstance(node, ast.Constant):
            return float(node.value)
        
        if isinstance(node, ast.Num):  # Python 3.7 compatibility
            return float(node.n)
        
        if isinstance(node, ast.Name):
            if node.id in self.CONSTANTS:
                return self.CONSTANTS[node.id]
            raise ValueError(f"Unknown constant: {node.id}")
        
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self.OPERATORS:
                raise ValueError(f"Unsupported operator: {op_type}")
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return self.OPERATORS[op_type](left, right)
        
        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self.OPERATORS:
                raise ValueError(f"Unsupported operator: {op_type}")
            operand = self._eval_node(node.operand)
            return self.OPERATORS[op_type](operand)
        
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name not in self.FUNCTIONS:
                    raise ValueError(f"Unknown function: {func_name}")
                args = [self._eval_node(arg) for arg in node.args]
                return self.FUNCTIONS[func_name](*args)
        
        raise ValueError(f"Unsupported node type: {type(node)}")


# ==============================================================================
# Math Plugin
# ==============================================================================

class MathPlugin(Plugin):
    """Math Plugin for LLMHive.
    
    Provides advanced mathematical computation tools.
    
    Tools:
    - math_calculate: Evaluate mathematical expressions
    - math_statistics: Calculate statistics for a dataset
    - math_convert: Unit conversions
    - math_solve: Solve simple equations (when sympy available)
    """
    
    def __init__(self):
        config = PluginConfig(
            name="math",
            display_name="Mathematics",
            version="1.0.0",
            description="Advanced mathematical computations and statistics",
            author="LLMHive",
            domains=["math", "calculation", "statistics"],
            keywords=[
                "calculate", "math", "compute", "solve", "equation",
                "statistics", "average", "mean", "sum", "convert",
                "factorial", "sqrt", "sin", "cos", "log",
            ],
            min_tier=PluginTier.FREE,
            capabilities=[PluginCapability.TOOLS],
            enabled=True,
            auto_activate=True,
            priority=30,
        )
        super().__init__(config)
        
        self.evaluator = SafeMathEvaluator()
    
    async def initialize(self) -> bool:
        """Initialize Math plugin."""
        logger.info("Initializing Math plugin")
        return True
    
    def get_tools(self) -> List[PluginTool]:
        """Get math tools."""
        return [
            PluginTool(
                name="math_calculate",
                description="Evaluate a mathematical expression. Supports trigonometry, logarithms, powers, factorial, etc.",
                handler=self._tool_calculate,
                parameters={
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Mathematical expression (e.g., 'sin(pi/4) + sqrt(2)', '5! + 2^10')",
                        },
                    },
                    "required": ["expression"],
                },
                domains=["math", "calculation"],
                trigger_keywords=["calculate", "compute", "math", "evaluate"],
            ),
            PluginTool(
                name="math_statistics",
                description="Calculate statistics for a list of numbers (mean, median, std dev, etc.).",
                handler=self._tool_statistics,
                parameters={
                    "type": "object",
                    "properties": {
                        "numbers": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "List of numbers to analyze",
                        },
                    },
                    "required": ["numbers"],
                },
                domains=["math", "statistics"],
                trigger_keywords=["statistics", "average", "mean", "median", "std"],
            ),
            PluginTool(
                name="math_convert",
                description="Convert between units (length, weight, temperature, etc.).",
                handler=self._tool_convert,
                parameters={
                    "type": "object",
                    "properties": {
                        "value": {
                            "type": "number",
                            "description": "Value to convert",
                        },
                        "from_unit": {
                            "type": "string",
                            "description": "Source unit (e.g., 'km', 'celsius', 'kg')",
                        },
                        "to_unit": {
                            "type": "string",
                            "description": "Target unit (e.g., 'miles', 'fahrenheit', 'lbs')",
                        },
                    },
                    "required": ["value", "from_unit", "to_unit"],
                },
                domains=["math", "conversion"],
                trigger_keywords=["convert", "conversion", "unit", "transform"],
            ),
            PluginTool(
                name="math_prime_check",
                description="Check if a number is prime.",
                handler=self._tool_prime_check,
                parameters={
                    "type": "object",
                    "properties": {
                        "number": {
                            "type": "integer",
                            "description": "Number to check",
                        },
                    },
                    "required": ["number"],
                },
                domains=["math"],
                trigger_keywords=["prime", "is prime"],
            ),
        ]
    
    # -------------------------------------------------------------------------
    # Tool Handlers
    # -------------------------------------------------------------------------
    
    async def _tool_calculate(
        self,
        expression: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Handle math_calculate tool call."""
        try:
            result = self.evaluator.evaluate(expression)
            
            # Format result nicely
            if result == int(result):
                formatted = str(int(result))
            else:
                formatted = f"{result:.10g}"
            
            return {
                "success": True,
                "expression": expression,
                "result": result,
                "formatted": formatted,
            }
        except Exception as e:
            return {
                "success": False,
                "expression": expression,
                "error": str(e),
            }
    
    async def _tool_statistics(
        self,
        numbers: List[float],
        **kwargs,
    ) -> Dict[str, Any]:
        """Handle math_statistics tool call."""
        if not numbers:
            return {"success": False, "error": "Empty list"}
        
        try:
            result = {
                "success": True,
                "count": len(numbers),
                "sum": sum(numbers),
                "mean": stats_module.mean(numbers),
                "min": min(numbers),
                "max": max(numbers),
            }
            
            if len(numbers) >= 2:
                result["median"] = stats_module.median(numbers)
                result["stdev"] = stats_module.stdev(numbers)
                result["variance"] = stats_module.variance(numbers)
            
            if len(numbers) >= 4:
                result["quantiles"] = {
                    "q1": stats_module.quantiles(numbers, n=4)[0],
                    "q2": stats_module.quantiles(numbers, n=4)[1],
                    "q3": stats_module.quantiles(numbers, n=4)[2],
                }
            
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _tool_convert(
        self,
        value: float,
        from_unit: str,
        to_unit: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Handle math_convert tool call."""
        conversions = {
            # Length
            ("km", "miles"): lambda x: x * 0.621371,
            ("miles", "km"): lambda x: x * 1.60934,
            ("m", "feet"): lambda x: x * 3.28084,
            ("feet", "m"): lambda x: x * 0.3048,
            ("cm", "inches"): lambda x: x * 0.393701,
            ("inches", "cm"): lambda x: x * 2.54,
            
            # Weight
            ("kg", "lbs"): lambda x: x * 2.20462,
            ("lbs", "kg"): lambda x: x * 0.453592,
            ("g", "oz"): lambda x: x * 0.035274,
            ("oz", "g"): lambda x: x * 28.3495,
            
            # Temperature
            ("celsius", "fahrenheit"): lambda x: x * 9/5 + 32,
            ("fahrenheit", "celsius"): lambda x: (x - 32) * 5/9,
            ("celsius", "kelvin"): lambda x: x + 273.15,
            ("kelvin", "celsius"): lambda x: x - 273.15,
            
            # Volume
            ("liters", "gallons"): lambda x: x * 0.264172,
            ("gallons", "liters"): lambda x: x * 3.78541,
            
            # Area
            ("sqm", "sqft"): lambda x: x * 10.7639,
            ("sqft", "sqm"): lambda x: x * 0.092903,
        }
        
        # Normalize unit names
        from_unit = from_unit.lower().strip()
        to_unit = to_unit.lower().strip()
        
        # Try to find conversion
        key = (from_unit, to_unit)
        if key in conversions:
            result = conversions[key](value)
            return {
                "success": True,
                "original": value,
                "from_unit": from_unit,
                "result": round(result, 6),
                "to_unit": to_unit,
            }
        
        return {
            "success": False,
            "error": f"Conversion from {from_unit} to {to_unit} not supported",
            "supported_conversions": [
                f"{f} -> {t}" for f, t in conversions.keys()
            ],
        }
    
    async def _tool_prime_check(
        self,
        number: int,
        **kwargs,
    ) -> Dict[str, Any]:
        """Handle math_prime_check tool call."""
        def is_prime(n: int) -> bool:
            if n < 2:
                return False
            if n == 2:
                return True
            if n % 2 == 0:
                return False
            for i in range(3, int(n**0.5) + 1, 2):
                if n % i == 0:
                    return False
            return True
        
        result = is_prime(number)
        
        return {
            "success": True,
            "number": number,
            "is_prime": result,
            "message": f"{number} is {'a prime' if result else 'not a prime'} number",
        }


# Plugin manifest
PLUGIN_MANIFEST = {
    "name": "math",
    "display_name": "Mathematics",
    "version": "1.0.0",
    "description": "Advanced mathematical computations and statistics",
    "author": "LLMHive",
    "domains": ["math", "calculation", "statistics"],
    "keywords": ["calculate", "math", "compute", "solve", "statistics"],
    "min_tier": "free",
    "capabilities": ["tools"],
    "entry_point": "math_plugin.py",
    "plugin_class": "MathPlugin",
    "enabled": True,
    "auto_activate": True,
    "priority": 30,
}

