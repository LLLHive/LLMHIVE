"""Prompt templates for advanced reasoning methods."""
from __future__ import annotations

from typing import Dict, Optional

from .model_router import ReasoningMethod


def get_reasoning_prompt_template(
    method: ReasoningMethod,
    base_prompt: str,
    domain_pack: Optional[str] = None,
) -> str:
    """
    Get a prompt template for the specified reasoning method.
    
    Args:
        method: The reasoning method to use
        base_prompt: The user's original prompt
        domain_pack: Optional domain specialization (medical, legal, etc.)
        
    Returns:
        Enhanced prompt with reasoning method instructions
    """
    # Domain-specific prefixes with clear instruction to answer directly
    # CRITICAL: Models must NOT ask clarifying questions when the user's request is clear
    base_instruction = """IMPORTANT: Answer the user's question directly. Do NOT ask clarifying questions unless the query is genuinely incomprehensible. If the user specifies criteria (e.g., "by effectiveness", "top 10"), use those criteria. Do not ask about alternative criteria.

"""
    
    domain_prefixes = {
        "medical": f"""{base_instruction}You are a medical expert with deep knowledge of clinical research, treatments, therapies, and evidence-based medicine. Provide accurate, well-researched information based on current medical literature and guidelines.

""",
        "legal": f"""{base_instruction}You are a legal expert. Provide precise, well-reasoned legal analysis based on established law and precedent.

""",
        "marketing": f"""{base_instruction}You are a marketing expert. Provide creative, strategic insights grounded in marketing best practices.

""",
        "coding": f"""{base_instruction}You are a software engineering expert. Provide clear, efficient code solutions with best practices.

""",
        "general": f"""{base_instruction}You are a knowledgeable assistant. Provide clear, accurate, and helpful responses.

""",
    }
    
    domain_prefix = domain_prefixes.get(domain_pack or "", base_instruction)
    
    templates: Dict[ReasoningMethod, str] = {
        ReasoningMethod.chain_of_thought: f"""{domain_prefix}Let's work this out step by step.

{base_prompt}

Please think through this problem step by step, showing your reasoning at each stage. Do not skip steps. After reasoning, provide a concise final answer clearly marked as 'Final Answer:'.""",

        ReasoningMethod.tree_of_thought: f"""{domain_prefix}Let's explore multiple approaches to solve this problem.

{base_prompt}

First, think of 3 distinct approaches/solution paths. For each, briefly outline the idea, its promise, and next steps. Then choose the most promising path, develop it fully, and if it fails, backtrack to the next best. End with a clear 'Final Answer:'.""",

        ReasoningMethod.react: f"""{domain_prefix}You are an AI agent with access to tools. Use the following format:

Thought: <your reasoning about what to do>
Action: <tool_name>[<tool_input>]
Observation: <result from tool>

Repeat Thought/Action/Observation as needed until you can provide a final answer.

Question: {base_prompt}

Available tools (sample):
- WEB_SEARCH(query): Search the web for up-to-date info
- WEB_BROWSER(url): Fetch full page text content
- KNOWLEDGE_BASE(query): Retrieve stored knowledge snippets
- CALCULATOR(expr): Evaluate math expressions
- CODE_EXECUTION(code): Run code in a sandbox (Python)
- DOC_QA(query, document): Answer based on provided document text
- VISION(image_url_or_data): Caption/OCR an image
- IMAGE_GENERATION(prompt): Generate an image from a prompt
- DATABASE(query): (read-only) run safe DB queries if enabled

Begin by thinking about what information or tools you need to answer this question. Use tools when they improve accuracy (facts, calculations, code, docs, images). When you are ready, provide 'Final Answer:' with no additional tool calls afterwards.""",

        ReasoningMethod.plan_and_solve: f"""{domain_prefix}Solve this problem in two phases:

Phase 1 - Planning: Outline a step-by-step plan or pseudocode to solve this problem. Be specific about each step.

Phase 2 - Solution: Execute the plan and provide the solution. If code is needed, write it and show the result.

Problem: {base_prompt}

Start with Phase 1.""",

        ReasoningMethod.self_consistency: f"""{domain_prefix}Solve this problem using multiple independent reasoning approaches.

{base_prompt}

Produce 3 short, independent solution attempts (Approach A, B, C), each reasoned separately. Then compare them and select the most consistent/well-supported result. Present only the final chosen answer labeled 'Final Answer:'.""",

        ReasoningMethod.reflexion: f"""{domain_prefix}Solve this problem, then reflect on and refine your solution.

{base_prompt}

First, provide an initial solution with reasoning. Then critically examine it for errors, gaps, or weaknesses. Revise the solution to fix issues. Output only the improved final solution at the end, labeled 'Final Answer:' (do not include the critique text).""",

        # Research methods from "Implementing Advanced Reasoning Methods with Optimal LLMs (2025)"
        
        # 1. Hierarchical Task Decomposition (HRM-style)
        ReasoningMethod.hierarchical_decomposition: f"""{domain_prefix}Break this complex problem into a hierarchy of sub-tasks.

{base_prompt}

First, act as a high-level planner: decompose the problem into major steps or sub-problems. For each sub-problem, outline what needs to be solved. Then, work through each sub-problem systematically, solving smaller chunks in sequence. Finally, synthesize the solutions from all sub-problems into a coherent final answer.""",

        # 2. Diffusion-Inspired Iterative Reasoning
        ReasoningMethod.iterative_refinement: f"""{domain_prefix}Solve this problem through iterative refinement.

{base_prompt}

Step 1 - Draft: Provide an initial "draft" solution quickly, even if it's rough or incomplete.

Step 2 - Refine: Review your draft. Identify errors, gaps, or areas that need improvement. Then produce a refined version that corrects mistakes, fills gaps, and polishes the wording.

Step 3 - Final: If needed, do one more refinement pass to ensure the solution is complete and accurate.""",

        # 3. Confidence-Based Filtering (DeepConf)
        ReasoningMethod.confidence_filtering: f"""{domain_prefix}Solve this problem and indicate your confidence level.

{base_prompt}

Provide your solution with reasoning. Then, explicitly state:
1. Your confidence level in this answer (0-100%)
2. Which parts you're most certain about
3. Which parts you're less certain about

If your confidence is below 70%, note what additional information or verification would increase your confidence. End with 'Final Answer:' plus confidence.""",

        # 4. Dynamic Planning (Test-Time Decision-Making)
        ReasoningMethod.dynamic_planning: f"""{domain_prefix}Solve this problem using adaptive, dynamic planning.

{base_prompt}

As you work through this problem, make on-the-fly decisions about the best next step. Observe intermediate results and adapt your approach:
- If one approach seems uncertain, try a different method
- If you need more information, identify what's missing
- If you encounter an obstacle, adjust your strategy

Document your decision-making process: explain why you chose each step and how you adapted based on what you learned. Stop when you have a clear 'Final Answer:'.""",
    }
    
    return templates.get(method, base_prompt)


def get_reflexion_followup_prompt(previous_answer: str) -> str:
    """Get a prompt for the reflection phase of Reflexion method."""
    return f"""Reflect on the above solution. Analyze it carefully:

1. Is the reasoning sound?
2. Are there any errors or gaps?
3. Could the solution be improved?

If you find issues, provide a revised solution. If the solution is correct, confirm it clearly.

Previous solution:
{previous_answer}"""


def get_tree_of_thought_branch_prompt(
    base_prompt: str,
    current_branch: str,
    previous_attempts: Optional[list[str]] = None,
) -> str:
    """Get a prompt for evaluating a branch in tree-of-thought reasoning."""
    attempts_text = ""
    if previous_attempts:
        attempts_text = "\n\nPrevious attempts:\n" + "\n".join(
            f"- {attempt}" for attempt in previous_attempts
        )
    
    return f"""Given this partial approach to the problem, evaluate it:

Problem: {base_prompt}

Current approach: {current_branch}{attempts_text}

Is this approach promising? What is the next step, or is this a dead-end? If promising, continue developing it. If not, suggest an alternative approach."""

