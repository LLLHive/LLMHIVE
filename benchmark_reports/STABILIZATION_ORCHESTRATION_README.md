# Stabilization Orchestration Artifact

Use this helper to generate a single JSON artifact implementing the approved post-recovery stabilization framework.

## Command

```bash
python scripts/stabilization_orchestration_engine.py \
  --output benchmark_reports/stabilization_orchestration_artifact.json
```

Optional replay input:

```bash
python scripts/stabilization_orchestration_engine.py \
  --replays-json benchmark_reports/replay_scores.json \
  --output benchmark_reports/stabilization_orchestration_artifact.json
```

`replay_scores.json` format:

```json
{
  "mmlu": [61.0, 60.5, 61.2],
  "humaneval": [90.5, 90.0, 91.0],
  "gsm8k": [93.8, 94.1, 93.9],
  "mmmlu": [84.0, 84.2, 83.8],
  "long_context": [95.0, 95.1, 94.9],
  "tool_use": [83.0, 83.5, 83.3],
  "rag": [49.0, 50.1, 49.4],
  "dialogue": [6.2, 6.1, 6.3]
}
```

If replay scores are omitted, the artifact marks variance values as missing (artifact-backed only policy).
