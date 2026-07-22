# Benchmark Metric Definitions (Faz 11.5)

This document unifies benchmark classification labels used in code (`benchmark_matching_service.py`) and release reporting.

## Classification labels

| Label | Code constant | Definition |
|-------|---------------|------------|
| True positive (TP) | `true_positive` | Supported + `detection_required=True` expected item matched to one actual finding |
| False negative (FN) | `false_negative` | Supported + `detection_required=True` expected item with no match |
| Confirmed false positive | `confirmed_false_positive` | Unmatched actual finding; not duplicate, informational, or matcher failure |
| Valid additional finding | `valid_additional_finding` | Supported expected item with `detection_required=False` matched |
| Informational | `out_of_scope_informational` | Unmatched info-severity or known informational correlation keys |
| Duplicate | `duplicate` | Extra instance of an already matched finding |
| Matcher failure | `matcher_failure` | Unmatched finding that would match an FN under relaxed rules |
| Ground truth gap | `ground_truth_missing` | Expected item marked `manual_only` or `unsupported` |

## Precision / recall inclusion

**Precision** = `TP / (TP + confirmed_false_positive)`

Included: TP, confirmed FP  
Excluded: duplicates, informational, valid additional, matcher failures, coverage gaps, partial metrics

**Recall** = `TP / required_supported_detection_required_count`

Included: TP, required supported expected items  
Excluded: duplicates, informational, valid additional, confirmed FP, matcher failures, coverage gaps

**Partial recall** is reported separately for `partially_supported` expected items and is not mixed into main recall.

## Customer-visible validation layer

Benchmark raw findings are never deleted. A separate validation layer (`customer_validation.py`) classifies customer publication readiness:

- `confirmed` — independent validator evidence (header, CORS preflight, OpenAPI body signature)
- `high_confidence` — strong scanner/header evidence with lower customer impact
- `needs_review` — insufficient independent evidence
- `informational` — excluded from customer risk aggregates

Suppression reasons and raw finding counts are always recorded in validation artifacts.

## Risk Engine metric note

Official Risk Engine metrics use **human-labeled** cases only. Severity agreement compares the **predicted severity band derived from `calculate_risk_score()`** to the human severity label. Severity band compliance compares the numeric score to the expected score range. These measure different dimensions and can diverge.
