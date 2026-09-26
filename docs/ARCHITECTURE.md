# Architecture

## AI Pipeline
The ConsistencyMesh AI pipeline is designed to be a robust, multi-stage process combining deterministic processing and bounded AI concurrency.

```text
[Upload & Document Precedence Setup] 
   |
[Security Validation & Zip-Bomb Guard]
   |
[Parsing & Page Layout Extraction]
   |
[Segmentation + Precomputed Metadata & Precedence Ranking]
   |
[Precomputed TF-IDF Indexing + Sparse Matrix Dot Product]
   |
[Deterministic Candidate Filtering & Short-Circuit Early Exit]
   |
[AI Pairwise Analysis & Order of Precedence Reasoning] (Bounded Concurrency, Cache-First Semaphore)
   |
[Deterministic Citation Validation & Risk Level Triage]
   |
[Side-by-Side Comparative Report + Export API (CSV/JSON)]
```

- **Upload & Precedence**: Accepts 2-6 documents; supports tagging document types (MSA, SOW, Amendment) and order of precedence.
- **Security Validation**: Validates magic bytes, file sizes, and mitigates zip-bomb threats (`security/validation.py`).
- **Parsing**: Extracts text and page-level layout provenance (`parsing/`).
- **Segmentation + Metadata**: Chunks text into clauses, pre-caches set metadata (entities, dates, monetary values, topics, numeric attributes).
- **TF-IDF Indexing**: Pre-fits TF-IDF vectorizer and stores L2-normalized sparse matrices for fast $O(1)$ sparse dot products (`matching/scoring.py`).
- **Candidate Filtering**: Uses metadata overlap + cosine similarity with short-circuit early exit to prune unpromising pairs.
- **AI Analysis**: Analyzes candidate pairs using bounded concurrency. Checks cache and in-flight deduplication *before* acquiring semaphore slots.
- **Evidence Validation**: Ensures AI findings correspond to actual source text without fake fallback injection (`services/evidence_validator.py`). Assigns risk levels (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFORMATIONAL`).
- **Side-by-Side Comparative Report**: Renders 2-column comparative layout with risk badges and CSV audit export.

## State & Cache Design
We use a `StateStore` and `CacheStore` abstraction to handle caching and state across jobs.
- **Local vs Redis**: Local in-memory caching for local deployments; Redis for shared state across scaled workers.
- **Automatic fallback**: If `REDIS_URL` is configured, Redis is used. Otherwise, it falls back to Local with a logged warning.
- **Content-addressable caching**: Caches use keys based on `SHA-256(content) + prompt_version + model_config`.
- **Cache-first Concurrency**: Semaphore slots are only consumed for uncached, in-flight LLM calls.

## Async Job Model
ConsistencyMesh implements an in-process `asyncio` task queue with a bounded worker pool.
- **Concurrency**: An `asyncio.Semaphore` limits concurrent LLM calls (`max_concurrent_llm_calls`).
- **Parallel IO**: Non-blocking `asyncio.gather()` parallelizes state store reads.
- **Job States**: `QUEUED -> PARSING -> INDEXING -> MATCHING -> ANALYZING -> VALIDATING -> COMPLETE | FAILED`.

## Order of Precedence & Risk Triage Architecture
- **Document Precedence Hierarchy**: Documents carry precedence ranks (`precedence_rank`) and types (`MSA`, `SOW`, `Amendment`) passed into LLM context.
- **Risk Level Severity**: Findings carry risk tiers (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFORMATIONAL`) enabling immediate triage of high-risk contradictions.
- **Audit Export API**: Endpoint `GET /api/analysis/{job_id}/export?format=csv|json` provides downloadable audit trails.

## Security Architecture
- Upload validation (magic bytes, size limits, zip-bombs).
- Nonce-delimited prompt injection isolation.
- Cache-poisoning defense via content hashing.
- Output sanitization and rate limiting (`security/`).

## WCAG AA Color Palette
- High-contrast dark mode palette.
- Relationship and risk types use icons + text (never color alone).
- `prefers-reduced-motion` respected.
