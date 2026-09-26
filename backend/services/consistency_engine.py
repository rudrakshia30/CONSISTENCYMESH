"""
Core consistency analysis engine.

Orchestrates the full pipeline: clause loading -> candidate generation ->
deterministic filtering -> bounded concurrent AI analysis -> evidence
validation -> consistency graph construction. Includes request
deduplication for in-flight LLM calls.
"""

from __future__ import annotations

import asyncio
import time

from backend.core.config import Settings
from backend.core.logging import JobMetrics, LLMCallMetric, get_logger
from backend.matching.candidate_generator import (
    count_naive_pairs,
    generate_candidate_pairs,
)
from backend.matching.scoring import CandidateScorer
from backend.models.schemas import (
    AnalysisResult,
    Clause,
    ConsistencyEdge,
    ConsistencyGraph,
    Document,
    Finding,
    JobState,
)
from backend.prompts.consistency_judge import PROMPT_VERSION
from backend.providers.base import LLMProvider
from backend.services.evidence_validator import EvidenceValidator
from backend.state.base import CacheStore, StateStore
from backend.state.keys import build_cache_key, content_hash

logger = get_logger("services.engine")


class ConsistencyEngine:
    """Core orchestration engine for multi-document consistency analysis.

    Coordinates the full pipeline from clause loading through AI analysis
    to validated findings. Uses bounded concurrency and request
    deduplication to minimize LLM calls.

    Attributes:
        _provider: LLM provider for AI analysis.
        _state_store: State store for document/clause data.
        _cache_store: Cache store for pairwise judgment results.
        _settings: Application settings.
        _validator: Evidence validation service.
        _in_flight: Tracks in-flight LLM requests for deduplication.
    """

    def __init__(
        self,
        provider: LLMProvider,
        state_store: StateStore,
        cache_store: CacheStore,
        settings: Settings,
    ) -> None:
        """Initialize the consistency engine.

        Args:
            provider: LLM provider for analysis calls.
            state_store: State store for retrieving documents and clauses.
            cache_store: Cache store for pairwise judgment caching.
            settings: Application settings.
        """
        self._provider = provider
        self._state_store = state_store
        self._cache_store = cache_store
        self._settings = settings
        self._validator = EvidenceValidator()
        self._in_flight: dict[str, asyncio.Future[Finding | None]] = {}

    async def analyze(
        self,
        document_ids: list[str],
        session_id: str,
        job_metrics: JobMetrics,
    ) -> AnalysisResult:
        """Run the full analysis pipeline on a set of documents.

        Args:
            document_ids: List of document IDs to analyze.
            session_id: Client session ID.
            job_metrics: Metrics object to record progress.

        Returns:
            Complete analysis result with findings and consistency graph.
        """
        # 1. Load all clauses for all documents in parallel
        clauses_by_doc: dict[str, list[Clause]] = {}
        all_clauses: list[Clause] = []

        doc_clauses_results = await asyncio.gather(
            *[self._state_store.get(f"doc:{doc_id}:clauses") for doc_id in document_ids]
        )

        for doc_id, clauses_data in zip(document_ids, doc_clauses_results):
            if clauses_data is not None:
                doc_clauses = [Clause.model_validate(c) for c in clauses_data]
                clauses_by_doc[doc_id] = doc_clauses
                all_clauses.extend(doc_clauses)

        job_metrics.total_clauses = len(all_clauses)

        # 2. Count naive pairs and generate candidates
        job_metrics.naive_candidate_pairs = count_naive_pairs(clauses_by_doc)
        pairs = generate_candidate_pairs(clauses_by_doc)

        # 3. Build TF-IDF index and filter candidates
        scorer = CandidateScorer(self._settings)
        scorer.build_index(all_clauses)
        filtered = scorer.filter_candidates(pairs)
        job_metrics.filtered_candidate_pairs = len(filtered)

        logger.info(
            "Candidate filtering: %d naive -> %d filtered (%.1f%% reduction)",
            job_metrics.naive_candidate_pairs,
            job_metrics.filtered_candidate_pairs,
            job_metrics.candidate_reduction_percent,
        )

        # 4. Bounded concurrent analysis
        semaphore = asyncio.Semaphore(self._settings.max_concurrent_llm_calls)
        findings: list[Finding] = []

        async def analyze_pair(
            clause_a: Clause, clause_b: Clause, score: float
        ) -> Finding | None:
            """Analyze a single clause pair with caching and deduplication."""
            # Build cache key from sorted content hashes
            hash_a = content_hash(clause_a.text.encode("utf-8"))
            hash_b = content_hash(clause_b.text.encode("utf-8"))
            sorted_hashes = sorted([hash_a, hash_b])
            cache_key = build_cache_key(
                sorted_hashes[0] + sorted_hashes[1],
                PROMPT_VERSION,
                self._settings.gemini_model,
            )

            # Check in-flight deduplication BEFORE acquiring semaphore
            if cache_key in self._in_flight:
                return await self._in_flight[cache_key]

            # Check cache BEFORE acquiring semaphore
            cached = await self._cache_store.get_cached(cache_key)
            if cached is not None:
                job_metrics.record_llm_call(LLMCallMetric(
                    provider="cache",
                    operation="consistency_judge",
                    latency_ms=0,
                    success=True,
                    cache_hit=True,
                    estimated_tokens=0,
                ))
                return Finding.model_validate(cached)

            # Acquire semaphore ONLY for actual in-flight LLM calls
            async with semaphore:
                # Double-check in-flight after acquiring semaphore
                if cache_key in self._in_flight:
                    return await self._in_flight[cache_key]

                # Create future for deduplication
                loop = asyncio.get_running_loop()
                future: asyncio.Future[Finding | None] = loop.create_future()
                self._in_flight[cache_key] = future

                try:
                    start = time.monotonic()

                    # Call LLM provider
                    context = {
                        "doc_a_name": f"Document_{clause_a.document_id[:8]}",
                        "doc_b_name": f"Document_{clause_b.document_id[:8]}",
                    }

                    judgment = await self._provider.analyze_consistency(
                        clause_a, clause_b, context
                    )

                    latency_ms = (time.monotonic() - start) * 1000

                    # Validate evidence
                    finding = self._validator.validate_finding(
                        judgment, clause_a, clause_b
                    )

                    # Cache result
                    await self._cache_store.set_cached(
                        cache_key,
                        finding.model_dump(mode="json"),
                        ttl=self._settings.cache_ttl_seconds,
                    )

                    # Record metrics
                    est_tokens = (len(clause_a.text) + len(clause_b.text)) // 4
                    job_metrics.record_llm_call(LLMCallMetric(
                        provider="gemini",
                        operation="consistency_judge",
                        latency_ms=latency_ms,
                        success=True,
                        estimated_tokens=est_tokens,
                    ))

                    future.set_result(finding)
                    return finding

                except Exception as e:
                    logger.warning(
                        "Pair analysis failed (%s vs %s): %s",
                        clause_a.clause_id[:8],
                        clause_b.clause_id[:8],
                        str(e),
                    )
                    future.set_result(None)
                    return None
                finally:
                    self._in_flight.pop(cache_key, None)

        # Launch all pair analyses
        tasks = [
            analyze_pair(clause_a, clause_b, score)
            for clause_a, clause_b, score in filtered
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect valid findings
        for result in results:
            if isinstance(result, Finding):
                findings.append(result)

        # 5. Build consistency graph
        graph = self._build_graph(findings, document_ids)

        # 6. Load document metadata in parallel
        documents: list[Document] = []
        doc_data_results = await asyncio.gather(
            *[self._state_store.get(f"doc:{doc_id}:data") for doc_id in document_ids]
        )
        for doc_data in doc_data_results:
            if doc_data is not None:
                documents.append(Document.model_validate(doc_data))

        return AnalysisResult(
            job_id=job_metrics.job_id,
            state=JobState.COMPLETE,
            documents=documents,
            findings=findings,
            graph=graph,
            metrics=job_metrics.to_dict(),
        )

    def _build_graph(
        self, findings: list[Finding], document_ids: list[str]
    ) -> ConsistencyGraph:
        """Construct a consistency graph from validated findings.

        Args:
            findings: List of validated findings.
            document_ids: List of document IDs in the analysis.

        Returns:
            ConsistencyGraph with nodes and edges.
        """
        nodes: set[str] = set()
        edges: list[ConsistencyEdge] = []

        for finding in findings:
            if len(finding.evidence) >= 2:
                source_clause = finding.evidence[0].clause_id
                target_clause = finding.evidence[1].clause_id
                nodes.add(source_clause)
                nodes.add(target_clause)
                edges.append(ConsistencyEdge(
                    source_clause_id=source_clause,
                    target_clause_id=target_clause,
                    finding_id=finding.finding_id,
                    relationship_type=finding.relationship_type,
                ))

        return ConsistencyGraph(
            nodes=list(nodes),
            document_nodes=document_ids,
            edges=edges,
        )
