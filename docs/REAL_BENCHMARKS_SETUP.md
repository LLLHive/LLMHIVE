# Real Industry Benchmarks Setup & Usage

## 🎯 What This Does

Runs **REAL industry-standard benchmarks** (GSM8K, MMLU) with proper evaluation methods.

**Results CAN be compared to:**
- GPT-5.2 Pro (99.2% GSM8K, 89.6% MMLU)
- Claude Opus 4.5 (95% GSM8K, 90.8% MMLU)
- Gemini 3 Pro (91.8% MMLU)
- DeepSeek R1 (89.3% GSM8K)

---

## ⚡ Quick Start (5 minutes)

### 1. Install Dependencies
```bash
cd /Users/camilodiaz/LLMHIVE
pip install datasets
```

### 2. Set API Key
```bash
export API_KEY="your-llmhive-api-key"
# Or
export LLMHIVE_API_KEY="your-llmhive-api-key"
```

### 3. Run Benchmarks
```bash
python scripts/run_real_industry_benchmarks.py
```

**Time:** ~30-60 minutes for default settings (200 GSM8K + 500 MMLU samples)

---

## 📊 What Gets Tested

### GSM8K (Grade School Math)
- **Dataset**: OpenAI's official 1,319-question test set
- **Sample**: 200 random questions (configurable)
- **Evaluation**: Extract numerical answer, exact match (±0.1% tolerance)
- **Industry Standard**: Yes ✅

**Example Question:**
```
Janet's ducks lay 16 eggs per day. She eats three for breakfast 
every morning and bakes muffins for her friends every day with four. 
She sells the remainder at the farmers' market daily for $2 per 
fresh duck egg. How much in dollars does she make every day?

Expected: 18
```

### MMLU (Massive Multitask Language Understanding)
- **Dataset**: 15,908 questions across 57 academic subjects
- **Sample**: 500 random questions (configurable)
- **Evaluation**: Multiple choice (A/B/C/D), exact letter match
- **Industry Standard**: Yes ✅

**Example Question:**
```
What is the capital of France?
A) London
B) Berlin
C) Paris
D) Madrid

Expected: C
```

---

## ⚙️ Configuration

### Adjust Sample Sizes
```bash
# Fast testing (smaller samples)
export GSM8K_SAMPLE_SIZE=50
export MMLU_SAMPLE_SIZE=100
python scripts/run_real_industry_benchmarks.py

# Full evaluation (takes hours)
export GSM8K_SAMPLE_SIZE=1319  # Full GSM8K test set
export MMLU_SAMPLE_SIZE=5000   # Large MMLU subset
python scripts/run_real_industry_benchmarks.py
```

### Statistical Significance

| Sample Size | Margin of Error (95% CI) | Time Estimate |
|-------------|--------------------------|---------------|
| 50 | ±14% | 5-10 min |
| 100 | ±10% | 10-20 min |
| 200 (default GSM8K) | ±7% | 20-30 min |
| 500 (default MMLU) | ±4.4% | 40-60 min |
| 1000 | ±3.1% | 1.5-2 hrs |
| 5000 | ±1.4% | 6-8 hrs |

**Recommended for Launch:** 200 GSM8K + 500 MMLU (±3-4% margin of error)

---

## 📈 Expected Results

### ELITE Tier (Premium Models)
Based on your current orchestration with GPT-5.2 Pro, Claude Opus 4.5, etc.:

| Benchmark | Expected Range | Target |
|-----------|----------------|--------|
| GSM8K | 90-96% | Match/exceed Claude Opus 4.5 (95%) |
| MMLU | 85-91% | Approach Gemini 3 Pro (91.8%) |

### FREE Tier (Free Models)
Based on your orchestration with DeepSeek R1, Qwen3, Gemini Flash:

| Benchmark | Expected Range | Target |
|-----------|----------------|--------|
| GSM8K | 75-88% | Approach DeepSeek R1 (89.3%) |
| MMLU | 65-80% | Beat GPT-4 historical (86.4%) |

---

## 🎯 Marketing Claims You Can Make

### ✅ With These Real Benchmarks

**If ELITE scores 92% on GSM8K:**
- "Achieves 92% on GSM8K, competitive with Claude Opus 4.5 (95%)"
- "Top-tier mathematical reasoning validated on industry benchmarks"
- "Within 3% of GPT-5.2 Pro on grade school math"

**If FREE scores 85% on GSM8K:**
- "FREE tier achieves 85% on GSM8K at $0 cost"
- "Outperforms many premium services on mathematical reasoning"
- "Approaching DeepSeek R1 performance (89.3%) at zero cost"

**If ELITE scores 88% on MMLU:**
- "Achieves 88% on MMLU across 57 academic subjects"
- "Competitive with GPT-5.2 Pro (89.6%) on multitask understanding"
- "Industry-validated general knowledge and reasoning"

### ❌ Cannot Make (Without Running This)

- "Beats GPT-5.2 Pro on math benchmarks"
- "Outperforms Claude Opus 4.5"
- Any claim about MMLU/GSM8K without actually running these tests

---

## 📁 Output Files

After running, you'll get:

### 1. Markdown Report
```
benchmark_reports/REAL_INDUSTRY_BENCHMARK_20260127_143022.md
```

Contains:
- Accuracy scores for ELITE and FREE tiers
- Direct comparison to GPT-5.2 Pro, Claude Opus 4.5, etc.
- Performance analysis
- Verified marketing claims
- Cost analysis

### 2. JSON Results
```
benchmark_reports/real_benchmark_results_20260127_143022.json
```

Contains:
- Full results for every question
- Latency metrics
- Cost tracking
- Industry comparison data

---

## 🚨 Troubleshooting

### Error: "datasets library not installed"
```bash
pip install datasets
```

### Error: "API_KEY environment variable not set"
```bash
export API_KEY="your-key"
# Or add to ~/.zshrc:
echo 'export API_KEY="your-key"' >> ~/.zshrc
source ~/.zshrc
```

### Error: "Failed to load GSM8K/MMLU"
```bash
# May need trust_remote_code for some datasets
pip install --upgrade datasets
```

### Slow performance / timeouts
```bash
# Reduce sample sizes
export GSM8K_SAMPLE_SIZE=50
export MMLU_SAMPLE_SIZE=100
```

---

## 🔬 Validation

To verify results are real industry benchmarks:

1. **Check dataset source:**
   ```python
   from datasets import load_dataset
   gsm8k = load_dataset("openai/gsm8k", "main", split="test")
   print(len(gsm8k))  # Should be 1319
   ```

2. **Verify evaluation method:**
   - GSM8K: Numerical extraction + exact match
   - MMLU: Letter extraction + exact match
   - Both use industry-standard methods

3. **Compare to published scores:**
   - Your results should be within ±5% of frontier models on similar hardware
   - Large deviations suggest implementation issues

---

## 💡 Next Steps After Running

1. **Review Results**: Check accuracy scores and compare to frontier models

2. **Update Marketing**: Use verified claims in your materials

3. **Iterate**: If scores are lower than expected:
   - Review failed samples in JSON output
   - Check if prompting could be improved
   - Consider ensemble strategies

4. **Full Evaluation** (Optional): Run with full test sets for publication

---

## 📊 Comparison: Old vs New Tests

| Aspect | Old Tests (run_elite_free_benchmarks.py) | New Tests (run_real_industry_benchmarks.py) |
|--------|------------------------------------------|---------------------------------------------|
| **Dataset** | Custom questions | GSM8K, MMLU (official) |
| **Questions** | 5 math, 5 coding | 200 GSM8K, 500 MMLU |
| **Evaluation** | Keyword matching | Exact numerical/letter match |
| **Marketing** | ❌ Cannot compare | ✅ Can compare to GPT-5.2 Pro |
| **Time** | 5 minutes | 30-60 minutes |
| **Legitimacy** | Internal only | Industry standard |

---

**Bottom Line:** Run this for your launch to make legitimate, defensible claims about your performance vs GPT-5.2 Pro, Claude Opus 4.5, and other frontier models.
