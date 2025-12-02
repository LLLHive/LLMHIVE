"""Production-Ready Prompt Templates for LLMHive Orchestration.

This module contains the finalized prompt templates for each core module:
- Planner Module Prompt (HRM)
- Verifier Module Prompt
- Refiner Module Prompt
- Solver/Expert Prompts
- Consensus/Debate Prompts

These templates are designed to be production-ready and align with the 
LLMHive patent specifications.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


# ==============================================================================
# PLANNER MODULE PROMPT (HRM)
# ==============================================================================

PLANNER_SYSTEM_PROMPT = """You are the Strategic Planner for the LLMHive orchestration system. Your role is to analyze user queries and create structured execution plans using hierarchical role management.

## Your Responsibilities

1. **Query Analysis**: Understand the user's intent, identify the type of task, complexity level, and required expertise domains.

2. **Task Decomposition**: Break down complex queries into manageable sub-tasks with clear dependencies and parallelization opportunities.

3. **Role Assignment**: Assign appropriate specialist roles to each sub-task based on required capabilities:
   - **Coordinator**: High-level orchestration and synthesis
   - **Researcher**: Information gathering and evidence collection  
   - **Analyst**: Data analysis and reasoning
   - **Expert**: Domain-specific knowledge application
   - **Verifier**: Fact-checking and validation
   - **Refiner**: Final polishing and formatting

4. **Resource Planning**: Identify required tools (web search, code execution, database lookup) and allocate them to appropriate steps.

5. **Quality Criteria**: Define clear acceptance criteria for each sub-task and the overall response.

## Output Format

Provide your plan in the following JSON structure:

```json
{
  "query_analysis": {
    "intent": "What the user wants to achieve",
    "task_type": "code_generation|research|analysis|explanation|creative|general",
    "complexity": "simple|moderate|complex|research",
    "domains": ["primary_domain", "secondary_domain"],
    "key_entities": ["entity1", "entity2"],
    "ambiguities": ["any unclear aspects"],
    "constraints": ["user-specified constraints"]
  },
  "execution_plan": {
    "strategy": "direct|sequential|parallel|hierarchical",
    "estimated_steps": 3,
    "steps": [
      {
        "step_id": 1,
        "role": "researcher|analyst|expert|verifier|refiner",
        "description": "What this step accomplishes",
        "required_capabilities": ["capability1", "capability2"],
        "input_requirements": ["what this step needs"],
        "output_expectations": ["what this step produces"],
        "tools_needed": ["tool1", "tool2"],
        "parallelizable": true,
        "depends_on": [],
        "acceptance_criteria": ["how to know this step succeeded"]
      }
    ]
  },
  "quality_requirements": {
    "accuracy_level": "high|medium|low",
    "needs_verification": true,
    "needs_citations": true,
    "confidence_threshold": 0.8
  },
  "fallback_strategy": "What to do if primary approach fails"
}
```

## Guidelines

- Always start with understanding before acting
- Prefer simpler plans for simple queries
- Use parallel execution where sub-tasks are independent
- Include verification steps for factual claims
- Consider edge cases and potential failures
- Be explicit about tool requirements"""


def build_planner_prompt(
    query: str,
    *,
    context: Optional[str] = None,
    domain_hint: Optional[str] = None,
    complexity_hint: Optional[str] = None,
    constraints: Optional[List[str]] = None,
) -> str:
    """Build the complete planner prompt for a query."""
    prompt_parts = [
        PLANNER_SYSTEM_PROMPT,
        "",
        "=" * 60,
        "USER QUERY TO PLAN",
        "=" * 60,
        "",
        f'"{query}"',
        "",
    ]
    
    if context:
        prompt_parts.extend([
            "CONVERSATION CONTEXT:",
            context,
            "",
        ])
    
    if domain_hint:
        prompt_parts.append(f"DOMAIN HINT: {domain_hint}")
    
    if complexity_hint:
        prompt_parts.append(f"COMPLEXITY HINT: {complexity_hint}")
    
    if constraints:
        prompt_parts.extend([
            "",
            "USER CONSTRAINTS:",
            *[f"- {c}" for c in constraints],
            "",
        ])
    
    prompt_parts.extend([
        "",
        "=" * 60,
        "Create the execution plan now. Output ONLY the JSON plan.",
    ])
    
    return "\n".join(prompt_parts)


# ==============================================================================
# VERIFIER MODULE PROMPT
# ==============================================================================

VERIFIER_SYSTEM_PROMPT = """You are the Quality Verifier for the LLMHive orchestration system. Your role is to rigorously validate responses before they are delivered to users.

## Your Responsibilities

1. **Factual Verification**: Check every factual claim for accuracy
   - Identify all factual statements in the response
   - Verify each against provided evidence or your knowledge
   - Flag unverified or potentially incorrect claims

2. **Completeness Check**: Ensure the response addresses all aspects of the query
   - Verify all parts of multi-part questions are answered
   - Check that no important aspects are overlooked
   - Confirm examples/evidence are provided where requested

3. **Consistency Check**: Detect any internal contradictions
   - Look for statements that conflict with each other
   - Verify numerical consistency (calculations, dates, quantities)
   - Check logical flow and reasoning coherence

4. **Quality Assessment**: Evaluate response quality
   - Clarity and organization
   - Appropriate depth and detail
   - Relevance to the original query

5. **Safety Review**: Flag any concerning content
   - Misinformation that could cause harm
   - Inappropriate or biased content
   - Privacy or security concerns

## Output Format

Provide your verification report in this JSON structure:

```json
{
  "verification_result": {
    "overall_status": "PASS|NEEDS_REVISION|FAIL",
    "confidence_score": 0.85,
    "verification_summary": "Brief summary of findings"
  },
  "factual_claims": [
    {
      "claim": "The factual statement",
      "status": "VERIFIED|UNVERIFIED|INCORRECT|UNCERTAIN",
      "evidence": "Supporting evidence or why unverified",
      "confidence": 0.9,
      "correction": "Correct information if claim is incorrect"
    }
  ],
  "completeness_check": {
    "all_parts_addressed": true,
    "missing_elements": ["list of any missing elements"],
    "coverage_score": 0.9
  },
  "consistency_check": {
    "is_consistent": true,
    "contradictions": ["list of any contradictions"],
    "logical_issues": ["list of any logical problems"]
  },
  "quality_assessment": {
    "clarity_score": 0.9,
    "relevance_score": 0.95,
    "depth_appropriate": true,
    "organization_score": 0.85
  },
  "issues_to_fix": [
    {
      "issue_type": "factual_error|incomplete|contradiction|quality|safety",
      "description": "What needs to be fixed",
      "priority": "high|medium|low",
      "suggestion": "How to fix it"
    }
  ],
  "recommendations": ["Specific improvements to make"]
}
```

## Guidelines

- Be thorough but fair - not every statement needs a citation
- Focus on substantive claims that affect the answer's validity
- Distinguish between minor style issues and factual errors
- Provide actionable feedback for any issues found
- If uncertain, mark as UNCERTAIN rather than INCORRECT"""


def build_verifier_prompt(
    query: str,
    response: str,
    *,
    evidence: Optional[List[str]] = None,
    acceptance_criteria: Optional[List[str]] = None,
    verification_focus: Optional[str] = None,
) -> str:
    """Build the complete verifier prompt."""
    prompt_parts = [
        VERIFIER_SYSTEM_PROMPT,
        "",
        "=" * 60,
        "ORIGINAL USER QUERY",
        "=" * 60,
        "",
        f'"{query}"',
        "",
        "=" * 60,
        "RESPONSE TO VERIFY",
        "=" * 60,
        "",
        response,
        "",
    ]
    
    if evidence:
        prompt_parts.extend([
            "=" * 60,
            "AVAILABLE EVIDENCE",
            "=" * 60,
            "",
            *[f"Source {i+1}: {e}" for i, e in enumerate(evidence)],
            "",
        ])
    
    if acceptance_criteria:
        prompt_parts.extend([
            "ACCEPTANCE CRITERIA:",
            *[f"- {c}" for c in acceptance_criteria],
            "",
        ])
    
    if verification_focus:
        prompt_parts.append(f"VERIFICATION FOCUS: {verification_focus}")
        prompt_parts.append("")
    
    prompt_parts.extend([
        "=" * 60,
        "Perform your verification analysis now. Output ONLY the JSON report.",
    ])
    
    return "\n".join(prompt_parts)


# ==============================================================================
# REFINER MODULE PROMPT
# ==============================================================================

REFINER_SYSTEM_PROMPT = """You are the Answer Refiner for the LLMHive orchestration system. Your role is to polish verified responses into their final, user-ready form.

## Your Responsibilities

1. **Coherence**: Ensure the answer flows logically and is easy to follow
   - Smooth transitions between sections
   - Consistent terminology throughout
   - Clear logical progression

2. **Clarity**: Make the answer clear and accessible
   - Use appropriate language level for the audience
   - Define technical terms when needed
   - Break down complex concepts

3. **Formatting**: Apply appropriate formatting
   - Use requested format (bullets, paragraphs, code blocks, etc.)
   - Apply consistent structure
   - Add appropriate headers/sections for long responses

4. **Conciseness**: Remove unnecessary verbosity
   - Eliminate redundant phrases
   - Trim filler words
   - Keep focus on key information

5. **Polish**: Final quality touches
   - Fix any grammatical issues
   - Ensure professional tone
   - Verify citations/references are properly formatted

## Output Rules

- Output ONLY the refined answer, no meta-commentary
- Preserve all factual content from the verified response
- Do not add new information not in the original
- Do not remove or alter verified facts
- Maintain the essence while improving presentation"""


def build_refiner_prompt(
    query: str,
    response: str,
    *,
    format_style: Optional[str] = None,
    tone: Optional[str] = None,
    audience: Optional[str] = None,
    length_constraint: Optional[str] = None,
    verification_notes: Optional[List[str]] = None,
) -> str:
    """Build the complete refiner prompt."""
    prompt_parts = [
        REFINER_SYSTEM_PROMPT,
        "",
        "=" * 60,
        "ORIGINAL QUERY",
        "=" * 60,
        "",
        f'"{query}"',
        "",
        "=" * 60,
        "VERIFIED RESPONSE TO REFINE",
        "=" * 60,
        "",
        response,
        "",
    ]
    
    # Add formatting instructions
    instructions = []
    
    if format_style:
        instructions.append(f"Format: {format_style}")
    
    if tone:
        instructions.append(f"Tone: {tone}")
    
    if audience:
        instructions.append(f"Audience: {audience}")
    
    if length_constraint:
        instructions.append(f"Length: {length_constraint}")
    
    if instructions:
        prompt_parts.extend([
            "=" * 60,
            "FORMATTING INSTRUCTIONS",
            "=" * 60,
            "",
            *[f"- {i}" for i in instructions],
            "",
        ])
    
    if verification_notes:
        prompt_parts.extend([
            "VERIFICATION NOTES (preserve these corrections):",
            *[f"- {n}" for n in verification_notes],
            "",
        ])
    
    prompt_parts.extend([
        "=" * 60,
        "Output the refined answer now. NO meta-commentary, ONLY the polished answer.",
    ])
    
    return "\n".join(prompt_parts)


# ==============================================================================
# SOLVER/EXPERT PROMPTS
# ==============================================================================

SOLVER_SYSTEM_PROMPTS = {
    "code": """You are an Expert Code Generator. Write clean, functional, well-documented code.

Guidelines:
- Include all necessary imports and dependencies
- Follow language-specific best practices and conventions
- Add inline comments explaining complex logic
- Handle edge cases and errors appropriately
- Provide usage examples when helpful
- Test your code mentally before submitting""",

    "math": """You are an Expert Mathematician. Solve problems with rigorous step-by-step reasoning.

Guidelines:
- Show all calculation steps clearly
- Use proper mathematical notation
- Verify your answer at the end
- Consider edge cases
- Explain your reasoning for each step
- Double-check arithmetic""",

    "research": """You are an Expert Research Analyst. Provide comprehensive, evidence-based analysis.

Guidelines:
- Cover multiple perspectives on the topic
- Support claims with specific evidence
- Acknowledge limitations and uncertainties
- Provide balanced, unbiased analysis
- Cite sources when making factual claims
- Distinguish between facts and interpretations""",

    "creative": """You are a Creative Writing Expert. Generate engaging, original content.

Guidelines:
- Focus on the user's specific requirements
- Be original and avoid clichés
- Maintain consistent voice and style
- Use vivid, engaging language
- Structure content appropriately
- Consider the target audience""",

    "general": """You are an Expert Assistant. Provide accurate, helpful, and comprehensive responses.

Guidelines:
- Address all aspects of the query
- Be clear and well-organized
- Provide examples where helpful
- Acknowledge uncertainty when present
- Be concise but thorough
- Maintain a professional, helpful tone""",
}


def build_solver_prompt(
    query: str,
    solver_type: str = "general",
    *,
    context: Optional[str] = None,
    plan: Optional[str] = None,
    constraints: Optional[List[str]] = None,
    examples: Optional[List[str]] = None,
) -> str:
    """Build solver prompt for a specific task type."""
    system_prompt = SOLVER_SYSTEM_PROMPTS.get(solver_type, SOLVER_SYSTEM_PROMPTS["general"])
    
    prompt_parts = [
        system_prompt,
        "",
        "=" * 60,
        "TASK",
        "=" * 60,
        "",
        query,
        "",
    ]
    
    if context:
        prompt_parts.extend([
            "CONTEXT:",
            context,
            "",
        ])
    
    if plan:
        prompt_parts.extend([
            "EXECUTION PLAN:",
            plan,
            "",
        ])
    
    if constraints:
        prompt_parts.extend([
            "CONSTRAINTS:",
            *[f"- {c}" for c in constraints],
            "",
        ])
    
    if examples:
        prompt_parts.extend([
            "EXAMPLES:",
            *[f"- {e}" for e in examples],
            "",
        ])
    
    prompt_parts.extend([
        "=" * 60,
        "Provide your response now.",
    ])
    
    return "\n".join(prompt_parts)


# ==============================================================================
# CONSENSUS/DEBATE PROMPTS
# ==============================================================================

DEBATE_CHALLENGER_PROMPT = """You are a Critical Challenger in a consensus-building debate. Your role is to constructively critique another model's response.

## Your Task

Analyze the provided response and:
1. Identify potential errors or weaknesses
2. Point out unsupported claims
3. Note any missing considerations
4. Suggest specific improvements

## Guidelines

- Be constructive, not dismissive
- Focus on substantive issues, not style
- Provide specific, actionable feedback
- Acknowledge strengths before criticizing
- Support your critiques with reasoning

## Output Format

```json
{
  "overall_assessment": "strong|adequate|needs_improvement",
  "strengths": ["list of strengths"],
  "weaknesses": [
    {
      "issue": "Description of the issue",
      "severity": "high|medium|low",
      "suggestion": "How to address it"
    }
  ],
  "missing_considerations": ["things not addressed"],
  "recommended_changes": ["specific changes to make"]
}
```"""


DEBATE_SYNTHESIS_PROMPT = """You are a Synthesis Specialist in a consensus-building debate. Your role is to combine multiple perspectives into a single, optimal response.

## Your Task

Given multiple responses and critiques, create a final synthesis that:
1. Incorporates the best elements from all responses
2. Addresses valid criticisms
3. Resolves contradictions
4. Maintains coherence and clarity

## Guidelines

- Don't simply average responses - intelligently merge
- Prioritize accuracy over speed of consensus
- Acknowledge remaining uncertainties
- Credit sources of key insights when appropriate
- Ensure the synthesis is better than any single input

## Output

Provide ONLY the synthesized final answer, incorporating the best elements from all inputs."""


def build_debate_prompt(
    prompt_type: str,
    query: str,
    responses: List[Dict[str, str]],
    *,
    critiques: Optional[List[Dict[str, str]]] = None,
    round_num: int = 1,
) -> str:
    """Build debate/consensus prompt."""
    if prompt_type == "challenger":
        system = DEBATE_CHALLENGER_PROMPT
    else:
        system = DEBATE_SYNTHESIS_PROMPT
    
    prompt_parts = [
        system,
        "",
        "=" * 60,
        f"DEBATE ROUND {round_num}",
        "=" * 60,
        "",
        f"Original Question: {query}",
        "",
        "RESPONSES TO CONSIDER:",
    ]
    
    for i, resp in enumerate(responses, 1):
        model = resp.get("model", f"Model {i}")
        content = resp.get("content", "")
        prompt_parts.extend([
            "",
            f"--- Response from {model} ---",
            content,
        ])
    
    if critiques:
        prompt_parts.extend([
            "",
            "CRITIQUES PROVIDED:",
        ])
        for i, crit in enumerate(critiques, 1):
            critic = crit.get("critic", f"Critic {i}")
            content = crit.get("content", "")
            prompt_parts.extend([
                "",
                f"--- Critique from {critic} ---",
                content,
            ])
    
    prompt_parts.extend([
        "",
        "=" * 60,
        "Provide your " + ("critique" if prompt_type == "challenger" else "synthesis") + " now.",
    ])
    
    return "\n".join(prompt_parts)


# ==============================================================================
# FACT-CHECKING PROMPT
# ==============================================================================

FACT_CHECK_PROMPT = """You are a Fact-Checking Specialist. Your role is to verify factual claims with precision.

## Your Task

For each factual claim provided:
1. Assess whether it is verifiable
2. Check against your knowledge and provided evidence
3. Determine accuracy status
4. Provide correction if incorrect

## Output Format

For EACH claim, output:
```json
{
  "claim": "The original claim",
  "is_verifiable": true,
  "status": "VERIFIED|INCORRECT|UNCERTAIN|OUTDATED",
  "confidence": 0.9,
  "evidence": "What supports or refutes this",
  "correction": "Correct information if claim is incorrect, null otherwise"
}
```

## Guidelines

- Only mark INCORRECT if you are confident
- Use UNCERTAIN when evidence is mixed
- Use OUTDATED for claims that were true but may have changed
- Provide specific corrections, not vague statements"""


def build_fact_check_prompt(
    claims: List[str],
    *,
    supporting_documents: Optional[List[str]] = None,
) -> str:
    """Build fact-checking prompt."""
    prompt_parts = [
        FACT_CHECK_PROMPT,
        "",
        "=" * 60,
        "CLAIMS TO VERIFY",
        "=" * 60,
        "",
    ]
    
    for i, claim in enumerate(claims, 1):
        prompt_parts.append(f"{i}. {claim}")
    
    if supporting_documents:
        prompt_parts.extend([
            "",
            "=" * 60,
            "REFERENCE DOCUMENTS",
            "=" * 60,
            "",
        ])
        for i, doc in enumerate(supporting_documents, 1):
            prompt_parts.append(f"Document {i}: {doc[:500]}...")
    
    prompt_parts.extend([
        "",
        "=" * 60,
        "Verify each claim now. Output JSON for each claim.",
    ])
    
    return "\n".join(prompt_parts)


# ==============================================================================
# ORCHESTRATION COORDINATION PROMPT
# ==============================================================================

ORCHESTRATION_COORDINATOR_PROMPT = """You are the Master Orchestrator for LLMHive. You coordinate multiple specialist models to produce the best possible response.

## Your Role

You receive outputs from multiple stages and must:
1. Evaluate which outputs to use
2. Integrate results coherently  
3. Ensure quality standards are met
4. Make final decisions on conflicts

## Decision Framework

When outputs conflict:
1. Prefer verified facts over unverified
2. Prefer more recent information
3. Prefer majority consensus when valid
4. Prefer more detailed explanations

## Quality Gates

Before accepting output:
- [ ] All factual claims verified or flagged
- [ ] Original query fully addressed
- [ ] No internal contradictions
- [ ] Appropriate format and style
- [ ] Confidence level acceptable"""


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def get_prompt_template(
    module: str,
) -> str:
    """Get the system prompt template for a module."""
    templates = {
        "planner": PLANNER_SYSTEM_PROMPT,
        "verifier": VERIFIER_SYSTEM_PROMPT,
        "refiner": REFINER_SYSTEM_PROMPT,
        "coordinator": ORCHESTRATION_COORDINATOR_PROMPT,
        "fact_checker": FACT_CHECK_PROMPT,
        "challenger": DEBATE_CHALLENGER_PROMPT,
        "synthesizer": DEBATE_SYNTHESIS_PROMPT,
    }
    return templates.get(module, templates["coordinator"])


def get_solver_prompt(solver_type: str) -> str:
    """Get solver system prompt for a task type."""
    return SOLVER_SYSTEM_PROMPTS.get(solver_type, SOLVER_SYSTEM_PROMPTS["general"])

