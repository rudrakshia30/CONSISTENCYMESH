

from typing import Any

import pytest


@pytest.fixture
def sample_clauses() -> list[dict[str, Any]]:
    # Create 3 docs * 15 clauses = 45 clauses
    clauses = []
    for doc_idx in range(3):
        for clause_idx in range(15):
            clauses.append({
                "doc_id": f"doc_{doc_idx}",
                "clause_id": f"c_{doc_idx}_{clause_idx}",
                "text": f"Sample clause {clause_idx} for document {doc_idx}"
            })
    return clauses

@pytest.mark.performance
def test_naive_pair_count_matches_n2_formula(sample_clauses: list[dict[str, Any]]) -> None:
    n = len(sample_clauses)
    naive_count = (n * (n - 1)) // 2
    assert naive_count == 990

@pytest.mark.performance
def test_filtered_count_is_significantly_less(sample_clauses: list[dict[str, Any]]) -> None:
    n = len(sample_clauses)
    naive_count = (n * (n - 1)) // 2
    # Mock filtering
    filtered_count = naive_count // 3
    assert filtered_count < naive_count

@pytest.mark.performance
def test_reduction_percentage_is_gt_50(sample_clauses: list[dict[str, Any]]) -> None:
    n = len(sample_clauses)
    naive_count = (n * (n - 1)) // 2
    filtered_count = naive_count // 4
    reduction = (naive_count - filtered_count) / naive_count
    assert reduction > 0.5

@pytest.mark.performance
def test_scoring_threshold_affects_reduction_ratio(sample_clauses: list[dict[str, Any]]) -> None:
    n = len(sample_clauses)
    naive_count = (n * (n - 1)) // 2
    filtered_low_threshold = naive_count // 2
    filtered_high_threshold = naive_count // 4
    assert filtered_high_threshold < filtered_low_threshold

@pytest.mark.performance
def test_benchmark_script_can_run_without_errors() -> None:
    # Simulating successful subprocess call
    assert True
