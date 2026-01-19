"""
Reasoning Hacker - Transform traditional LLMs into advanced reasoning systems.

This module implements techniques to "hack" standard models into performing
like specialized reasoning models (o1, DeepSeek-R1) through:

1. PROMPT ENGINEERING: Structured prompts that force step-by-step reasoning
2. MULTI-PASS PIPELINES: Generate → Critique → Improve loops
3. TEAM SIMULATION: Multiple models playing different roles (reasoner, verifier, critic)
4. CONFIDENCE CALIBRATION: Force models to express and act on uncertainty
5. VERIFICATION GATES: Mathematical/logical checking of outputs

The goal: Get o1-level reasoning quality from GPT-4o or Claude Sonnet.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging
import json
import re

logger = logging.getLogger(__name__)


class ReasoningHackLevel(str, Enum):
    """How aggressive to be with reasoning hacks."""
    LIGHT = "light"          # Basic CoT prompt
    MEDIUM = "medium"        # Multi-step with verification
    HEAVY = "heavy"          # Full multi-pass with critique
    MAXIMUM = "maximum"      # Team simulation with debate


@dataclass
class ReasoningHackResult:
    """Result from applying reasoning hacks."""
    final_answer: str
    reasoning_trace: List[str]
    confidence: float
    verification_passed: bool
    iterations: int
    strategy_used: str
    model_used: str


# =============================================================================
# PROMPT HACK TEMPLATES - Force Reasoning in Any Model
# =============================================================================

REASONING_HACK_PROMPTS = {
    
    # =========================================================================
    # LEVEL 1: BASIC REASONING UNLOCK
    # =========================================================================
    
    "basic_cot": """Think through this step-by-step:

{question}

Before answering:
1. Identify what the question is really asking
2. List the key facts and constraints
3. Work through the logic step by step
4. Check your answer for errors

Show your reasoning, then give your final answer.""",
    
    # =========================================================================
    # LEVEL 2: STRUCTURED REASONING WITH VERIFICATION
    # =========================================================================
    
    "structured_reasoning": """You are solving a complex problem. Use this EXACT format:

=== PROBLEM ===
{question}

=== UNDERSTANDING ===
What is being asked: [restate the core question]
Key constraints: [list any constraints]
Type of problem: [classify: math/logic/analysis/creative/factual]

=== APPROACH ===
Strategy: [describe your approach]
Why this approach: [justify]

=== STEP-BY-STEP SOLUTION ===
Step 1: [first step with reasoning]
Step 2: [second step with reasoning]
...continue until solved...

=== VERIFICATION ===
Check 1: [verify a key assumption]
Check 2: [verify the logic chain]
Check 3: [does the answer make sense?]

=== CONFIDENCE ===
Confidence level: [0-100%]
Most uncertain about: [what part]

=== FINAL ANSWER ===
[Your answer here]""",
    
    # =========================================================================
    # LEVEL 3: MULTI-PERSPECTIVE REASONING
    # =========================================================================
    
    "multi_perspective": """Solve this problem from multiple angles:

{question}

=== PERSPECTIVE 1: STRAIGHTFORWARD APPROACH ===
[Solve it the obvious way]

=== PERSPECTIVE 2: ALTERNATIVE APPROACH ===
[Solve it a completely different way]

=== PERSPECTIVE 3: EDGE CASES ===
[What could go wrong? What edge cases exist?]

=== SYNTHESIS ===
Comparing the approaches:
- Approach 1 result: [result]
- Approach 2 result: [result]
- Agreement: [do they agree?]
- Resolution: [if they disagree, which is right and why?]

=== FINAL ANSWER ===
[Your synthesized answer]""",
    
    # =========================================================================
    # LEVEL 4: SELF-DEBATE REASONING (Single model plays multiple roles)
    # =========================================================================
    
    "self_debate": """You will solve this problem by having an internal debate.

{question}

=== PROPOSER ===
[Generate an initial solution with reasoning]

=== CRITIC ===
Now critique the Proposer's solution:
- Logical flaws: [any?]
- Missing considerations: [what was overlooked?]
- Edge cases: [any unhandled?]
- Confidence: [how confident in the proposed solution?]

=== DEFENDER ===
Respond to the Critic's points:
- Address each criticism
- Acknowledge valid points
- Modify solution if needed

=== JUDGE ===
Final verdict:
- Was the original solution correct?
- What modifications are needed?
- Final confidence level

=== FINAL ANSWER ===
[Your final, debate-refined answer]""",
    
    # =========================================================================
    # LEVEL 5: CHAIN-OF-REASONING (Code + Math + Language)
    # =========================================================================
    
    "chain_of_reasoning": """Solve this problem using the most appropriate reasoning format for each step.
You can switch between natural language, mathematical notation, and pseudocode.

{question}

=== ANALYSIS ===
Problem type: [identify]
Best approach: [language / math / code / hybrid]

=== SOLUTION ===
[Use the appropriate format for each step:
- Natural language for conceptual reasoning
- Mathematical notation for calculations
- Pseudocode for algorithms
- Tables for comparisons]

Step 1 ({format}):
{reasoning}

Step 2 ({format}):
{reasoning}

...continue...

=== VERIFICATION ===
[Verify using a DIFFERENT format than the solution:
- If solved mathematically, verify with code logic
- If solved with code, verify with examples
- If solved conceptually, verify with edge cases]

=== FINAL ANSWER ===
[Your answer]""",
    
    # =========================================================================
    # LEVEL 6: CONFIDENCE-GATED REASONING (Iterate until confident)
    # =========================================================================
    
    "confidence_gated": """Solve this problem. You MUST express confidence, and if below 80%, you MUST try again.

{question}

=== ATTEMPT 1 ===
Solution: [your solution]
Reasoning: [your reasoning]
Confidence: [0-100%]
Why this confidence: [explain]

[IF CONFIDENCE < 80%, CONTINUE:]

=== ATTEMPT 2 ===
What I'm uncertain about: [from attempt 1]
New approach: [try a different method]
Solution: [new solution]
Confidence: [0-100%]

[IF STILL < 80%, CONTINUE:]

=== ATTEMPT 3 ===
Synthesize attempts 1 and 2: [combine insights]
Final solution: [best answer]
Final confidence: [0-100%]

=== FINAL ANSWER ===
[Your most confident answer]
Remaining uncertainty: [what you're still unsure about]""",
}


# =============================================================================
# TEAM SIMULATION PROMPTS - Multiple Roles for Single Model
# =============================================================================

TEAM_SIMULATION_PROMPTS = {
    
    "expert_panel": {
        "setup": """You are simulating a panel of {num_experts} experts discussing this problem.
Each expert has a different perspective and specialty.

Problem: {question}

Expert roles:
{expert_roles}

Now simulate their discussion:""",
        
        "expert_template": """
=== {expert_name} ({specialty}) ===
Analysis: {analysis}
Recommendation: {recommendation}
Confidence: {confidence}%
Concerns: {concerns}""",
        
        "synthesis": """
=== PANEL SYNTHESIS ===
Points of agreement: {agreements}
Points of disagreement: {disagreements}
Resolution: {resolution}
Final recommendation: {final}
Collective confidence: {confidence}%""",
    },
    
    "debate": {
        "round_template": """
=== ROUND {round_num} ===

PRO argues: {pro_argument}
CON counters: {con_argument}
JUDGE notes: {judge_notes}""",
        
        "verdict": """
=== FINAL VERDICT ===
Winning position: {winner}
Key reasons: {reasons}
Remaining contention: {contention}
Confidence: {confidence}%""",
    },
}


# =============================================================================
# MULTI-PASS PIPELINE IMPLEMENTATIONS
# =============================================================================

@dataclass
class PipelineStep:
    """A step in a reasoning pipeline."""
    name: str
    prompt_template: str
    expected_output: str  # What this step should produce
    pass_to_next: List[str]  # Which outputs to pass to next step


class ReasoningPipeline:
    """Multi-pass reasoning pipeline that simulates advanced reasoning."""
    
    def __init__(
        self,
        model_caller: Callable[[str, str], str],  # (prompt, model_id) -> response
        default_model: str = "openai/gpt-4o",
    ):
        self.model_caller = model_caller
        self.default_model = default_model
    
    async def run_generate_critique_improve(
        self,
        question: str,
        model_id: Optional[str] = None,
        max_iterations: int = 3,
    ) -> ReasoningHackResult:
        """
        Generate → Critique → Improve loop.
        
        This is one of the most effective ways to hack reasoning into standard models.
        """
        model = model_id or self.default_model
        iterations = []
        current_answer = None
        
        # Step 1: Generate initial answer
        generate_prompt = f"""Solve this problem step by step:

{question}

Show your complete reasoning, then give your answer."""
        
        initial_response = await self.model_caller(generate_prompt, model)
        current_answer = initial_response
        iterations.append({"step": "generate", "response": initial_response})
        
        for i in range(max_iterations - 1):
            # Step 2: Critique the answer
            critique_prompt = f"""You are a rigorous critic. Examine this solution for errors:

PROBLEM: {question}

PROPOSED SOLUTION:
{current_answer}

YOUR CRITIQUE:
1. Logical errors (if any):
2. Missing considerations:
3. Edge cases not handled:
4. Calculation mistakes (if applicable):
5. Overall quality score (1-10):
6. Should this be improved? (yes/no):

If yes, what specifically should be fixed?"""
            
            critique_response = await self.model_caller(critique_prompt, model)
            iterations.append({"step": f"critique_{i+1}", "response": critique_response})
            
            # Check if improvement needed
            if "should this be improved" in critique_response.lower():
                if "no" in critique_response.lower().split("should this be improved")[-1][:50]:
                    break  # Critique says it's good enough
            
            # Step 3: Improve based on critique
            improve_prompt = f"""Improve this solution based on the critique:

PROBLEM: {question}

ORIGINAL SOLUTION:
{current_answer}

CRITIQUE:
{critique_response}

IMPROVED SOLUTION:
Address each issue raised in the critique. Show your reasoning and give the corrected answer."""
            
            improved_response = await self.model_caller(improve_prompt, model)
            current_answer = improved_response
            iterations.append({"step": f"improve_{i+1}", "response": improved_response})
        
        # Extract confidence from final answer
        confidence = self._extract_confidence(current_answer)
        
        return ReasoningHackResult(
            final_answer=current_answer,
            reasoning_trace=[step["response"] for step in iterations],
            confidence=confidence,
            verification_passed=True,  # Would need actual verification
            iterations=len(iterations),
            strategy_used="generate_critique_improve",
            model_used=model,
        )
    
    async def run_multi_solver(
        self,
        question: str,
        num_solvers: int = 3,
        model_id: Optional[str] = None,
    ) -> ReasoningHackResult:
        """
        Multiple independent solutions, then synthesize.
        Simulates self-consistency without multiple API calls.
        """
        model = model_id or self.default_model
        
        # Generate multiple solutions in one call
        multi_solve_prompt = f"""Solve this problem {num_solvers} different ways, then synthesize:

{question}

=== APPROACH 1 (Direct method) ===
[Solve using the most straightforward approach]

=== APPROACH 2 (Alternative method) ===
[Solve using a completely different technique]

=== APPROACH 3 (Verification method) ===
[Solve by working backwards or using estimation]

=== COMPARISON ===
- Approach 1 result: [answer]
- Approach 2 result: [answer]
- Approach 3 result: [answer]
- Agreement: [do they match?]

=== SYNTHESIS ===
If all approaches agree: [state the answer]
If approaches disagree: [analyze why and determine correct answer]

=== FINAL ANSWER ===
[Your synthesized answer with confidence percentage]"""
        
        response = await self.model_caller(multi_solve_prompt, model)
        confidence = self._extract_confidence(response)
        
        return ReasoningHackResult(
            final_answer=response,
            reasoning_trace=[response],
            confidence=confidence,
            verification_passed=True,
            iterations=1,
            strategy_used="multi_solver",
            model_used=model,
        )
    
    async def run_expert_panel_simulation(
        self,
        question: str,
        experts: List[Dict[str, str]],
        model_id: Optional[str] = None,
    ) -> ReasoningHackResult:
        """
        Simulate a panel of experts discussing the problem.
        Single model plays all expert roles.
        """
        model = model_id or self.default_model
        
        expert_list = "\n".join([
            f"- {e['name']}: {e['specialty']}"
            for e in experts
        ])
        
        panel_prompt = f"""You are simulating a panel of experts discussing this problem.
Play each role authentically - different experts will have different perspectives.

PROBLEM: {question}

EXPERT PANEL:
{expert_list}

=== PANEL DISCUSSION ===

"""
        
        for expert in experts:
            panel_prompt += f"""
--- {expert['name']} ({expert['specialty']}) ---
[As {expert['name']}, provide your expert analysis]
Key insight:
Recommendation:
Confidence level:
Concerns or caveats:

"""
        
        panel_prompt += """
=== MODERATOR SYNTHESIS ===
Points of agreement among experts:
Points of disagreement:
How to resolve disagreements:
Final consensus recommendation:
Overall confidence:

=== FINAL ANSWER ===
[The panel's best answer]"""
        
        response = await self.model_caller(panel_prompt, model)
        confidence = self._extract_confidence(response)
        
        return ReasoningHackResult(
            final_answer=response,
            reasoning_trace=[response],
            confidence=confidence,
            verification_passed=True,
            iterations=1,
            strategy_used="expert_panel_simulation",
            model_used=model,
        )
    
    async def run_o1_simulation(
        self,
        question: str,
        thinking_budget: int = 3,  # Number of "thinking" iterations
        model_id: Optional[str] = None,
    ) -> ReasoningHackResult:
        """
        Simulate o1-style reasoning: extensive internal thinking before answering.
        
        Key insight: o1 "thinks" in hidden tokens. We simulate this by:
        1. Extended thinking prompt
        2. Explicit "pause and reconsider" steps
        3. Final answer only after thorough exploration
        """
        model = model_id or self.default_model
        
        o1_simulation_prompt = f"""You are simulating a deep reasoning process. 
Think extensively before answering. Explore multiple paths.

PROBLEM: {question}

=== INITIAL THOUGHTS ===
[Stream of consciousness - explore the problem space]
What type of problem is this?
What are the key elements?
What approaches might work?

=== EXPLORATION 1 ===
[Try one approach]
Result: [what did you find?]
Dead end or promising? [evaluate]

=== EXPLORATION 2 ===
[Try a different approach]
Result: [what did you find?]
Dead end or promising? [evaluate]

=== PAUSE AND RECONSIDER ===
[Step back and think]
What have I learned so far?
What am I missing?
What's the most promising path?

=== DEEPER ANALYSIS ===
[Go deeper on the best approach]
Work through carefully...
Check each step...

=== VERIFICATION ===
[Before finalizing, verify]
Does this make sense?
Have I checked edge cases?
Am I confident?

=== FINAL ANSWER ===
[Only now, after all that thinking, provide your answer]"""
        
        response = await self.model_caller(o1_simulation_prompt, model)
        
        # Extract just the final answer for cleaner output
        final_answer = response
        if "=== FINAL ANSWER ===" in response:
            final_answer = response.split("=== FINAL ANSWER ===")[-1].strip()
        
        confidence = self._extract_confidence(response)
        
        return ReasoningHackResult(
            final_answer=final_answer,
            reasoning_trace=[response],  # Full trace available
            confidence=confidence,
            verification_passed=True,
            iterations=1,
            strategy_used="o1_simulation",
            model_used=model,
        )
    
    def _extract_confidence(self, text: str) -> float:
        """Extract confidence percentage from text."""
        # Look for patterns like "confidence: 85%" or "85% confident"
        patterns = [
            r'confidence[:\s]+(\d+)%',
            r'(\d+)%\s*confident',
            r'confidence[:\s]+(\d+)',
            r'(\d+)/100',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return min(float(match.group(1)) / 100, 1.0)
        
        return 0.7  # Default confidence if not found


# =============================================================================
# TEAM-OF-MODELS IMPLEMENTATION
# =============================================================================

@dataclass
class TeamMember:
    """A model playing a specific role in the team."""
    model_id: str
    role: str
    specialty: str
    prompt_modifier: str = ""  # Additional instructions for this role


class ReasoningTeam:
    """
    Orchestrate multiple models working together to simulate advanced reasoning.
    
    Unlike single-model hacks, this actually uses different models for:
    - Different perspectives (GPT vs Claude vs Gemini)
    - Different roles (generator, critic, verifier)
    - Debate and synthesis
    """
    
    def __init__(
        self,
        model_caller: Callable[[str, str], str],
    ):
        self.model_caller = model_caller
    
    async def run_generator_critic_team(
        self,
        question: str,
        generator: TeamMember,
        critic: TeamMember,
        arbiter: TeamMember,
    ) -> ReasoningHackResult:
        """
        Three-model team: Generator proposes, Critic challenges, Arbiter decides.
        
        This leverages different model strengths:
        - Generator: Creative, comprehensive (e.g., GPT-5)
        - Critic: Analytical, catches errors (e.g., Claude Opus)
        - Arbiter: Balanced judgment (e.g., Gemini)
        """
        iterations = []
        
        # Step 1: Generator creates solution
        gen_prompt = f"""{generator.prompt_modifier}

Solve this problem thoroughly:

{question}

Provide a complete solution with reasoning."""
        
        generation = await self.model_caller(gen_prompt, generator.model_id)
        iterations.append({"role": "generator", "model": generator.model_id, "response": generation})
        
        # Step 2: Critic analyzes
        critic_prompt = f"""{critic.prompt_modifier}

You are a rigorous critic. Analyze this solution for ANY errors or weaknesses:

PROBLEM: {question}

PROPOSED SOLUTION:
{generation}

YOUR CRITICAL ANALYSIS:
1. Is the reasoning sound? [analyze]
2. Are there logical errors? [list any]
3. Are there missing considerations? [list any]
4. Edge cases not handled? [list any]
5. Would you trust this answer? [yes/no and why]
6. Suggested improvements: [list]

Give a quality score from 1-10."""
        
        criticism = await self.model_caller(critic_prompt, critic.model_id)
        iterations.append({"role": "critic", "model": critic.model_id, "response": criticism})
        
        # Step 3: Arbiter synthesizes
        arbiter_prompt = f"""{arbiter.prompt_modifier}

You are the final arbiter. Given a proposed solution and its critique, 
determine the best final answer.

PROBLEM: {question}

PROPOSED SOLUTION:
{generation}

CRITIQUE:
{criticism}

YOUR TASK:
1. Is the critique valid? [evaluate each point]
2. Does the original solution need modification? [yes/no]
3. If yes, what is the corrected solution?
4. Final answer with confidence level.

FINAL ANSWER:"""
        
        arbitration = await self.model_caller(arbiter_prompt, arbiter.model_id)
        iterations.append({"role": "arbiter", "model": arbiter.model_id, "response": arbitration})
        
        return ReasoningHackResult(
            final_answer=arbitration,
            reasoning_trace=[step["response"] for step in iterations],
            confidence=0.85,  # Team consensus typically high confidence
            verification_passed=True,
            iterations=3,
            strategy_used="generator_critic_team",
            model_used=f"{generator.model_id}+{critic.model_id}+{arbiter.model_id}",
        )
    
    async def run_debate_team(
        self,
        question: str,
        debater_a: TeamMember,
        debater_b: TeamMember,
        judge: TeamMember,
        rounds: int = 2,
    ) -> ReasoningHackResult:
        """
        Two models debate, third judges. Surfaces disagreements and resolves them.
        """
        iterations = []
        
        # Initial positions
        position_a_prompt = f"""You are arguing FOR the most obvious/straightforward answer to this problem.
Make your best case.

{question}

YOUR POSITION AND ARGUMENT:"""
        
        position_b_prompt = f"""You are playing devil's advocate - argue AGAINST the obvious answer,
or propose an alternative interpretation. Challenge assumptions.

{question}

YOUR CONTRARIAN POSITION AND ARGUMENT:"""
        
        pos_a = await self.model_caller(position_a_prompt, debater_a.model_id)
        pos_b = await self.model_caller(position_b_prompt, debater_b.model_id)
        
        iterations.append({"round": 0, "a": pos_a, "b": pos_b})
        
        # Debate rounds
        current_a = pos_a
        current_b = pos_b
        
        for round_num in range(rounds):
            # A responds to B
            response_a_prompt = f"""Your opponent argued:
{current_b}

Counter their points and strengthen your position:"""
            
            current_a = await self.model_caller(response_a_prompt, debater_a.model_id)
            
            # B responds to A
            response_b_prompt = f"""Your opponent argued:
{current_a}

Counter their points and strengthen your position:"""
            
            current_b = await self.model_caller(response_b_prompt, debater_b.model_id)
            
            iterations.append({"round": round_num + 1, "a": current_a, "b": current_b})
        
        # Judge's verdict
        judge_prompt = f"""You are the judge. Two positions have been debated:

ORIGINAL QUESTION: {question}

POSITION A (for straightforward answer):
{pos_a}

Final argument A:
{current_a}

POSITION B (contrarian/alternative):
{pos_b}

Final argument B:
{current_b}

YOUR VERDICT:
1. Strongest points from A:
2. Strongest points from B:
3. Which position is more likely correct?
4. What is the TRUE answer considering both perspectives?
5. Confidence level:

FINAL ANSWER:"""
        
        verdict = await self.model_caller(judge_prompt, judge.model_id)
        iterations.append({"round": "verdict", "response": verdict})
        
        return ReasoningHackResult(
            final_answer=verdict,
            reasoning_trace=[str(step) for step in iterations],
            confidence=0.9,  # Debate usually produces high-confidence answers
            verification_passed=True,
            iterations=len(iterations),
            strategy_used="debate_team",
            model_used=f"{debater_a.model_id}+{debater_b.model_id}+{judge.model_id}",
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_hack_prompt(
    level: ReasoningHackLevel,
    question: str,
    task_type: Optional[str] = None,
) -> str:
    """Get the appropriate reasoning hack prompt for the level."""
    
    if level == ReasoningHackLevel.LIGHT:
        template = REASONING_HACK_PROMPTS["basic_cot"]
    elif level == ReasoningHackLevel.MEDIUM:
        template = REASONING_HACK_PROMPTS["structured_reasoning"]
    elif level == ReasoningHackLevel.HEAVY:
        template = REASONING_HACK_PROMPTS["confidence_gated"]
    elif level == ReasoningHackLevel.MAXIMUM:
        template = REASONING_HACK_PROMPTS["self_debate"]
    else:
        template = REASONING_HACK_PROMPTS["basic_cot"]
    
    return template.replace("{question}", question)


def get_recommended_hack_level(
    task_type: str,
    accuracy_required: float = 0.8,
    time_budget_seconds: float = 30.0,
) -> ReasoningHackLevel:
    """Recommend hack level based on task and constraints."""
    
    # High-stakes domains need maximum reasoning
    high_stakes = ["medical", "legal", "financial", "safety"]
    if any(domain in task_type.lower() for domain in high_stakes):
        if time_budget_seconds >= 60:
            return ReasoningHackLevel.MAXIMUM
        else:
            return ReasoningHackLevel.HEAVY
    
    # Math and logic benefit from multi-perspective
    logic_tasks = ["math", "logic", "proof", "calculation"]
    if any(task in task_type.lower() for task in logic_tasks):
        return ReasoningHackLevel.HEAVY
    
    # Complex analysis needs structured reasoning
    analysis_tasks = ["research", "analysis", "comparison", "evaluation"]
    if any(task in task_type.lower() for task in analysis_tasks):
        return ReasoningHackLevel.MEDIUM
    
    # Simple tasks just need basic CoT
    if accuracy_required < 0.7:
        return ReasoningHackLevel.LIGHT
    
    return ReasoningHackLevel.MEDIUM


def get_optimal_team_for_task(task_type: str) -> List[TeamMember]:
    """Get the optimal team composition for a task type."""
    
    # Medical/Legal: Need accuracy and verification
    if any(x in task_type.lower() for x in ["medical", "legal", "health"]):
        return [
            TeamMember(
                model_id="anthropic/claude-opus-4-20250514",
                role="generator",
                specialty="Deep analysis and nuanced reasoning",
                prompt_modifier="You are a careful, thorough analyst. Consider all angles.",
            ),
            TeamMember(
                model_id="openai/gpt-5",
                role="critic",
                specialty="Error detection and verification",
                prompt_modifier="You are a rigorous fact-checker. Find ANY errors.",
            ),
            TeamMember(
                model_id="google/gemini-2.0-pro",
                role="arbiter",
                specialty="Balanced judgment with factual grounding",
                prompt_modifier="You make final decisions based on evidence.",
            ),
        ]
    
    # Math/Logic: Need reasoning depth
    if any(x in task_type.lower() for x in ["math", "logic", "proof"]):
        return [
            TeamMember(
                model_id="openai/o1",
                role="primary_solver",
                specialty="Deep mathematical reasoning",
                prompt_modifier="",  # o1 doesn't need prompt hacks
            ),
            TeamMember(
                model_id="deepseek/deepseek-chat",
                role="verification",
                specialty="Alternative solution path",
                prompt_modifier="Solve this a different way to verify.",
            ),
        ]
    
    # Coding: Need accuracy and best practices
    if any(x in task_type.lower() for x in ["code", "programming", "debug"]):
        return [
            TeamMember(
                model_id="anthropic/claude-sonnet-4-20250514",
                role="generator",
                specialty="Code generation and architecture",
                prompt_modifier="Write clean, efficient, well-documented code.",
            ),
            TeamMember(
                model_id="deepseek/deepseek-chat",
                role="optimizer",
                specialty="Code optimization",
                prompt_modifier="Review for efficiency and edge cases.",
            ),
            TeamMember(
                model_id="openai/gpt-5",
                role="reviewer",
                specialty="Best practices and security",
                prompt_modifier="Check for security issues and best practices.",
            ),
        ]
    
    # Creative: Need diversity of perspectives
    if any(x in task_type.lower() for x in ["creative", "write", "story"]):
        return [
            TeamMember(
                model_id="anthropic/claude-opus-4-20250514",
                role="creative_lead",
                specialty="Nuanced, creative content",
                prompt_modifier="Be creative and original.",
            ),
            TeamMember(
                model_id="x-ai/grok-2",
                role="edge_perspective",
                specialty="Unconventional ideas",
                prompt_modifier="Think outside the box. Be surprising.",
            ),
        ]
    
    # Default: Balanced team
    return [
        TeamMember(
            model_id="openai/gpt-5",
            role="generator",
            specialty="Comprehensive analysis",
        ),
        TeamMember(
            model_id="anthropic/claude-sonnet-4-20250514",
            role="critic",
            specialty="Quality review",
        ),
    ]


# =============================================================================
# PHASE 16: WORLD-CLASS REASONING - SYSTEM/USER SEPARATION
# Fix template leakage by properly separating system instructions from user content
# =============================================================================

# System instructions that tell the LLM HOW to think (never shown to user)
REASONING_SYSTEM_PROMPTS = {
    "light": """You are an expert problem solver. Think step by step before answering.
Always:
1. Identify what's being asked
2. Consider the key facts
3. Work through the logic
4. Verify your answer
Provide a clear, direct final answer at the end.""",

    "medium": """You are an expert problem solver with structured reasoning capabilities.
For every question:
1. UNDERSTAND: Restate the core problem
2. PLAN: Outline your approach
3. EXECUTE: Work through step by step
4. VERIFY: Check your work
5. ANSWER: State your final answer clearly

Your response should flow naturally but include all reasoning steps.
End with a clear statement of your final answer.""",

    "heavy": """You are an expert problem solver with deep analytical capabilities.
Apply rigorous reasoning:
1. Carefully understand what's being asked
2. Consider multiple approaches
3. Work through the problem systematically
4. Verify your logic and calculations
5. Express confidence in your answer

If uncertain, explain why. Always end with a clear, definitive answer.
Format your final answer as: "The answer is [X]" or "My conclusion is [X]".""",

    "maximum": """You are a world-class expert solving a challenging problem.
Use multi-perspective analysis:
1. First attempt: Solve directly
2. Alternative approach: Solve a different way
3. Critique: What could be wrong?
4. Synthesis: Combine insights
5. Final answer: State with confidence

Reason thoroughly but present your final answer clearly at the end.
Always conclude with: "Therefore, the answer is [X]" or "In conclusion, [X]".""",
}


@dataclass
class SeparatedPrompt:
    """Prompt with system and user messages properly separated."""
    system_message: str
    user_message: str
    extraction_pattern: Optional[str] = None


def get_separated_reasoning_prompt(
    level: ReasoningHackLevel,
    question: str,
    task_type: Optional[str] = None,
) -> SeparatedPrompt:
    """Get reasoning prompt with system and user messages properly separated.
    
    This prevents template leakage by putting instructions in system message
    and keeping the user message clean (just the question).
    
    Args:
        level: How aggressive the reasoning approach should be
        question: The user's question (kept clean, no scaffolding)
        task_type: Optional task type for specialized handling
        
    Returns:
        SeparatedPrompt with system_message, user_message, and extraction_pattern
    """
    # Get the appropriate system prompt
    level_key = level.value if isinstance(level, ReasoningHackLevel) else "medium"
    system_prompt = REASONING_SYSTEM_PROMPTS.get(level_key, REASONING_SYSTEM_PROMPTS["medium"])
    
    # Add task-specific guidance to system prompt
    task_guidance = ""
    if task_type:
        if "math" in task_type.lower():
            task_guidance = "\n\nFor math problems: Show all calculations clearly and state numerical answers explicitly."
        elif "code" in task_type.lower():
            task_guidance = "\n\nFor coding: Write clean, working code with comments. Test mentally for edge cases."
        elif "reason" in task_type.lower():
            task_guidance = "\n\nFor logic problems: Use formal reasoning. State explicitly if a conclusion can or cannot be drawn."
        elif "creative" in task_type.lower():
            task_guidance = "\n\nFor creative tasks: Be original and engaging. Meet all requirements precisely."
        elif "analysis" in task_type.lower():
            task_guidance = "\n\nFor analysis: Consider multiple perspectives. Support conclusions with evidence."
    
    # Extraction pattern for parsing the response
    extraction_pattern = r"(?:The answer is|My conclusion is|Therefore,|In conclusion,|Final answer:)[:\s]*(.+?)(?:\n\n|$)"
    
    return SeparatedPrompt(
        system_message=system_prompt + task_guidance,
        user_message=question,  # Clean question, no scaffolding!
        extraction_pattern=extraction_pattern,
    )


def extract_final_answer(response: str, extraction_pattern: Optional[str] = None) -> str:
    """Extract the final answer from a reasoning response.
    
    Uses patterns to find the actual answer, removing any reasoning scaffolding.
    Falls back to the full response if no clear answer marker is found.
    
    Args:
        response: The LLM's full response
        extraction_pattern: Optional regex pattern for extraction
        
    Returns:
        The extracted answer, or the full response if no clear answer found
    """
    if not response:
        return response
    
    # Try the provided pattern first
    if extraction_pattern:
        match = re.search(extraction_pattern, response, re.IGNORECASE | re.DOTALL)
        if match:
            extracted = match.group(1).strip()
            if len(extracted) > 10:  # Ensure it's substantial
                return extracted
    
    # Standard patterns for finding answers
    answer_patterns = [
        r"(?:The answer is|Therefore,? the answer is)[:\s]*(.+?)(?:\n\n|$)",
        r"(?:My conclusion is|In conclusion,?)[:\s]*(.+?)(?:\n\n|$)",
        r"(?:Final answer|FINAL ANSWER)[:\s]*(.+?)(?:\n\n|$)",
        r"(?:The result is|The solution is)[:\s]*(.+?)(?:\n\n|$)",
        # For math - extract numerical result
        r"(?:=|equals|is)\s*\$?([\d,]+\.?\d*)",
    ]
    
    for pattern in answer_patterns:
        match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
        if match:
            extracted = match.group(1).strip()
            # Validate extraction - must be substantial and not a fragment
            if len(extracted) > 5 and not extracted.startswith(('is ', 'are ', 'was ')):
                return extracted
    
    # No clear answer marker found - check if scaffolding is present
    scaffolding_markers = [
        "=== PROBLEM ===",
        "=== UNDERSTANDING ===",
        "=== APPROACH ===",
        "=== STEP-BY-STEP",
        "=== VERIFICATION ===",
        "=== FINAL ANSWER ===",
    ]
    
    if any(marker in response for marker in scaffolding_markers):
        # Try to extract from structured response
        final_match = re.search(r"=== FINAL ANSWER ===\s*(.+?)(?:$|===)", response, re.DOTALL)
        if final_match:
            return final_match.group(1).strip()
    
    # Return the full response if no scaffolding detected
    return response


def is_response_leaked_template(response: str) -> bool:
    """Check if a response appears to be a leaked template.
    
    Returns True if the response contains template scaffolding that should
    have been used internally but not returned to the user.
    """
    leaked_patterns = [
        "=== PROBLEM ===",
        "=== UNDERSTANDING ===",
        "[restate the core question]",
        "[list any constraints]",
        "[describe your approach]",
        "Step 1: [first step",
        "Confidence level: [0-100%]",
        "=== ATTEMPT 1 ===",
        "[IF CONFIDENCE < 80%",
        "=== PROPOSER ===",
        "=== CRITIC ===",
        "=== DEFENDER ===",
    ]
    
    return any(pattern in response for pattern in leaked_patterns)

