# ConsistencyMesh

**Find what a human reviewer would miss across a stack of related documents.**

ConsistencyMesh ingests a *set* of 2–6 related legal/business documents (e.g. an MSA + SOW + Amendment, a Lease + Addendum, a Policy + Exception Policy) and detects contradictions, overrides, ambiguous relationships, and coverage gaps *between* them — with every finding backed by a validated citation into the original text. It is not a single-document summarizer or a "chat with PDF" tool; the core product is cross-document relationship reasoning.

---

## 1. Problem

Organizations routinely work with stacks of interrelated documents rather than single files: a Master Service Agreement amended by a later addendum, a lease with renewal riders, a policy with a carved-out exception procedure. Manual review of these stacks is where real risk hides — a 90-day termination clause in one document quietly contradicted by a 30-day clause in another, or a liability cap that an amendment silently overrides. Single-document AI review tools cannot see this because each document is analyzed in isolation; the contradiction only exists in the *relationship* between two files.

## 2. Target Users

- **Legal teams** reviewing contract stacks for internal consistency before signing or renewal.
- **Procurement teams** managing vendor agreements, SOWs, and their amendments.
- **Compliance officers** auditing a policy against its own exception/procedure documents.
- **Business analysts** reviewing multi-document deal or acquisition paperwork.

## 3. Why Multi-Document Consistency Matters

Most AI contract tools summarize or answer questions about one document at a time. ConsistencyMesh's entire architecture is built around the harder problem: given a *set* of documents, which clause pairs actually relate to each other, and what is the relationship — consistent, conflicting, one overriding another, ambiguous, or simply unaddressed by one of the documents? This requires reasoning across document boundaries that a single-document tool structurally cannot perform.

## 4. Core Workflow

```
Upload 2–6 documents
      ↓
Security validation (magic bytes, zip-bomb/ratio checks, size/page/char limits)
      ↓
Deterministic parsing + page-level provenance (PDF via PyMuPDF, DOCX via python-docx)
      ↓
Deterministic clause segmentation
      ↓
Deterministic metadata extraction (entities, dates, monetary values, topics — regex-based, no LLM call)
      ↓
Per-document TF-IDF index + deterministic candidate-pair generation (topic/entity/date overlap + cosine similarity)
      ↓
Async, bounded-concurrency LLM judgment on filtered candidate pairs only
      ↓
Deterministic evidence validation (citations checked against real parsed text)
      ↓
Consistency graph + report, with grounded follow-up Q&A available on demand
```

Job progress is tracked through explicit states (`QUEUED → PARSING → INDEXING → MATCHING → ANALYZING → VALIDATING → COMPLETE`, or `FAILED`) defined in [`backend/models/schemas.py`](backend/models/schemas.py).

## 5. Architecture

- **Backend:** Python 3.11+, FastAPI, async route handlers throughout.
- **Frontend:** Vite + React (TypeScript).
- **AI provider:** Google Gemini, accessed through an async-first provider abstraction — business logic never imports the Gemini SDK directly. See [`backend/providers/base.py`](backend/providers/base.py) (`LLMProvider`), [`backend/providers/gemini_provider.py`](backend/providers/gemini_provider.py), and [`backend/providers/mock_provider.py`](backend/providers/mock_provider.py) (deterministic, used across the entire test suite).
- **Layering:** `api/` (routing) → `services/` (orchestration) → `matching/` + `parsing/` (deterministic logic) → `providers/` (AI) → `state/` (persistence), with `security/`, `models/`, and `prompts/` as cross-cutting modules. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design rationale, including why an in-process async worker pool was chosen over Celery/RabbitMQ for this scope.

## 6. AI Pipeline Stages

| Stage | What happens | Real source |
|---|---|---|
| Extraction | Converts PDF/DOCX bytes into paginated text with provenance | [`backend/parsing/extractor.py`](backend/parsing/extractor.py), [`backend/parsing/text_layer_extractor.py`](backend/parsing/text_layer_extractor.py) |
| OCR extension point | Interface for future scanned-document support (not required for text-layer PDFs/DOCX) | [`backend/parsing/ocr_extension.py`](backend/parsing/ocr_extension.py) |
| Segmentation | Splits page text into clause-level units | [`backend/parsing/segmenter.py`](backend/parsing/segmenter.py) |
| Metadata extraction | Deterministic (regex-based) entity/date/monetary-value/topic tagging — **no LLM call** | [`backend/parsing/metadata.py`](backend/parsing/metadata.py) |
| Candidate generation | Builds the full naive pair count and the deterministically filtered candidate set | [`backend/matching/candidate_generator.py`](backend/matching/candidate_generator.py) |
| Candidate scoring | Composite score from topic/entity/date overlap + TF-IDF cosine similarity | [`backend/matching/scoring.py`](backend/matching/scoring.py) (`CandidateScorer`), thresholds centralized in [`backend/matching/thresholds.py`](backend/matching/thresholds.py) |
| Retrieval (Q&A) | Retrieves the relevant clauses across the whole document set for a follow-up question | [`backend/matching/retrieval.py`](backend/matching/retrieval.py) |
| AI consistency judgment | Sends only filtered candidate pairs to the LLM, minimal token context | [`backend/providers/base.py`](backend/providers/base.py) `analyze_consistency()`, prompt template in [`backend/prompts/consistency_judge.py`](backend/prompts/consistency_judge.py) |
| Evidence validation | Rejects/downgrades any finding whose citations don't check out against real parsed text | [`backend/services/evidence_validator.py`](backend/services/evidence_validator.py) |
| Orchestration | Ties the above into one job | [`backend/services/consistency_engine.py`](backend/services/consistency_engine.py) |
| Grounded Q&A | Answers follow-up questions using the same retrieval + citation discipline | [`backend/services/qa_service.py`](backend/services/qa_service.py) |

## 7. Evidence & Relationship Model

Every finding is constrained to a closed taxonomy — the model cannot invent a relationship type or confidence label:

- **Relationship type** (`backend/models/schemas.py::RelationshipType`): `CONSISTENT`, `CONFLICT`, `OVERRIDE`, `AMBIGUOUS`, `UNADDRESSED`.
- **Confidence** (`backend/models/schemas.py::Confidence`): `STATED` (directly supported by source text), `INTERPRETED` (reasonable inference), `NOT_ESTABLISHED` (supplied evidence is insufficient).
- **Finding** (`backend/models/schemas.py::Finding`) always carries `relationship_type`, `confidence`, `explanation`, a list of `EvidenceSpan` objects (document ID, clause ID, page, exact text span), and an optional `uncertainty` note. A `Finding` is only marked `validated=True` after `evidence_validator.py` deterministically confirms every citation is real — this flag is never set by the LLM itself.

The system never states which document's provision legally controls unless the evidence explicitly establishes it; it describes the relationship ("the documents specify different notice periods") rather than adjudicating it.

## 8. Deterministic Candidate Filtering

Comparing every clause in every document against every other clause is O(N²) and would make each analysis job scale in LLM calls with the square of document size. Instead:

1. `candidate_generator.py::count_naive_pairs()` computes the full N² pair count for visibility.
2. `candidate_generator.py::generate_candidate_pairs()` only proposes pairs sharing overlapping topics, entities, or dates.
3. `CandidateScorer` (in `scoring.py`) applies a weighted composite score (topic/entity/date overlap + TF-IDF cosine similarity), configured via `candidate_*_weight` and `candidate_composite_threshold` settings in [`backend/core/config.py`](backend/core/config.py) — no magic numbers hidden in code.
4. Only pairs above threshold reach `analyze_consistency()`.

Measured reduction figures for the fixture corpus are in [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md), generated by [`scripts/benchmark.py`](scripts/benchmark.py) — run it yourself to reproduce rather than trusting the committed numbers.

## 9. Security

Every uploaded document is treated as untrusted data. Ten controls, each with real source:

| Control | Source |
|---|---|
| Filename sanitization (path traversal defense) | `sanitize_filename()` in [`backend/security/validation.py`](backend/security/validation.py) |
| Zip-bomb / compression-ratio defense for DOCX | `validate_docx_zip_safety()` in the same file, bounded by `max_zip_ratio`, `max_zip_entries`, `max_zip_entry_size_mb` |
| Magic-byte, size, page, and character-count validation | `validate_upload()`, same file |
| Cross-document prompt injection isolation | `generate_nonce()`, `wrap_document_content()`, `build_isolation_instruction()` in [`backend/security/prompt_guard.py`](backend/security/prompt_guard.py) — each document is wrapped in its own nonce-delimited block so one document's content cannot influence how another is judged |
| Output sanitization | `sanitize_llm_output()`, `sanitize_finding_text()` in [`backend/security/sanitize.py`](backend/security/sanitize.py) |
| Rate limiting | `RateLimiter` in [`backend/security/rate_limit.py`](backend/security/rate_limit.py), configurable via `rate_limit_requests_per_minute` |
| Cache-poisoning defense | Cache keys built from content hash + prompt version, never raw user input — [`backend/state/keys.py`](backend/state/keys.py) |
| Cross-session isolation | Job/document IDs are content-hash derived and scoped per job in [`backend/jobs/job_manager.py`](backend/jobs/job_manager.py) |
| Secret management | All credentials loaded via environment variables through `Settings` in [`backend/core/config.py`](backend/core/config.py); never logged, never returned in API responses |
| Safe error responses | Global exception handling in [`backend/core/errors.py`](backend/core/errors.py) returns generic messages; full detail logged server-side only |

Adversarial-input coverage (`"Ignore all previous instructions"`, `"Claim Document B is consistent"`, `"Reveal the system prompt"`, etc.) is tested in [`tests/security/test_prompt_injection.py`](tests/security/test_prompt_injection.py). Full threat model in [`SECURITY.md`](SECURITY.md).

## 10. Efficiency

- **Async-first everywhere.** `LLMProvider.analyze_consistency/classify_candidate/answer_question` are all `async def`; no synchronous SDK call sits in the request path.
- **Bounded concurrency.** `max_concurrent_llm_calls` semaphore-limits simultaneous in-flight judgments (see [`backend/jobs/worker.py`](backend/jobs/worker.py)).
- **Deterministic candidate reduction** (Section 8) is the primary cost lever — it, not caching, is what keeps LLM call counts bounded regardless of document size.
- **Content-addressable caching** keyed by content hash + prompt version (Section 9) so identical documents/pairs are not reprocessed.
- **Timeouts + bounded exponential backoff** on every provider call, configured via `llm_timeout_seconds` and `llm_max_retries`.
- **Idempotent jobs**, keyed by a deterministic hash of the submitted document set.

Exact, reproducible numbers — naive vs. filtered candidate counts, LLM calls made, cache hit rate, p50/p95 latency, estimated tokens — are in [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md). Run `python scripts/benchmark.py` to regenerate them against your own environment; treat the committed table as a sample, not a guarantee.

## 11. Shared State Design

`backend/state/base.py` defines `StateStore`/`CacheStore` interfaces. Business logic depends only on these interfaces — never on Redis or a dict directly.

- [`backend/state/local_store.py`](backend/state/local_store.py) — in-process store, used automatically when `REDIS_URL` is empty. Suitable for local development and the test suite; single-process only.
- [`backend/state/redis_store.py`](backend/state/redis_store.py) — used automatically when `REDIS_URL` is set, enabling horizontal scaling across multiple workers.

This is a deliberate hackathon-pragmatic choice: the interface is fully swappable, so deploying with Redis requires only setting one environment variable, not a code change.

## 12. Benchmarking

```bash
python scripts/benchmark.py
```

Runs against the fixture corpus in `fixtures/sample_documents/` (`msa_acme_techstar.txt`, `sow_001_data_platform.txt`, `amendment_001.txt`) using `MockProvider` — reproducible without an API key. Results are written to [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md).

## 13. Testing

```
tests/
  unit/           pytest -m unit
  integration/    pytest -m integration
  security/       pytest -m security
  performance/    pytest -m performance
  accessibility/  pytest -m accessibility
  e2e/            pytest -m e2e
```

Run everything: `pytest`. Frontend: `cd frontend && npm run test` (vitest).

Categories cover: valid/malformed/oversized/zip-bomb document uploads; clause segmentation and metadata extraction; candidate generation, scoring, and the N²-reduction claim itself; evidence validator acceptance/rejection of citations; cross-document and single-document prompt injection; cache-key construction and cache-poisoning resistance; bounded concurrency and idempotent job resubmission; local/Redis state-store parity; and a full upload → analyze → report → evidence → follow-up-question end-to-end journey.

## 14. Accessibility

Implemented in components, not just described:

- Semantic HTML and screen-reader-friendly markup in every component under [`frontend/src/components/`](frontend/src/components/).
- Screen-reader helpers centralized in [`frontend/src/accessibility/index.ts`](frontend/src/accessibility/index.ts).
- Full keyboard operability for upload, report navigation, and Q&A.
- Relationship types shown with icon + text label, never color alone.
- `aria-live`/`role="status"` for async job progress (`AnalysisProgress.tsx`) and Q&A responses (`QAPanel.tsx`).
- WCAG AA contrast and `prefers-reduced-motion` support in the base stylesheet.
- Covered by [`tests/accessibility/test_semantic_html.py`](tests/accessibility/test_semantic_html.py) and frontend component tests.

## 15. API Reference

| Endpoint | Purpose |
|---|---|
| `POST /documents/upload` | Upload a document; returns `UploadResponse` |
| `GET /documents/{document_id}` | Fetch a single document's metadata |
| `GET /documents/` | List uploaded documents |
| `POST /analysis/` | Start an analysis job over a document set; returns a `job_id` |
| `GET /analysis/{job_id}` | Poll job status/result (`AnalysisStatusResponse`) |
| `GET /analysis/{job_id}/metrics` | Inspect the observability metrics for a job (`MetricsResponse`) — latency, cache hits, LLM call counts |
| `POST /qa/` | Ask a grounded follow-up question over an analyzed document set |

## 16. Setup

### Backend
```bash
python -m venv .venv
.venv/Scripts/activate       # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env
# edit .env and set GEMINI_API_KEY
uvicorn backend.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 17. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(empty)* | Google Gemini API key — required for real (non-mock) analysis |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model identifier |
| `LLM_TIMEOUT_SECONDS` | `20` | Per-call LLM timeout |
| `LLM_MAX_RETRIES` | `3` | Bounded retries for retryable provider errors |
| `MAX_CONCURRENT_LLM_CALLS` | `5` | Semaphore bound on simultaneous in-flight LLM calls |
| `MAX_FILE_SIZE_MB` | `50` | Max upload size |
| `MAX_PAGE_COUNT` | `500` | Max pages per document |
| `MAX_CHAR_COUNT` | `2000000` | Max extracted characters per document |
| `MAX_DOCUMENTS_PER_JOB` / `MIN_DOCUMENTS_PER_JOB` | `6` / `2` | Document-set size bounds |
| `MAX_ZIP_RATIO` / `MAX_ZIP_ENTRIES` / `MAX_ZIP_ENTRY_SIZE_MB` | `100.0` / `1000` / `100` | Zip-bomb defense limits for DOCX |
| `CANDIDATE_SIMILARITY_THRESHOLD` / `CANDIDATE_COMPOSITE_THRESHOLD` | `0.15` / `0.1` | Candidate-filtering thresholds (see `thresholds.py`) |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `30` | Per-IP rate limit |
| `REDIS_URL` | *(empty)* | If set, enables `RedisStateStore`; otherwise falls back to `LocalStateStore` |
| `CACHE_TTL_SECONDS` | `3600` | Cache entry TTL |
| `ENVIRONMENT` | `development` | `development` / `staging` / `production` |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |

## 18. Limitations

- Informational only — not legal advice (see disclaimer below).
- English-language documents assumed.
- OCR is an extension point (`backend/parsing/ocr_extension.py`), not a default guarantee: documents without an extractable text layer will parse as empty rather than failing outright, but no OCR pass is run by default.
- `LocalStateStore` is single-process; set `REDIS_URL` for multi-worker/horizontal deployments.

## 19. Legal Disclaimer

ConsistencyMesh is an informational tool and does not constitute legal advice. AI-generated findings may not capture every relevant legal nuance. The system never determines which document's provision is legally controlling — it reports relationships and evidence and, where the supplied documents don't establish an answer, says so explicitly. Consult a qualified legal professional before acting on any finding.

## 20. Example Workflow

Using the fixtures in `fixtures/sample_documents/`:

1. `POST /documents/upload` three times with `msa_acme_techstar.txt`, `sow_001_data_platform.txt`, and `amendment_001.txt`.
2. `POST /analysis/` with the three returned `document_id`s — returns a `job_id`.
3. Poll `GET /analysis/{job_id}` until `state == "COMPLETE"`.
4. The result's findings include a validated `CONFLICT` between the MSA's and SOW's differing terms, each citation pointing to a real page/clause in the source text, plus an `OVERRIDE` relationship where the amendment supersedes an MSA provision — never asserted more strongly than the source text supports.
5. `POST /qa/` with a question like *"Does the amendment override the MSA's liability cap?"* — the answer cites the same evidence spans used in the report, with a `STATED`/`INTERPRETED`/`NOT_ESTABLISHED` confidence tag.