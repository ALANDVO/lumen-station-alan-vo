"""
Reproducible evaluation benchmark for AI/ML context window optimization.
Run command: python3 -m app.evaluation.evaluate_context_savings
"""

import json
import time
import tempfile
import sqlite3
import os
from typing import Dict, Any, List

from app.services.sandbox_engine import fold_large_output
from app.services.search_index import estimate_tokens, split_into_bounded_chunks


def generate_benchmark_workloads() -> List[Dict[str, Any]]:
    """
    Generate deterministic synthetic workloads modeling real agent tool outputs.
    Data provenance:
    - Workload A: Comprehensive test suite run (500 test cases with failure traces)
    - Workload B: Large multi-file git diff (25 files changed across full-stack repo)
    - Workload C: Verbose TypeScript & Vite build log with rollup chunk tree
    - Workload D: Tiny shell output (single-line status check - edge case)
    """
    # Workload A: 500 test cases
    test_lines = ["============================= test session starts ==============================\n"]
    for i in range(1, 501):
        if i in {42, 118, 305}:
            test_lines.append(f"FAILED tests/test_core.py::test_case_{i} - AssertionError: Expected status 200 but got 500\n")
            test_lines.append(f"    Traceback (most recent call last):\n      File 'test_core.py', line {i}\n        assert resp.status_code == 200\n")
        else:
            test_lines.append(f"tests/test_unit.py::test_item_{i} PASSED [ {i/5.0:.1f}% ]\n")
    test_lines.append("======================== 3 failed, 497 passed in 14.82s =========================\n")
    workload_a = "".join(test_lines)

    # Workload B: Multi-file git diff
    diff_lines = ["diff --git a/src/index.ts b/src/index.ts\nindex 8a34bc1..9f81cd2 100644\n--- a/src/index.ts\n+++ b/src/index.ts\n"]
    for f_idx in range(1, 30):
        diff_lines.append(f"diff --git a/src/module_{f_idx}.ts b/src/module_{f_idx}.ts\n")
        diff_lines.append("@@ -1,20 +1,35 @@\n")
        for line_idx in range(1, 40):
            diff_lines.append(f"+ export const helper_{f_idx}_{line_idx} = () => {{ return 'val_{line_idx}'; }};\n")
    workload_b = "".join(diff_lines)

    # Workload C: Build log
    build_lines = ["vite v5.4.8 building for production...\ntransforming...\n"]
    for mod in range(1, 350):
        build_lines.append(f"node_modules/pkg_{mod}/index.mjs (12.4 kB)\n")
    build_lines.append("✓ 350 modules transformed.\nrendering chunks...\ncomputing gzip size...\ndist/index.html   0.45 kB\ndist/assets/index.js   412.80 kB │ gzip: 114.20 kB\n✓ built in 1.45s\n")
    workload_c = "".join(build_lines)

    # Workload D: Edge case - tiny output
    workload_d = "OK: Branch main is up to date with origin/main.\n"

    return [
        {"name": "pytest_500_tests", "workload": workload_a, "type": "test_suite"},
        {"name": "git_diff_30_files", "workload": workload_b, "type": "version_control_diff"},
        {"name": "vite_build_350_modules", "workload": workload_c, "type": "compiler_build_log"},
        {"name": "tiny_status_check", "workload": workload_d, "type": "edge_case_minimal"},
    ]


def run_evaluation() -> Dict[str, Any]:
    """Execute reproducible context window optimization evaluation."""
    workloads = generate_benchmark_workloads()
    results = []

    total_raw_tokens = 0
    total_compact_tokens = 0
    total_latency_ms = 0.0

    for item in workloads:
        content = item["workload"]
        t_start = time.perf_counter()

        raw_tok = estimate_tokens(content)
        compact_text, omitted_lines, omitted_bytes = fold_large_output(
            content=content,
            execution_id="eval-bench-run",
            head_lines_count=25,
            tail_lines_count=25,
        )
        compact_tok = estimate_tokens(compact_text)

        chunks = split_into_bounded_chunks(content, max_bytes=65536)

        duration = (time.perf_counter() - t_start) * 1000.0

        if raw_tok > 0:
            savings_pct = round(max(0.0, (raw_tok - compact_tok) / float(raw_tok)) * 100.0, 2)
        else:
            savings_pct = 0.0

        total_raw_tokens += raw_tok
        total_compact_tokens += compact_tok
        total_latency_ms += duration

        results.append({
            "workload_name": item["name"],
            "workload_type": item["type"],
            "raw_bytes": len(content.encode("utf-8")),
            "raw_tokens": raw_tok,
            "compact_tokens": compact_tok,
            "savings_percentage": savings_pct,
            "omitted_lines": omitted_lines,
            "bounded_chunks_created": len(chunks),
            "latency_ms": round(duration, 3),
        })

    overall_savings_pct = round(
        max(0.0, (total_raw_tokens - total_compact_tokens) / float(total_raw_tokens)) * 100.0, 2
    )

    evaluation_summary = {
        "benchmark_suite": "Lumen Station Context Window Optimization v1.0",
        "timestamp": "2026-10-12T15:45:00Z",
        "data_provenance": "Synthetic standardized developer traces modeled from real coding agent execution logs",
        "baseline_comparison": "Uncompressed raw tool stdout/stderr fed directly into LLM prompt",
        "aggregate_metrics": {
            "total_raw_tokens": total_raw_tokens,
            "total_compact_tokens": total_compact_tokens,
            "saved_tokens": total_raw_tokens - total_compact_tokens,
            "overall_context_reduction_percentage": overall_savings_pct,
            "mean_processing_latency_ms": round(total_latency_ms / len(workloads), 3),
        },
        "workload_results": results,
        "boundary_limitations": [
            "Small outputs (<50 tokens): fold threshold bypasses compression to prevent fold-banner expansion.",
            "Raw unformatted binary data: stream should be truncated or converted to hex before FTS tokenization.",
        ],
    }

    return evaluation_summary


def main():
    report = run_evaluation()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
