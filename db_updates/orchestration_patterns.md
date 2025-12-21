# Orchestration Patterns Registry

This document catalogs proven orchestration and reasoning patterns for the LLMHive orchestrator.
Each pattern includes: description, when to use, failure modes, cost/latency impact, and sources.

---

## 1. Planning & Execution Patterns

### 1.1 Plan-Then-Execute (PTE)
**Description**: Generate a complete plan before executing any actions. The planner creates a step-by-step strategy, then execution follows the plan.

**When to use**: Multi-step tasks with clear dependencies, research tasks, complex code changes.

**Failure modes**: Plan may become stale if environment changes; over-planning for simple tasks; plan may miss edge cases discovered during execution.

**Cost/latency impact**: Additional planning call (1 LLM call overhead). Plan tokens add to context.

**Evaluation**: Compare task completion rate vs direct execution. Measure plan adherence.

**Sources**:
- Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models" (2022) https://arxiv.org/abs/2210.03629
- OpenAI "Building effective agents" (2025) https://cookbook.openai.com/examples/orchestrating_agents

---

### 1.2 ReAct (Reason-Act-Observe)
**Description**: Interleave reasoning traces with actions. Model reasons about what to do, takes an action, observes the result, then reasons again.

**When to use**: Exploration tasks, debugging, information gathering where next step depends on prior results.

**Failure modes**: Can loop indefinitely; reasoning traces bloat context; may abandon correct paths prematurely.

**Cost/latency impact**: Linear with number of steps. Each step = 1 LLM call.

**Evaluation**: Step efficiency (steps to completion), success rate, context growth rate.

**Sources**:
- Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models" (2022) https://arxiv.org/abs/2210.03629

---

### 1.3 Reflexion (Self-Reflection Loop)
**Description**: After task attempt, model reflects on failures and generates lessons learned. Subsequent attempts incorporate reflections.

**When to use**: Tasks with clear success/failure signals, coding with tests, iterative improvement.

**Failure modes**: Reflections may be superficial; can reinforce wrong strategies; adds latency for multiple attempts.

**Cost/latency impact**: 2-3x cost for reflection + retry. Significantly improves success on hard tasks.

**Evaluation**: Final success rate vs attempts, reflection quality scoring.

**Sources**:
- Shinn et al., "Reflexion: Language Agents with Verbal Reinforcement Learning" (2023) https://arxiv.org/abs/2303.11366

---

### 1.4 Plan-Act-Reflect (PAR)
**Description**: Three-phase loop: (1) Plan next action, (2) Execute action, (3) Reflect on result and update plan if needed.

**When to use**: Long-horizon tasks requiring adaptation, agentic coding, complex investigations.

**Failure modes**: Reflection overhead may slow simple tasks; may over-reflect on minor issues.

**Cost/latency impact**: ~1.5x overhead from reflection phase.

**Evaluation**: Task completion rate, plan revision frequency, time to completion.

**Sources**:
- Anthropic "Building effective agents" (2025) https://docs.anthropic.com/en/docs/build-with-claude/agentic-systems

---

## 2. Multi-Model Routing Patterns

### 2.1 Specialist Selection (Router Pattern)
**Description**: Use a lightweight classifier/router to select the best model for the task based on query characteristics.

**When to use**: Production systems with cost constraints, tasks spanning multiple domains.

**Failure modes**: Router may misclassify edge cases; cold start for new task types.

**Cost/latency impact**: Router call adds ~100ms + small cost. Saves by routing to cheaper models when appropriate.

**Evaluation**: Routing accuracy, cost savings vs quality trade-off.

**Sources**:
- RouteLLM paper, "RouteLLM: Learning to Route LLMs with Preference Data" (2024) https://arxiv.org/abs/2406.18665

---

### 2.2 Cascade/Fallback Tree
**Description**: Start with cheap/fast model. If confidence is low or task fails, escalate to more capable model.

**When to use**: High-volume production where most queries are simple, cost-sensitive deployments.

**Failure modes**: Confidence estimation may be unreliable; latency spikes on escalation.

**Cost/latency impact**: Reduces average cost by 30-70%. Adds latency for escalated queries.

**Evaluation**: Escalation rate, cost per query, quality on escalated vs non-escalated.

**Sources**:
- FrugalGPT, "FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance" (2023) https://arxiv.org/abs/2305.05176

---

### 2.3 Judge/Critic Pattern
**Description**: One model generates, another model critiques. Can be iterative or single-pass.

**When to use**: High-stakes outputs, content moderation, factuality-critical tasks.

**Failure modes**: Judge may share blind spots with generator; adds latency and cost.

**Cost/latency impact**: 2x cost minimum. Use smaller judge model when possible.

**Evaluation**: Detection rate of issues, false positive rate, quality improvement.

**Sources**:
- Constitutional AI, Anthropic (2022) https://arxiv.org/abs/2212.08073

---

### 2.4 Multi-Model Debate
**Description**: Multiple models propose solutions, then debate merits. Final answer synthesized from debate.

**When to use**: Complex reasoning tasks where single model may have blind spots.

**Failure modes**: Models may reinforce each other's errors; high cost; may not converge.

**Cost/latency impact**: N models × M rounds = N×M LLM calls. Very expensive.

**Evaluation**: Answer quality vs single model, convergence rate.

**Sources**:
- Du et al., "Improving Factuality and Reasoning in Language Models through Multiagent Debate" (2023) https://arxiv.org/abs/2305.14325

---

### 2.5 Mixture of Agents (MoA)
**Description**: Multiple models generate in parallel, then aggregator model synthesizes best answer.

**When to use**: When diversity of perspectives improves quality, high-stakes decisions.

**Failure modes**: Aggregator may not properly weight inputs; expensive.

**Cost/latency impact**: N+1 LLM calls (parallel + aggregator). Latency = max(generators) + aggregator.

**Evaluation**: Quality vs best individual model, cost efficiency.

**Sources**:
- Wang et al., "Mixture-of-Agents Enhances Large Language Model Capabilities" (2024) https://arxiv.org/abs/2406.04692

---

## 3. Self-Verification Patterns

### 3.1 Chain-of-Verification (CoVe)
**Description**: After generating answer, model generates verification questions, answers them, and revises original answer based on findings.

**When to use**: Factuality-critical tasks, reducing hallucination.

**Failure modes**: Verification questions may miss issues; verification answers may also be wrong.

**Cost/latency impact**: 2-3x tokens for verification process.

**Evaluation**: Hallucination rate reduction, verification question quality.

**Sources**:
- Dhuliawala et al., "Chain-of-Verification Reduces Hallucination in Large Language Models" (2023) https://arxiv.org/abs/2309.11495

---

### 3.2 Test-Driven Tool Use
**Description**: Before executing tool calls, generate tests for expected behavior. Run tests after tool execution to validate.

**When to use**: Coding tasks, data transformations, any task with testable outcomes.

**Failure modes**: Test generation may miss edge cases; tests themselves may be wrong.

**Cost/latency impact**: Adds test generation and execution time. Catches errors early.

**Evaluation**: Error catch rate, test coverage quality.

**Sources**:
- SWE-bench best practices https://www.swebench.com/

---

### 3.3 Self-Consistency (Majority Voting)
**Description**: Generate multiple solutions independently, select most common answer.

**When to use**: Math, reasoning, multiple-choice where diversity helps.

**Failure modes**: Expensive (N samples); doesn't help if model consistently wrong.

**Cost/latency impact**: N× cost for N samples. Can parallelize.

**Evaluation**: Accuracy improvement vs single sample.

**Sources**:
- Wang et al., "Self-Consistency Improves Chain of Thought Reasoning in Language Models" (2022) https://arxiv.org/abs/2203.11171

---

## 4. Retrieval & Grounding Patterns

### 4.1 Standard RAG
**Description**: Retrieve relevant documents, include in context, generate grounded answer.

**When to use**: Knowledge-intensive tasks, up-to-date information, domain-specific knowledge.

**Failure modes**: Retrieval may miss relevant docs; context pollution from irrelevant docs; over-reliance on retrieved content.

**Cost/latency impact**: Retrieval latency (~100-500ms) + larger context.

**Evaluation**: Answer quality, citation accuracy, retrieval recall@k.

**Sources**:
- Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (2020) https://arxiv.org/abs/2005.11401

---

### 4.2 Citation Discipline
**Description**: Require model to cite specific sources for claims. Validate citations exist and support claims.

**When to use**: Research, fact-checking, any task requiring verifiability.

**Failure modes**: Citations may be hallucinated; source may not support claim.

**Cost/latency impact**: Minimal additional cost for citation requirement. Validation adds processing.

**Evaluation**: Citation accuracy, hallucinated citation rate.

**Sources**:
- Cohere Command-R documentation https://docs.cohere.com/docs/command-r

---

### 4.3 Freshness-Aware Retrieval
**Description**: Weight recent documents higher, flag when knowledge may be stale.

**When to use**: Current events, rapidly changing domains (e.g., model capabilities, pricing).

**Failure modes**: May over-weight recency at expense of relevance.

**Cost/latency impact**: Minimal additional compute for timestamp weighting.

**Evaluation**: Accuracy on time-sensitive queries.

**Sources**:
- Perplexity AI engineering blog

---

### 4.4 Agentic RAG (Self-RAG)
**Description**: Model decides when to retrieve, what to retrieve, and whether retrieval was helpful.

**When to use**: Complex queries requiring multiple retrieval steps, adaptive information gathering.

**Failure modes**: May over-retrieve or under-retrieve; retrieval decisions may be suboptimal.

**Cost/latency impact**: Variable - depends on retrieval decisions.

**Evaluation**: Retrieval efficiency, answer quality.

**Sources**:
- Asai et al., "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection" (2023) https://arxiv.org/abs/2310.11511

---

## 5. Tool Use Optimization Patterns

### 5.1 High-Quality Tool Definitions
**Description**: Craft tool descriptions with clear semantics, parameter constraints, examples, and error conditions.

**When to use**: Always. Foundation for reliable tool use.

**Failure modes**: Poor descriptions → misuse, hallucinated parameters.

**Cost/latency impact**: No runtime cost. Development investment.

**Evaluation**: Tool call accuracy, parameter validity rate.

**Sources**:
- OpenAI Function Calling Best Practices https://platform.openai.com/docs/guides/function-calling
- Anthropic Tool Use Guide https://docs.anthropic.com/en/docs/build-with-claude/tool-use

---

### 5.2 Tool-Use Examples in Schema
**Description**: Include example tool calls in the tool definition when model supports it.

**When to use**: Complex tools with non-obvious parameter formats.

**Failure modes**: Examples may bias toward specific patterns.

**Cost/latency impact**: Additional tokens in system prompt.

**Evaluation**: First-attempt tool call accuracy.

**Sources**:
- Anthropic Tool Use documentation https://docs.anthropic.com/en/docs/build-with-claude/tool-use

---

### 5.3 Tool Search / Deferred Loading
**Description**: Don't load all tools upfront. Use semantic search to find relevant tools based on query.

**When to use**: Large tool libraries (50+ tools) where context limit is a concern.

**Failure modes**: May miss relevant tools if search quality is poor.

**Cost/latency impact**: Reduces context size significantly. Adds retrieval step.

**Evaluation**: Tool selection recall, context savings.

**Sources**:
- Gorilla Paper, "Gorilla: Large Language Model Connected with Massive APIs" (2023) https://arxiv.org/abs/2305.15334

---

### 5.4 Programmatic Tool Calling (Code-as-Orchestration)
**Description**: Model writes code to orchestrate tool calls rather than making individual function calls.

**When to use**: Complex multi-tool workflows, batch operations, conditional logic.

**Failure modes**: Code may have bugs; harder to debug than explicit tool calls.

**Cost/latency impact**: Reduces LLM round-trips by batching. Results stay in code context.

**Evaluation**: Workflow completion rate, code correctness.

**Sources**:
- Anthropic Claude computer use patterns https://docs.anthropic.com/en/docs/agents-and-tools/computer-use

---

### 5.5 Tool Output Summarization
**Description**: Summarize verbose tool outputs before adding to context to prevent bloat.

**When to use**: Tools returning large outputs (logs, API responses, search results).

**Failure modes**: Summarization may lose critical details.

**Cost/latency impact**: Adds summarization call. Saves context for subsequent reasoning.

**Evaluation**: Context size reduction, information retention.

**Sources**:
- LangChain agent patterns

---

## 6. Security-Aware Orchestration Patterns

### 6.1 Input Sanitization
**Description**: Validate and sanitize user inputs before passing to LLM or tools.

**When to use**: Always in production.

**Failure modes**: Incomplete sanitization allows injection.

**Cost/latency impact**: Minimal compute for validation.

**Evaluation**: Injection attack resistance rate.

**Sources**:
- OWASP LLM Top 10 https://owasp.org/www-project-top-10-for-large-language-model-applications/

---

### 6.2 Prompt Injection Resistance
**Description**: Delimit user content clearly, use system prompts to establish behavior, validate outputs.

**When to use**: Any user-facing application.

**Failure modes**: Sophisticated attacks may still succeed.

**Cost/latency impact**: Minimal overhead for delimiters and validation.

**Evaluation**: Red team testing, injection success rate.

**Sources**:
- Anthropic Prompt Engineering Guide https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering
- Simon Willison's LLM security research

---

### 6.3 Tool Allowlisting
**Description**: Only expose tools the user's permission level allows. Validate tool calls against allowlist.

**When to use**: Multi-tenant systems, varying permission levels.

**Failure modes**: Allowlist may be too permissive or restrictive.

**Cost/latency impact**: Minimal validation overhead.

**Evaluation**: Unauthorized access attempts, usability impact.

**Sources**:
- Anthropic MCP Security Patterns

---

### 6.4 Output Validation / Schema Enforcement
**Description**: Validate LLM outputs against expected schemas. Reject or retry on invalid outputs.

**When to use**: Structured output requirements, API integrations.

**Failure modes**: Valid but incorrect outputs pass validation.

**Cost/latency impact**: Schema validation is fast. Retries add latency.

**Evaluation**: Schema compliance rate, downstream error rate.

**Sources**:
- OpenAI Structured Outputs https://platform.openai.com/docs/guides/structured-outputs

---

### 6.5 Sandboxed Execution
**Description**: Execute model-generated code in isolated sandbox with resource limits.

**When to use**: Code execution tools, agentic coding.

**Failure modes**: Sandbox escape (rare with proper setup).

**Cost/latency impact**: Container/sandbox startup overhead.

**Evaluation**: Security audit results, resource limit effectiveness.

**Sources**:
- E2B Sandbox https://e2b.dev/docs
- Modal Sandbox https://modal.com/docs

---

## 7. Context Management Patterns

### 7.1 Sliding Window with Summarization
**Description**: Keep recent messages, summarize older messages to maintain context limits.

**When to use**: Long conversations, chat applications.

**Failure modes**: Summarization loses important details.

**Cost/latency impact**: Periodic summarization calls.

**Evaluation**: Information retention over conversation length.

**Sources**:
- LangChain ConversationSummaryMemory

---

### 7.2 Hierarchical Memory
**Description**: Store facts at different levels: working memory (current turn), episodic (conversation), semantic (long-term knowledge).

**When to use**: Complex agents requiring long-term memory.

**Failure modes**: Memory retrieval may miss relevant facts.

**Cost/latency impact**: Memory operations add latency.

**Evaluation**: Fact retention, recall accuracy.

**Sources**:
- MemGPT Paper https://arxiv.org/abs/2310.08560

---

### 7.3 Structured Scratchpad
**Description**: Maintain structured scratchpad for intermediate results, plans, and state.

**When to use**: Multi-step reasoning, stateful agents.

**Failure modes**: Scratchpad may become stale or inconsistent.

**Cost/latency impact**: Additional tokens in context.

**Evaluation**: State consistency, task completion rate.

**Sources**:
- LLMHive HRM Blackboard implementation

---

## 8. Reasoning Enhancement Patterns

### 8.1 Chain-of-Thought (CoT)
**Description**: Prompt model to show reasoning steps before final answer.

**When to use**: Math, logic, multi-step reasoning.

**Failure modes**: Reasoning may be plausible but wrong.

**Cost/latency impact**: 2-5x more output tokens.

**Evaluation**: Accuracy improvement vs direct answering.

**Sources**:
- Wei et al., "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models" (2022) https://arxiv.org/abs/2201.11903

---

### 8.2 Tree-of-Thought (ToT)
**Description**: Explore multiple reasoning paths, evaluate intermediate states, backtrack if needed.

**When to use**: Complex problems with multiple valid approaches.

**Failure modes**: Expensive; may not converge.

**Cost/latency impact**: O(branching_factor × depth) LLM calls.

**Evaluation**: Solution quality vs CoT, exploration efficiency.

**Sources**:
- Yao et al., "Tree of Thoughts: Deliberate Problem Solving with Large Language Models" (2023) https://arxiv.org/abs/2305.10601

---

### 8.3 Step-Back Prompting
**Description**: Before answering, ask model to identify the underlying principle or higher-level concept.

**When to use**: Science, math, conceptual questions.

**Failure modes**: Step-back may not identify relevant principle.

**Cost/latency impact**: One additional LLM call.

**Evaluation**: Accuracy improvement on conceptual questions.

**Sources**:
- Zheng et al., "Take a Step Back: Evoking Reasoning via Abstraction in Large Language Models" (2023) https://arxiv.org/abs/2310.06117

---

### 8.4 Decomposition (Least-to-Most)
**Description**: Break complex problem into simpler sub-problems, solve sequentially.

**When to use**: Complex multi-part questions, compositional tasks.

**Failure modes**: Decomposition may miss dependencies.

**Cost/latency impact**: Multiple calls, but each simpler.

**Evaluation**: Complex task completion rate.

**Sources**:
- Zhou et al., "Least-to-Most Prompting Enables Complex Reasoning in Large Language Models" (2022) https://arxiv.org/abs/2205.10625

---

### 8.5 Extended Thinking / Budget Forcing
**Description**: Force model to use more compute for reasoning by requesting longer thinking or using reasoning models with effort parameters.

**When to use**: Hard problems where quality matters more than speed.

**Failure modes**: More thinking doesn't always help; expensive.

**Cost/latency impact**: Linear with thinking budget.

**Evaluation**: Quality vs thinking budget curve.

**Sources**:
- Anthropic Claude extended thinking https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking
- OpenAI o1 reasoning_effort parameter

---

## Index

| ID | Pattern | Category | Complexity | Cost Impact |
|----|---------|----------|------------|-------------|
| 1.1 | Plan-Then-Execute | Planning | Medium | +1 call |
| 1.2 | ReAct | Planning | Medium | Linear |
| 1.3 | Reflexion | Planning | High | 2-3x |
| 1.4 | Plan-Act-Reflect | Planning | High | 1.5x |
| 2.1 | Specialist Selection | Routing | Low | Savings |
| 2.2 | Cascade/Fallback | Routing | Medium | 30-70% savings |
| 2.3 | Judge/Critic | Routing | Medium | 2x |
| 2.4 | Multi-Model Debate | Routing | High | N×M× |
| 2.5 | Mixture of Agents | Routing | High | N+1 |
| 3.1 | Chain-of-Verification | Verification | Medium | 2-3x |
| 3.2 | Test-Driven Tool Use | Verification | Medium | Variable |
| 3.3 | Self-Consistency | Verification | Low | N× |
| 4.1 | Standard RAG | Retrieval | Low | Context |
| 4.2 | Citation Discipline | Retrieval | Low | Minimal |
| 4.3 | Freshness-Aware | Retrieval | Low | Minimal |
| 4.4 | Agentic RAG | Retrieval | High | Variable |
| 5.1 | Quality Tool Defs | Tool Use | Low | None |
| 5.2 | Tool Examples | Tool Use | Low | Tokens |
| 5.3 | Tool Search | Tool Use | Medium | Saves context |
| 5.4 | Programmatic Calling | Tool Use | High | Saves calls |
| 5.5 | Output Summarization | Tool Use | Medium | Saves context |
| 6.1 | Input Sanitization | Security | Low | Minimal |
| 6.2 | Injection Resistance | Security | Medium | Minimal |
| 6.3 | Tool Allowlisting | Security | Low | Minimal |
| 6.4 | Output Validation | Security | Low | Minimal |
| 6.5 | Sandboxed Execution | Security | Medium | Container |
| 7.1 | Sliding Window | Context | Medium | Periodic |
| 7.2 | Hierarchical Memory | Context | High | Memory ops |
| 7.3 | Structured Scratchpad | Context | Medium | Tokens |
| 8.1 | Chain-of-Thought | Reasoning | Low | 2-5x tokens |
| 8.2 | Tree-of-Thought | Reasoning | High | O(b×d) |
| 8.3 | Step-Back | Reasoning | Low | +1 call |
| 8.4 | Decomposition | Reasoning | Medium | Multiple |
| 8.5 | Extended Thinking | Reasoning | Low | Linear |

---

*Last updated: 2024-12-20*
*Total patterns: 28*

