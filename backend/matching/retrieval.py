"""Staged Hybrid Retrieval and Query-Intent-Aware Reranking module.

Combines lexical retrieval (TF-IDF), metadata/topic filtering,
numeric attribute matching, and intent-aware score penalty/boosting.
Enforces a minimum relevance threshold to prevent generic word drift.
"""

from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.models.schemas import Clause, QueryIntent
from backend.parsing.intent import extract_query_intent


def retrieve_relevant_clauses(
    query: str,
    clauses: list[Clause],
    top_k: int = 10,
    min_threshold: float = 0.25,
) -> tuple[QueryIntent, list[tuple[Clause, float]]]:
    """Retrieve and rerank relevant clauses using staged hybrid retrieval.

    Steps:
    1. Query intent extraction
    2. TF-IDF lexical similarity
    3. Topic & attribute alignment boosting
    4. Topic mismatch penalization (generic word drift defense)
    5. Minimum relevance threshold filtering

    Args:
        query: User question string.
        clauses: List of candidate clauses across documents.
        top_k: Maximum number of clauses to return.
        min_threshold: Minimum score threshold (default 0.25).

    Returns:
        Tuple of (QueryIntent, list of (Clause, reranked_score) tuples).
    """
    intent = extract_query_intent(query)

    if not clauses:
        return intent, []

    # 1. TF-IDF Lexical Similarity
    texts = [c.text for c in clauses]
    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
        query_vec = vectorizer.transform([query])
        raw_similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
    except ValueError:
        raw_similarities = np.zeros(len(clauses))

    scored_candidates: list[tuple[Clause, float]] = []

    for idx, clause in enumerate(clauses):
        tfidf_sim = float(raw_similarities[idx]) if idx < len(raw_similarities) else 0.0
        score = tfidf_sim

        clause_text_lower = clause.text.lower()
        clause_topics = set(clause.topics)

        # 2. Topic Match / Mismatch Scoring
        if intent.topic:
            if intent.topic in clause_topics or (clause.section and intent.topic in clause.section.lower()):
                score += 0.40  # Topic boost
            else:
                # Strong penalization if clause belongs to a completely different primary topic
                competing_topics = {"payment", "liability", "confidentiality", "intellectual_property", "insurance", "governing_law"}
                if clause_topics & (competing_topics - {intent.topic}):
                    score -= 0.50  # Topic mismatch penalty

        # 3. Subtopic & Attribute Alignment
        for subtopic in intent.subtopics:
            if subtopic in clause_topics or subtopic in clause_text_lower or (clause.section and subtopic in clause.section.lower()):
                score += 0.20

        # Numeric attribute match boost
        if intent.requested_attributes:
            has_numeric_match = any(
                num_attr.attribute in ["notice_period", "payment_term", "duration", "retention_period", "renewal_period"]
                for num_attr in clause.numeric_attributes
            )
            if has_numeric_match:
                score += 0.15

        # Bound score between 0.0 and 1.0
        final_score = max(0.0, min(1.0, score))

        # 4. Enforce Relevance Threshold
        if final_score >= min_threshold:
            scored_candidates.append((clause, final_score))

    # Sort descending by final score
    scored_candidates.sort(key=lambda x: x[1], reverse=True)

    return intent, scored_candidates[:top_k]
