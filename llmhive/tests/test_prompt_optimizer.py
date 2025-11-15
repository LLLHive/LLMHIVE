from llmhive.app.prompt_optimizer import optimize_prompt


def test_optimize_prompt_injects_directives():
    prompt = "Detail the advantages of solar microgrids"
    optimized = optimize_prompt(prompt, ["Microgrids enhance resilience."])
    assert "Follow these directives" in optimized
    assert "[Memory 1]" in optimized
    assert prompt in optimized
