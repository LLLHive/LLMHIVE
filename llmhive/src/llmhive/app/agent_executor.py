"""Autonomous Agent Executor for LLMHive.

This module implements an AutoGPT-like agent that can:
- Iteratively plan and execute tool calls in a loop
- Maintain a scratchpad of intermediate results
- Break down complex tasks into steps
- Integrate tool results back into LLM context
- Handle multi-step problem solving autonomously

The agent operates in a REPL-like loop:
1. LLM receives task + context (including previous results)
2. LLM outputs thought/action (possibly a tool request)
3. If tool request: execute tool, add result to context, goto 1
4. If final answer: return result

Example flow for "What is 5! + sqrt(16)?":
1. Agent thinks: "I need to calculate this"
2. Agent: [TOOL:calculator] factorial(5) + sqrt(16)
3. Tool returns: 124
4. Agent: "The answer is 124"

Usage:
    executor = AgentExecutor(providers, tool_broker)
    result = await executor.execute("Find population of France in 1900, 1950, 2000")
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


# ==============================================================================
# Types and Configuration
# ==============================================================================

class AgentAction(str, Enum):
    """Types of agent actions."""
    THINK = "think"  # Internal reasoning
    TOOL_CALL = "tool_call"  # Request to use a tool
    ANSWER = "answer"  # Final answer
    ERROR = "error"  # Error state


class AgentStatus(str, Enum):
    """Status of agent execution."""
    RUNNING = "running"
    COMPLETED = "completed"
    MAX_ITERATIONS = "max_iterations"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class AgentStep:
    """A single step in the agent's execution."""
    step_number: int
    action: AgentAction
    content: str
    tool_name: Optional[str] = None
    tool_args: Optional[str] = None
    tool_result: Optional[str] = None
    thought: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tokens_used: int = 0
    latency_ms: float = 0.0


@dataclass(slots=True)
class AgentExecutionResult:
    """Result of agent execution."""
    success: bool
    final_answer: str
    status: AgentStatus
    steps: List[AgentStep] = field(default_factory=list)
    total_iterations: int = 0
    total_tool_calls: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    scratchpad_summary: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    @property
    def tool_calls_made(self) -> List[Dict[str, str]]:
        """Get list of tool calls made."""
        return [
            {"tool": s.tool_name, "args": s.tool_args, "result": s.tool_result}
            for s in self.steps
            if s.action == AgentAction.TOOL_CALL and s.tool_name
        ]


# Tier-based limits for agent execution
# SIMPLIFIED 4-TIER STRUCTURE (January 2026): Lite, Pro, Enterprise, Maximum
AGENT_TIER_LIMITS = {
    "lite": {
        "max_iterations": 5,
        "max_tool_calls": 3,
        "max_tokens_per_step": 1500,
        "allowed_tools": {"calculator", "web_search", "knowledge_lookup"},
        "timeout_seconds": 60,
    },
    "pro": {
        "max_iterations": 10,
        "max_tool_calls": 8,
        "max_tokens_per_step": 2000,
        "allowed_tools": {"calculator", "web_search", "knowledge_lookup", "python_exec", 
                         "analyze_image", "generate_image", "transcribe_audio"},
        "timeout_seconds": 120,
    },
    "enterprise": {
        "max_iterations": 25,
        "max_tool_calls": 20,
        "max_tokens_per_step": 4000,
        "allowed_tools": {"calculator", "web_search", "knowledge_lookup", "python_exec",
                         "api_call", "advanced_search", "analyze_image", "generate_image",
                         "transcribe_audio", "synthesize_speech"},
        "timeout_seconds": 300,
    },
    "maximum": {
        "max_iterations": 50,
        "max_tool_calls": 40,
        "max_tokens_per_step": 8000,
        "allowed_tools": {"calculator", "web_search", "knowledge_lookup", "python_exec",
                         "api_call", "advanced_search", "analyze_image", "generate_image",
                         "transcribe_audio", "synthesize_speech", "custom_integrations"},
        "timeout_seconds": 600,
    },
    "free": {
        "max_iterations": 3,
        "max_tool_calls": 2,
        "max_tokens_per_step": 1000,
        "allowed_tools": {"calculator", "web_search"},
        "timeout_seconds": 30,
    },
}


# ==============================================================================
# Agent Scratchpad
# ==============================================================================

class AgentScratchpad:
    """Scratchpad for storing intermediate agent state.
    
    The scratchpad maintains:
    - Current task/goal
    - History of thoughts and actions
    - Tool call results
    - Accumulated context for the LLM
    """
    
    def __init__(self, initial_task: str):
        self.task = initial_task
        self.thoughts: List[str] = []
        self.actions: List[Dict[str, Any]] = []
        self.tool_results: Dict[str, Any] = {}
        self.context_accumulator: List[str] = []
        self.variables: Dict[str, Any] = {}
        self._created_at = datetime.now(timezone.utc)
    
    def add_thought(self, thought: str) -> None:
        """Add a thought/reasoning step."""
        self.thoughts.append(thought)
        self.context_accumulator.append(f"Thought: {thought}")
    
    def add_action(self, action: str, tool: Optional[str] = None, args: Optional[str] = None) -> None:
        """Add an action taken."""
        self.actions.append({
            "action": action,
            "tool": tool,
            "args": args,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if tool:
            self.context_accumulator.append(f"Action: Use tool '{tool}' with: {args}")
    
    def add_tool_result(self, tool_name: str, result: Any) -> None:
        """Add a tool execution result."""
        result_str = str(result)[:1000]  # Limit result size
        self.tool_results[f"{tool_name}_{len(self.tool_results)}"] = result
        self.context_accumulator.append(f"Result from {tool_name}: {result_str}")
    
    def set_variable(self, key: str, value: Any) -> None:
        """Store a variable for later use."""
        self.variables[key] = value
    
    def get_variable(self, key: str) -> Any:
        """Retrieve a stored variable."""
        return self.variables.get(key)
    
    def get_context(self, max_length: int = 4000) -> str:
        """Get accumulated context for LLM."""
        context = "\n".join(self.context_accumulator)
        if len(context) > max_length:
            # Truncate older context, keep recent
            context = "... (earlier context truncated) ...\n" + context[-max_length:]
        return context
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of scratchpad state."""
        return {
            "task": self.task,
            "num_thoughts": len(self.thoughts),
            "num_actions": len(self.actions),
            "num_tool_results": len(self.tool_results),
            "variables": list(self.variables.keys()),
        }
    
    def clear(self) -> None:
        """Clear the scratchpad (except initial task)."""
        self.thoughts.clear()
        self.actions.clear()
        self.tool_results.clear()
        self.context_accumulator.clear()
        self.variables.clear()


# ==============================================================================
# Agent Prompts
# ==============================================================================

AGENT_SYSTEM_PROMPT = """You are an autonomous AI agent that can solve complex tasks step by step.

You have access to the following tools:
{tool_descriptions}

When you need to use a tool, output EXACTLY this format:
[TOOL:tool_name] arguments

After receiving a tool result, continue reasoning toward the final answer.

When you have the final answer, output EXACTLY:
[ANSWER] Your final answer here

Rules:
1. Think step by step before using tools
2. Use tools only when necessary
3. After each tool result, decide if you need more tools or can answer
4. Always provide a final [ANSWER] when done
5. Be concise but thorough

Current task: {task}

Previous context (if any):
{context}

Now proceed with the task. Think about what you need to do, use tools if needed, and provide your answer."""


AGENT_CONTINUATION_PROMPT = """You are continuing to work on the task: {task}

Previous actions and results:
{context}

What should you do next? If you have enough information, provide [ANSWER]. Otherwise, use a tool or think more."""


def build_tool_descriptions(tool_broker: Any) -> str:
    """Build tool descriptions for the agent prompt."""
    descriptions = []
    
    for name, defn in tool_broker.tool_definitions.items():
        desc = f"- {name}: {defn.description}"
        if defn.parameters:
            params = ", ".join(f"{k}: {v}" for k, v in defn.parameters.items())
            desc += f" (Parameters: {params})"
        descriptions.append(desc)
    
    return "\n".join(descriptions) if descriptions else "No tools available."


# ==============================================================================
# Agent Executor
# ==============================================================================

class AgentExecutor:
    """Autonomous agent executor for multi-step problem solving.
    
    This executor implements an AutoGPT-like loop:
    1. Present task to LLM with available tools
    2. LLM outputs thought/action
    3. If tool request: execute and add result to context
    4. If final answer: return result
    5. Repeat until done or max iterations
    
    Features:
    - Iterative tool planning and execution
    - Scratchpad for intermediate results
    - Tier-based limits on iterations and tool calls
    - Automatic stopping when answer is found
    - Comprehensive execution tracking
    
    Usage:
        executor = AgentExecutor(providers, tool_broker)
        result = await executor.execute(
            "Calculate 5! + sqrt(16)",
            user_tier="pro",
        )
    """
    
    # Patterns for parsing agent output
    TOOL_PATTERN = re.compile(r'\[TOOL:(\w+)\]\s*(.+?)(?=\[TOOL:|\[ANSWER\]|$)', re.DOTALL | re.IGNORECASE)
    ANSWER_PATTERN = re.compile(r'\[ANSWER\]\s*(.+?)$', re.DOTALL | re.IGNORECASE)
    THOUGHT_PATTERN = re.compile(r'(?:Thought|Thinking|I need to|Let me|First,):\s*(.+?)(?=\[|$)', re.DOTALL | re.IGNORECASE)
    
    def __init__(
        self,
        providers: Dict[str, Any],
        tool_broker: Any,
        *,
        default_model: str = "gpt-4o",
        verbose: bool = False,
    ):
        """
        Initialize the AgentExecutor.
        
        Args:
            providers: Dict of LLM providers
            tool_broker: ToolBroker instance
            default_model: Default model to use for agent reasoning
            verbose: Whether to log detailed execution info
        """
        self.providers = providers
        self.tool_broker = tool_broker
        self.default_model = default_model
        self.verbose = verbose
    
    async def execute(
        self,
        task: str,
        *,
        user_tier: str = "free",
        context: Optional[str] = None,
        model: Optional[str] = None,
        max_iterations: Optional[int] = None,
        max_tool_calls: Optional[int] = None,
        on_step: Optional[Callable[[AgentStep], None]] = None,
    ) -> AgentExecutionResult:
        """
        Execute a task autonomously.
        
        Args:
            task: The task/question to solve
            user_tier: User's tier for limits
            context: Optional initial context
            model: Model to use (overrides default)
            max_iterations: Override tier max iterations
            max_tool_calls: Override tier max tool calls
            on_step: Optional callback for each step
            
        Returns:
            AgentExecutionResult with final answer and execution details
        """
        start_time = time.time()
        
        # Get tier limits
        tier = user_tier.lower()
        limits = AGENT_TIER_LIMITS.get(tier, AGENT_TIER_LIMITS["free"])
        
        max_iters = max_iterations or limits["max_iterations"]
        max_tools = max_tool_calls or limits["max_tool_calls"]
        timeout = limits["timeout_seconds"]
        allowed_tools = limits["allowed_tools"]
        
        # Initialize scratchpad
        scratchpad = AgentScratchpad(task)
        if context:
            scratchpad.context_accumulator.append(f"Initial context: {context}")
        
        # Track execution
        steps: List[AgentStep] = []
        iteration = 0
        tool_call_count = 0
        total_tokens = 0
        
        model_to_use = model or self.default_model
        
        logger.info("Agent starting task: %s (tier=%s, max_iters=%d)", task[:50], tier, max_iters)
        
        try:
            while iteration < max_iters:
                iteration += 1
                step_start = time.time()
                
                if self.verbose:
                    logger.debug("Agent iteration %d/%d", iteration, max_iters)
                
                # Build prompt
                if iteration == 1:
                    prompt = AGENT_SYSTEM_PROMPT.format(
                        tool_descriptions=build_tool_descriptions(self.tool_broker),
                        task=task,
                        context=context or "(none)",
                    )
                else:
                    prompt = AGENT_CONTINUATION_PROMPT.format(
                        task=task,
                        context=scratchpad.get_context(),
                    )
                
                # Get LLM response
                try:
                    response, tokens = await self._invoke_llm(prompt, model_to_use)
                    total_tokens += tokens
                except Exception as e:
                    logger.error("LLM invocation failed: %s", e)
                    return AgentExecutionResult(
                        success=False,
                        final_answer="",
                        status=AgentStatus.ERROR,
                        steps=steps,
                        total_iterations=iteration,
                        total_tool_calls=tool_call_count,
                        total_tokens=total_tokens,
                        total_latency_ms=(time.time() - start_time) * 1000,
                        error=str(e),
                    )
                
                step_latency = (time.time() - step_start) * 1000
                
                # Parse response
                action, parsed = self._parse_response(response)
                
                # Create step record
                step = AgentStep(
                    step_number=iteration,
                    action=action,
                    content=response,
                    tokens_used=tokens,
                    latency_ms=step_latency,
                )
                
                # Handle based on action type
                if action == AgentAction.ANSWER:
                    # Final answer found
                    step.content = parsed.get("answer", response)
                    steps.append(step)
                    
                    if on_step:
                        on_step(step)
                    
                    logger.info("Agent completed with answer in %d iterations", iteration)
                    
                    return AgentExecutionResult(
                        success=True,
                        final_answer=parsed.get("answer", response),
                        status=AgentStatus.COMPLETED,
                        steps=steps,
                        total_iterations=iteration,
                        total_tool_calls=tool_call_count,
                        total_tokens=total_tokens,
                        total_latency_ms=(time.time() - start_time) * 1000,
                        scratchpad_summary=scratchpad.get_summary(),
                    )
                
                elif action == AgentAction.TOOL_CALL:
                    # Tool request
                    tool_name = parsed.get("tool_name")
                    tool_args = parsed.get("tool_args")
                    
                    step.tool_name = tool_name
                    step.tool_args = tool_args
                    
                    # Check limits
                    if tool_call_count >= max_tools:
                        step.action = AgentAction.ERROR
                        step.content = f"Tool call limit ({max_tools}) reached for {tier} tier"
                        steps.append(step)
                        
                        # Force an answer
                        scratchpad.add_thought("Tool limit reached, providing best answer with available information")
                        return AgentExecutionResult(
                            success=True,
                            final_answer=self._extract_best_answer(steps, scratchpad),
                            status=AgentStatus.MAX_ITERATIONS,
                            steps=steps,
                            total_iterations=iteration,
                            total_tool_calls=tool_call_count,
                            total_tokens=total_tokens,
                            total_latency_ms=(time.time() - start_time) * 1000,
                            scratchpad_summary=scratchpad.get_summary(),
                        )
                    
                    # Check if tool is allowed
                    if tool_name not in allowed_tools:
                        step.tool_result = f"Tool '{tool_name}' not available for {tier} tier"
                        scratchpad.add_tool_result(tool_name, step.tool_result)
                        steps.append(step)
                        continue
                    
                    # Execute tool
                    scratchpad.add_action("tool_call", tool_name, tool_args)
                    
                    try:
                        tool_result = await self._execute_tool(tool_name, tool_args, tier)
                        step.tool_result = str(tool_result)
                        scratchpad.add_tool_result(tool_name, tool_result)
                        tool_call_count += 1
                        
                        if self.verbose:
                            logger.debug("Tool %s returned: %s", tool_name, str(tool_result)[:100])
                        
                    except Exception as e:
                        step.tool_result = f"Tool error: {e}"
                        scratchpad.add_tool_result(tool_name, f"Error: {e}")
                    
                    steps.append(step)
                    
                    if on_step:
                        on_step(step)
                
                elif action == AgentAction.THINK:
                    # Just thinking, record and continue
                    thought = parsed.get("thought", response)
                    step.thought = thought
                    scratchpad.add_thought(thought)
                    steps.append(step)
                    
                    if on_step:
                        on_step(step)
                
                else:
                    # Unknown or no clear action - try to extract answer
                    if self._looks_like_answer(response):
                        steps.append(step)
                        return AgentExecutionResult(
                            success=True,
                            final_answer=response,
                            status=AgentStatus.COMPLETED,
                            steps=steps,
                            total_iterations=iteration,
                            total_tool_calls=tool_call_count,
                            total_tokens=total_tokens,
                            total_latency_ms=(time.time() - start_time) * 1000,
                            scratchpad_summary=scratchpad.get_summary(),
                        )
                    
                    # Continue and let agent try again
                    scratchpad.context_accumulator.append(f"Your response: {response[:500]}")
                    steps.append(step)
                    
                    if on_step:
                        on_step(step)
                
                # Check timeout
                if (time.time() - start_time) > timeout:
                    logger.warning("Agent timeout after %.1fs", time.time() - start_time)
                    return AgentExecutionResult(
                        success=False,
                        final_answer=self._extract_best_answer(steps, scratchpad),
                        status=AgentStatus.MAX_ITERATIONS,
                        steps=steps,
                        total_iterations=iteration,
                        total_tool_calls=tool_call_count,
                        total_tokens=total_tokens,
                        total_latency_ms=(time.time() - start_time) * 1000,
                        scratchpad_summary=scratchpad.get_summary(),
                        error="Execution timeout",
                    )
            
            # Max iterations reached
            logger.warning("Agent reached max iterations (%d)", max_iters)
            
            return AgentExecutionResult(
                success=True,
                final_answer=self._extract_best_answer(steps, scratchpad),
                status=AgentStatus.MAX_ITERATIONS,
                steps=steps,
                total_iterations=iteration,
                total_tool_calls=tool_call_count,
                total_tokens=total_tokens,
                total_latency_ms=(time.time() - start_time) * 1000,
                scratchpad_summary=scratchpad.get_summary(),
            )
            
        except Exception as e:
            logger.error("Agent execution failed: %s", e)
            return AgentExecutionResult(
                success=False,
                final_answer="",
                status=AgentStatus.ERROR,
                steps=steps,
                total_iterations=iteration,
                total_tool_calls=tool_call_count,
                total_tokens=total_tokens,
                total_latency_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )
    
    def _parse_response(self, response: str) -> Tuple[AgentAction, Dict[str, Any]]:
        """Parse the LLM response to determine action and details."""
        response = response.strip()
        
        # Check for final answer
        answer_match = self.ANSWER_PATTERN.search(response)
        if answer_match:
            return AgentAction.ANSWER, {"answer": answer_match.group(1).strip()}
        
        # Check for tool request
        tool_match = self.TOOL_PATTERN.search(response)
        if tool_match:
            return AgentAction.TOOL_CALL, {
                "tool_name": tool_match.group(1).lower(),
                "tool_args": tool_match.group(2).strip(),
            }
        
        # Check for explicit thought
        thought_match = self.THOUGHT_PATTERN.search(response)
        if thought_match:
            return AgentAction.THINK, {"thought": thought_match.group(1).strip()}
        
        # Default: treat as thinking
        return AgentAction.THINK, {"thought": response}
    
    def _looks_like_answer(self, response: str) -> bool:
        """Check if response looks like a final answer (without [ANSWER] tag)."""
        indicators = [
            r"the answer is",
            r"therefore,?\s",
            r"in conclusion",
            r"the result is",
            r"so,?\s+the",
            r"^(?:\d+|yes|no)\.?$",  # Simple numeric or yes/no answer
        ]
        
        response_lower = response.lower()
        
        # No tool patterns
        if "[tool:" in response_lower:
            return False
        
        # Check for answer indicators
        for pattern in indicators:
            if re.search(pattern, response_lower):
                return True
        
        return False
    
    async def _invoke_llm(self, prompt: str, model: str) -> Tuple[str, int]:
        """Invoke the LLM and return (response, tokens)."""
        # Map model to provider
        provider = None
        model_lower = model.lower()
        
        if "gpt" in model_lower or "openai" in model_lower:
            provider = self.providers.get("openai")
        elif "claude" in model_lower or "anthropic" in model_lower:
            provider = self.providers.get("anthropic")
        elif "grok" in model_lower:
            provider = self.providers.get("grok")
        elif "gemini" in model_lower:
            provider = self.providers.get("gemini")
        else:
            provider = self.providers.get(model)
        
        if not provider:
            provider = self.providers.get("stub") or next(iter(self.providers.values()), None)
        
        if not provider:
            raise ValueError(f"No provider available for model: {model}")
        
        # Invoke
        import inspect
        
        if hasattr(provider, 'generate'):
            if inspect.iscoroutinefunction(provider.generate):
                result = await provider.generate(prompt, model=model)
            else:
                result = await asyncio.to_thread(provider.generate, prompt, model=model)
        elif hasattr(provider, 'complete'):
            if inspect.iscoroutinefunction(provider.complete):
                result = await provider.complete(prompt, model=model)
            else:
                result = await asyncio.to_thread(provider.complete, prompt, model=model)
        else:
            # Stub
            result = f"Processed: {prompt[:100]}..."
        
        # Extract content
        if hasattr(result, 'content'):
            content = result.content
        elif hasattr(result, 'text'):
            content = result.text
        elif isinstance(result, str):
            content = result
        else:
            content = str(result)
        
        tokens = getattr(result, 'tokens_used', 0) or len(prompt.split()) // 2
        
        return content, tokens
    
    async def _execute_tool(self, tool_name: str, args: str, user_tier: str) -> Any:
        """Execute a tool and return the result."""
        from .tool_broker import ToolRequest
        
        request = ToolRequest(
            tool_name=tool_name,
            arguments=args,
            raw_request=f"[TOOL:{tool_name}] {args}",
        )
        
        result = await self.tool_broker.handle_tool_request_async(request, user_tier)
        
        if result.success:
            return result.result
        else:
            return f"Error: {result.error}"
    
    def _extract_best_answer(self, steps: List[AgentStep], scratchpad: AgentScratchpad) -> str:
        """Extract the best answer from execution history when no explicit answer was given."""
        # Look for tool results that might be the answer
        for step in reversed(steps):
            if step.tool_result and step.tool_name == "calculator":
                return f"Based on calculation, the result is: {step.tool_result}"
            
            if step.action == AgentAction.THINK and step.thought:
                # If last thought contains conclusive language
                if self._looks_like_answer(step.thought):
                    return step.thought
        
        # Summarize from scratchpad
        if scratchpad.tool_results:
            results = [f"{k}: {v}" for k, v in list(scratchpad.tool_results.items())[-3:]]
            return "Based on the gathered information:\n" + "\n".join(results)
        
        # Fallback
        return "Unable to determine a conclusive answer within the iteration limit."


# ==============================================================================
# Specialized Agent Types
# ==============================================================================

class ResearchAgent(AgentExecutor):
    """Agent specialized for research tasks."""
    
    async def research(
        self,
        topic: str,
        *,
        user_tier: str = "pro",
        depth: int = 3,
    ) -> AgentExecutionResult:
        """
        Research a topic using available tools.
        
        Args:
            topic: Topic to research
            user_tier: User's tier
            depth: How deep to research (affects iterations)
            
        Returns:
            AgentExecutionResult with research findings
        """
        task = f"Research the following topic thoroughly and provide a comprehensive summary: {topic}"
        
        return await self.execute(
            task,
            user_tier=user_tier,
            max_iterations=depth * 3,
        )


class CalculationAgent(AgentExecutor):
    """Agent specialized for calculations and data processing."""
    
    async def calculate(
        self,
        expression: str,
        *,
        user_tier: str = "free",
    ) -> AgentExecutionResult:
        """
        Calculate a mathematical expression.
        
        Args:
            expression: Math expression or problem
            user_tier: User's tier
            
        Returns:
            AgentExecutionResult with calculation result
        """
        task = f"Calculate the following and provide the numeric result: {expression}"
        
        return await self.execute(
            task,
            user_tier=user_tier,
            max_iterations=5,
            max_tool_calls=3,
        )


# ==============================================================================
# Convenience Functions
# ==============================================================================

_executor: Optional[AgentExecutor] = None


def get_agent_executor(
    providers: Optional[Dict[str, Any]] = None,
    tool_broker: Optional[Any] = None,
) -> AgentExecutor:
    """Get or create a global AgentExecutor instance."""
    global _executor
    
    if _executor is None and providers and tool_broker:
        _executor = AgentExecutor(providers, tool_broker)
    
    if _executor is None:
        raise RuntimeError("AgentExecutor not initialized. Provide providers and tool_broker.")
    
    return _executor


async def execute_autonomous_task(
    task: str,
    providers: Dict[str, Any],
    tool_broker: Any,
    *,
    user_tier: str = "free",
    model: Optional[str] = None,
) -> AgentExecutionResult:
    """
    Execute a task autonomously using an agent.
    
    Args:
        task: Task to execute
        providers: LLM providers
        tool_broker: ToolBroker instance
        user_tier: User's tier
        model: Model to use
        
    Returns:
        AgentExecutionResult
    """
    executor = AgentExecutor(providers, tool_broker)
    return await executor.execute(task, user_tier=user_tier, model=model)

