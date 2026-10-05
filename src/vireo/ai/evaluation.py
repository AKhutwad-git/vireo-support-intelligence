"""Metrics for reviewed labels and model outputs; missing model runs are explicit."""
from __future__ import annotations
from collections import Counter


def score_classification(labels, predictions):
    pairs = [(labels[k], predictions[k]) for k in labels if k in predictions and predictions[k] is not None]
    if not pairs: return {"sample_size": len(labels), "evaluated_count": 0, "accuracy": None, "macro_f1": None}
    classes = sorted(set(labels.values()) | {p for _, p in pairs})
    correct = sum(a == b for a,b in pairs)
    f1s = []
    for cls in classes:
        tp = sum(a == cls and b == cls for a,b in pairs)
        fp = sum(a != cls and b == cls for a,b in pairs)
        fn = sum(a == cls and b != cls for a,b in pairs)
        f1s.append((2*tp/(2*tp+fp+fn)) if (2*tp+fp+fn) else 0.0)
    return {"sample_size": len(labels), "evaluated_count": len(pairs), "accuracy": correct/len(pairs), "macro_f1": sum(f1s)/len(f1s)}


def error_flags(result, supplied_text):
    serialized = str(result).casefold()
    causal_terms = ("caused by agent", "agent caused", "agent fault", "because of the agent")
    return {"unsupported_claim": any(term in serialized for term in causal_terms),
        "unsupported_evidence": bool(result.get("evidence")) and not any(result["evidence"] in text for text in supplied_text),
        "missing_evidence": result.get("evidence_strength") != "insufficient" and not result.get("evidence"),
        "overstated_confidence": result.get("confidence", 0) > 0.9 and result.get("evidence_strength") in ("low", "insufficient")}
