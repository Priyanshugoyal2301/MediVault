# ml-eval

Reusable evaluation framework for every MediVault model under `models/*/`.

## Required metrics

Every evaluation **must** report:

| Metric | Key |
|--------|-----|
| Precision | `precision` |
| Recall | `recall` |
| F1 | `f1` |
| Accuracy | `accuracy` |
| Latency (batch / full-eval mean wall ms) | `latency_ms` |
| Model size (bytes on disk) | `model_size_bytes` |
| Memory usage (peak MiB) | `memory_mib` |
| Inference time (ms per example) | `inference_time_ms` |

## Quick start

```python
from packages.ml_eval import EvaluationRunner

runner = EvaluationRunner(
    model_name="anomaly-statistical",
    model_version="baseline",
    dataset="datasets/evaluation/anomaly_synth",
    model_path=None,  # rule-based: 0 bytes
)
report = runner.run_classification(
    y_true=labels,
    predict_all=lambda: preds,
    positive=True,
)
report.write_json("datasets/evaluation/anomaly_latest.json")
report.print_summary()
```

Retrieval models may use `run_retrieval` (Hit@k / MRR mapped into the same keys).
