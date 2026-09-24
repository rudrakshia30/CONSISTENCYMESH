"""
Deterministic candidate pair generation for ConsistencyMesh.
"""
from backend.models.schemas import Clause


def generate_candidate_pairs(clauses_by_doc: dict[str, list[Clause]]) -> list[tuple[Clause, Clause]]:
    """
    Generates all cross-document clause pairs.

    Args:
        clauses_by_doc: A dictionary grouping clauses by document_id.

    Returns:
        A list of all possible cross-document clause pairs.
    """
    doc_ids = list(clauses_by_doc.keys())
    pairs = []

    for i, doc_id_a in enumerate(doc_ids):
        for doc_id_b in doc_ids[i+1:]:
            for clause_a in clauses_by_doc[doc_id_a]:
                for clause_b in clauses_by_doc[doc_id_b]:
                    pairs.append((clause_a, clause_b))

    return pairs

def count_naive_pairs(clauses_by_doc: dict[str, list[Clause]]) -> int:
    """
    Counts total possible cross-document pairs without generating them.

    Args:
        clauses_by_doc: A dictionary grouping clauses by document_id.

    Returns:
        The total count of possible cross-document pairs.
    """
    doc_ids = list(clauses_by_doc.keys())
    total_pairs = 0

    for i, doc_id_a in enumerate(doc_ids):
        count_a = len(clauses_by_doc[doc_id_a])
        for doc_id_b in doc_ids[i+1:]:
            count_b = len(clauses_by_doc[doc_id_b])
            total_pairs += count_a * count_b

    return total_pairs
