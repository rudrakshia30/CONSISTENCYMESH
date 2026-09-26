"""Candidate pair scoring using TF-IDF and metadata overlap."""

from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.core.config import Settings
from backend.models.schemas import Clause


class CandidateScorer:
    """Scores cross-document clause pairs using TF-IDF cosine similarity
    and Jaccard overlap of topics, entities, and dates.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._vectorizer: TfidfVectorizer | None = None
        self._tfidf_matrix: Any = None
        self._clause_id_to_idx: dict[str, int] = {}
        self._clauses: list[Clause] = []
        self._topics_map: dict[str, set[str]] = {}
        self._entities_map: dict[str, set[str]] = {}
        self._dates_map: dict[str, set[str]] = {}

    def build_index(self, clauses: list[Clause]) -> None:
        """Build the TF-IDF index and pre-cache metadata sets from a list of clauses.

        Args:
            clauses: All clauses across all documents in the analysis.
        """
        self._clauses = clauses
        self._clause_id_to_idx = {clause.clause_id: idx for idx, clause in enumerate(clauses)}
        self._topics_map = {clause.clause_id: set(clause.topics) for clause in clauses}
        self._entities_map = {clause.clause_id: set(clause.entities) for clause in clauses}
        self._dates_map = {clause.clause_id: set(clause.dates) for clause in clauses}

        if not clauses:
            return

        texts = [clause.text for clause in clauses]
        self._vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
        try:
            self._tfidf_matrix = self._vectorizer.fit_transform(texts)
        except ValueError:
            # Handle empty/short texts
            self._tfidf_matrix = None

    def _jaccard(self, set_a: set[str], set_b: set[str]) -> float:
        """Compute Jaccard similarity between two sets.

        Args:
            set_a: First set.
            set_b: Second set.

        Returns:
            Jaccard similarity in [0, 1].
        """
        if not set_a and not set_b:
            return 0.0
        union = len(set_a | set_b)
        if union == 0:
            return 0.0
        return len(set_a & set_b) / union

    def score_pair(self, clause_a: Clause, clause_b: Clause) -> float:
        """Compute composite similarity score for a clause pair.

        Composite score formula:
            w_topic * topic_jaccard +
            w_entity * entity_jaccard +
            w_date * date_jaccard +
            w_tfidf * tfidf_cosine

        Args:
            clause_a: First clause.
            clause_b: Second clause.

        Returns:
            Composite score in [0, 1].
        """
        topics_a = self._topics_map.get(clause_a.clause_id) or set(clause_a.topics)
        topics_b = self._topics_map.get(clause_b.clause_id) or set(clause_b.topics)
        topic_score = self._jaccard(topics_a, topics_b)

        entities_a = self._entities_map.get(clause_a.clause_id) or set(clause_a.entities)
        entities_b = self._entities_map.get(clause_b.clause_id) or set(clause_b.entities)
        entity_score = self._jaccard(entities_a, entities_b)

        dates_a = self._dates_map.get(clause_a.clause_id) or set(clause_a.dates)
        dates_b = self._dates_map.get(clause_b.clause_id) or set(clause_b.dates)
        date_score = self._jaccard(dates_a, dates_b)

        partial_score = (
            self._settings.candidate_topic_overlap_weight * topic_score
            + self._settings.candidate_entity_overlap_weight * entity_score
            + self._settings.candidate_date_overlap_weight * date_score
        )

        max_possible_tfidf = self._settings.candidate_tfidf_weight
        threshold = self._settings.candidate_composite_threshold

        # Early exit: if even a 1.0 TF-IDF score cannot reach threshold, skip TF-IDF calculation
        if partial_score + max_possible_tfidf < threshold:
            return float(partial_score)

        tfidf_score = 0.0
        if (
            self._tfidf_matrix is not None
            and clause_a.clause_id in self._clause_id_to_idx
            and clause_b.clause_id in self._clause_id_to_idx
        ):
            idx_a = self._clause_id_to_idx[clause_a.clause_id]
            idx_b = self._clause_id_to_idx[clause_b.clause_id]
            vec_a = self._tfidf_matrix[idx_a]
            vec_b = self._tfidf_matrix[idx_b]
            # Fast sparse dot product (TF-IDF rows are L2-normalized)
            sim = float(vec_a.dot(vec_b.T).toarray()[0, 0])
            tfidf_score = max(0.0, sim)

        composite = partial_score + self._settings.candidate_tfidf_weight * tfidf_score
        return float(composite)

    def filter_candidates(
        self, pairs: list[tuple[Clause, Clause]]
    ) -> list[tuple[Clause, Clause, float]]:
        """Score all pairs and filter out those below composite_threshold.

        Args:
            pairs: List of cross-document clause pairs.

        Returns:
            List of (clause_a, clause_b, score) tuples for pairs meeting threshold,
            sorted descending by composite score.
        """
        results: list[tuple[Clause, Clause, float]] = []
        threshold = self._settings.candidate_composite_threshold

        for clause_a, clause_b in pairs:
            score = self.score_pair(clause_a, clause_b)
            if score >= threshold:
                results.append((clause_a, clause_b, score))

        results.sort(key=lambda x: x[2], reverse=True)
        return results
