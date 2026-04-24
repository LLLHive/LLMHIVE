from llmhive.app.services.orchestrator_adapter import _is_benchmark_mcq_prompt


def test_detects_structured_benchmark_mcq_prompt():
    prompt = (
        "You are a structured reasoning expert.\n\n"
        "Task: Solve the following multiple-choice question.\n\n"
        "A. First\nB. Second\nC. Third\nD. Fourth\n\n"
        "After your reasoning, output exactly:\n"
        "FINAL_ANSWER: <letter>\n"
        "CONFIDENCE: <0.00-1.00>"
    )
    assert _is_benchmark_mcq_prompt(prompt) is True


def test_does_not_flag_normal_math_prompt():
    prompt = "What is 25 * 47? Return the numeric result only."
    assert _is_benchmark_mcq_prompt(prompt) is False


def test_detects_multilingual_benchmark_mcq_prompt():
    prompt = (
        "You are a multilingual expert. Answer the following question carefully.\n\n"
        "Question: Versi klasifikasi yang diperbarui menunjukkan bahwa famili parvovirus memiliki berapa genus?\n\n"
        "A) Dua\nB) Tiga\nC) Empat\nD) Lima\n\n"
        "1. Understand the question in its original language.\n"
        "2. Identify key facts.\n"
        "3. Eliminate incorrect answers explicitly.\n"
        "4. Select the most defensible option.\n"
        "5. Provide FINAL_ANSWER as the letter only.\n\n"
        "After your reasoning, output exactly:\n"
        "FINAL_ANSWER: <letter>\n"
        "CONFIDENCE: <0.00-1.00>"
    )
    assert _is_benchmark_mcq_prompt(prompt) is True
