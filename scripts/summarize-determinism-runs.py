#!/usr/bin/env python3
"""Summarize customer-visible finding counts across determinism benchmark runs."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    storage = Path(sys.argv[1])
    runs = int(sys.argv[2])
    counts: list[int] = []
    tp_counts: list[int] = []
    for report in sorted(storage.glob("reports/*.json"))[-runs:]:
        payload = json.loads(report.read_text(encoding="utf-8"))
        validation = payload.get("customer_validation") or {}
        counts.append(int(validation.get("customer_visible_count", 0)))
        metrics = payload.get("metrics") or {}
        tp_counts.append(int(metrics.get("true_positive_count", 0)))

    if not counts:
        print(json.dumps({"error": "no_reports_found", "runs": runs}))
        return

    avg = sum(counts) / len(counts)
    variance_pct = 0.0
    if avg > 0:
        variance_pct = ((max(counts) - min(counts)) / avg) * 100.0

    print(
        json.dumps(
            {
                "runs": len(counts),
                "customer_visible_counts": counts,
                "true_positive_counts": tp_counts,
                "customer_visible_variance_pct": round(variance_pct, 2),
                "tp_stable": len(set(tp_counts)) == 1,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
