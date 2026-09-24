# Architecture

## AI Pipeline
The ConsistencyMesh AI pipeline is designed to be a robust, multi-stage process combining deterministic processing and bounded AI concurrency.

```text
[Upload] 
   |
[Security Validation]
   |
[Parsing]
   |
[Segmentation + Metadata]
   |
[TF-IDF Indexing]
   |
[Candidate Filtering]
   |
[AI Analysis] (Bounded Concurrency)
   |
[Evidence Validation]
   |
[Report]
```

- **Upload**: Accepts documents through the API.
- **Security Validation**: Validates magic bytes, file sizes, and mitigates zip-bomb threats. (See `security/validation.py`)
- **Parsing**: Extracts text and layout. (See `parsing/`)
- **Segmentation + Metadata**: Chunks the text and extracts structural metadata.
- **TF-IDF Indexing**: Creates term-frequency inverse document frequency indexes for clauses.
- **Candidate Filtering**: Reduces N² comparison space using deterministic similarity.
- **AI Analysis**: Compares candidate clauses using bounded concurrency to prevent API rate limits.
- **Evidence Validation**: Ensures AI findings correspond to actual source text.
- **Report**: Formats the final output.

The pipeline carefully isolates deterministic stages (fast, exact) from AI stages (slower, non-deterministic).

## State & Cache Design
We use a `StateStore` and `CacheStore` abstraction to handle caching and state across jobs.
- **Local vs Redis**: Local in-memory caching is fast and straightforward for local deployments. Redis provides shared state for scaled deployments.
- **Automatic fallback**: If `REDIS_URL` is set, Redis is used. Otherwise, it falls back to Local with a logged warning.
- **Content-addressable caching**: Caches use keys based on `SHA-256(content) + prompt_version + model_config`. This ensures consistency and prevents poisoning.
- **Cache key construction**: See `state/keys.py` for exact key construction details.

## Async Job Model
ConsistencyMesh implements an in-process `asyncio` task queue with a bounded worker pool.
- **Concurrency**: An `asyncio.Semaphore` limits concurrent LLM calls.
- **Job States**: Jobs transition through: `QUEUED` -> `PARSING` -> `INDEXING` -> `MATCHING` -> `ANALYZING` -> `VALIDATING` -> `COMPLETE` | `FAILED`.
- **Client polling**: Clients poll `GET /analysis/{job_id}` for status.
- **Architecture Decision**: We deliberately chose NOT to use Celery or RabbitMQ. This makes the project appropriate for a hackathon while still having a clear path to production when scaling is needed.

## Candidate Filtering
Comparing every clause against every other clause in multiple documents leads to an $O(N^2)$ problem.
- **Deterministic Filtering**: We use TF-IDF cosine similarity combined with topic/entity/date overlap to filter candidates deterministically before LLM comparison.
- **Composite Score**: The similarity score uses configurable weights for each component.
- **Measurable reduction**: This approach is proven to reduce LLM calls significantly (see `docs/BENCHMARKS.md`).
- **Implementation**: Refer to the `matching/` modules.

## Provider Abstraction
ConsistencyMesh implements an `LLMProvider` ABC to decouple from specific vendors.
- **GeminiProvider**: Uses `async httpx` with retry, timeout, and metrics logic.
- **MockProvider**: Provides deterministic responses, primarily used in tests.
- **Dependency Injection**: Providers are injected via FastAPI's `Depends`.
- **Implementation**: Refer to the `providers/` modules.

## Security Architecture
The system includes multiple layers of security:
- **Upload validation**: Checks magic bytes, size limits, and prevents zip-bombs.
- **Prompt injection**: Uses nonce-based prompt injection isolation.
- **Cache security**: Content-hash cache keys prevent cache poisoning.
- **Isolation**: Cross-session data is isolated.
- **Sanitization**: Output is strictly sanitized.
- **Rate limiting**: API endpoints are protected against abuse.
- **Implementation**: Refer to the `security/` directory and `SECURITY.md`.

## OCR Extension Point
An `OCRExtractor` stub exists in `parsing/ocr_extension.py`.
- **Interface**: The interface is defined but not yet implemented (Priority 1 for future).
- **Graceful degradation**: Scanned PDFs currently produce empty text rather than causing crashes.

## WCAG AA Color Palette
The UI strictly adheres to WCAG AA guidelines for dark mode.
- **Color contrast**: Colors are chosen to meet or exceed contrast ratios.
- **Relationship accessibility**: All relationship types use both an icon and text; color is never used as the sole indicator.
- **Motion**: The `prefers-reduced-motion` media query is respected across the application.
