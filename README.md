# ConsistencyMesh

**Find what a human reviewer would miss across a stack of related documents.**

## Problem Statement
- Organizations deal with stacks of interrelated legal/business documents (MSA + SOW + Amendment, Lease + Addendum, etc.).
- Manual review misses contradictions, overrides, and gaps between documents due to volume and cognitive overload.
- Single-document AI tools cannot detect cross-document inconsistencies because they lack context across the entire set.
- ConsistencyMesh analyzes 2-6 related documents as a **SET**, detecting conflicts, overrides, ambiguities, and coverage gaps across the entire stack.

## Target Users
- **Legal teams** reviewing contract stacks for compliance and consistency.
- **Procurement teams** managing complex vendor agreements and renewals.
- **Compliance officers** auditing policy sets and standard operating procedures.
- **Business analysts** reviewing multi-document deals and acquisitions.

## Why Multi-Document Consistency Matters
Most AI contract review tools analyze single documents in isolation. However, real-world document stacks almost always contain complex interdependencies where an Amendment overrides an MSA, or an SOW conflicts with general terms. Missing cross-document conflict detection is the #1 review failure mode. ConsistencyMesh contrasts with single-document tools by evaluating the *interplay* between multiple texts to surface true semantic inconsistencies.

## Core Workflow
```
Upload Documents 
      ↓
Security Validation 
      ↓
Text Extraction + Clause Segmentation 
      ↓
Metadata Extraction 
      ↓
TF-IDF Candidate Filtering 
      ↓
AI Pairwise Analysis 
      ↓
Evidence Validation 
      ↓
Consistency Report + Graph
```

## Architecture
- **Backend**: Python 3.11+, FastAPI, fully async implementation.
- **Frontend**: Vite + React (TypeScript) for high-performance interactive UI.
- **AI**: Google Gemini accessed via async `httpx` (never blocking sync SDK).
- See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed design decisions.

## AI Pipeline Stages
ConsistencyMesh employs an 8-stage asynchronous pipeline to ensure rigorous analysis:
1. **Extraction**: Parsers convert raw files to structured text. ([parsers](backend/parsing/))
2. **Segmentation**: Splitting text into semantic clauses. ([chunker.py](backend/parsing/chunker.py))
3. **Metadata**: AI identifies key entities, dates, and topics. ([metadata.py](backend/pipeline/metadata.py))
4. **Filtering**: Pre-AI heuristic filtering to minimize token usage. ([candidate_generator.py](backend/matching/candidate_generator.py))
5. **Pairing**: Finding related clauses across documents. ([pairing.py](backend/matching/pairing.py))
6. **Analysis**: LLM semantic consistency evaluation. ([analyzer.py](backend/pipeline/analyzer.py))
7. **Validation**: Fact-checking AI claims against source text. ([validator.py](backend/pipeline/validator.py))
8. **Aggregation**: Generating the final structured report and relationship graph. ([report.py](backend/pipeline/report.py))

## Deterministic Candidate Filtering
To solve the $O(N^2)$ explosion of comparing every clause to every other clause, we employ deterministic candidate filtering. This reduces potential pairs from $N^2$ down to $M$ highly relevant candidates.
- Uses TF-IDF cosine similarity combined with topic, entity, and date overlap scoring.
- Implemented in [candidate_generator.py](backend/matching/candidate_generator.py) and [scoring.py](backend/matching/scoring.py).
- See [BENCHMARKS.md](docs/BENCHMARKS.md) for measured reduction metrics.

## Security
ConsistencyMesh implements rigorous security controls (10 primary layers):
1. File type and magic byte validation
2. Malicious payload scanning (YARA/Regex)
3. ZIP bomb and compression attack protection
4. Path traversal prevention
5. DoS limits (size, token, concurrency)
6. PII redaction pipeline
7. Output sanitization
8. Strict CORS and headers
9. Secure state management
10. Temporary file lifecycle management
- See [SECURITY.md](docs/SECURITY.md) and [backend/security/](backend/security/) module.

## Efficiency
Designed for high throughput and low cost:
- **Async HTTP provider**: Non-blocking `httpx` for AI calls.
- **Bounded Concurrency**: Semaphores prevent API rate limits.
- **Caching**: Deduplication and aggressive response caching.
- **Idempotency**: Safe retries and failure recovery.
- See performance details in [BENCHMARKS.md](docs/BENCHMARKS.md).

## Shared State Design
ConsistencyMesh handles state seamlessly across environments:
- **StateStore/CacheStore**: Abstract interfaces for session state.
- **Auto-detection**: Attempts to connect to Redis, but gracefully falls back to a Thread-safe Local memory dictionary.
- Code at [backend/state/](backend/state/).

## Benchmarking
Run the automated benchmarking suite to verify local performance:
```bash
python scripts/benchmark.py
```
View baseline results in [BENCHMARKS.md](docs/BENCHMARKS.md).

## Testing Summary
| Category      | Test Count | How to Run                    |
|---------------|------------|-------------------------------|
| Unit          | ~83 tests  | `pytest -m unit`              |
| Integration   | ~20 tests  | `pytest -m integration`       |
| Security      | ~44 tests  | `pytest -m security`          |
| Performance   | ~15 tests  | `pytest -m performance`       |
| Accessibility | ~8 tests   | `pytest -m accessibility`     |
| E2E           | ~8 tests   | `pytest -m e2e`               |
| Frontend      |            | `npm run test` (vitest)       |
| **Total**     | **170+**   |                               |

## Accessibility
The frontend is built with an uncompromising focus on accessibility:
- Semantic HTML and ARIA labels.
- Full keyboard navigation support.
- WCAG-compliant contrast ratios.
- Reduced motion preferences respected.
- Found in [frontend/src/accessibility/](frontend/src/accessibility/) and component files.

## Setup Instructions

### Backend
```bash
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your GEMINI_API_KEY
uvicorn backend.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Environment Variables
| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Your Google Gemini API key (Required) |
| `ENVIRONMENT` | `development` or `production` |
| `REDIS_URL` | Optional Redis connection string for state |
| `LOG_LEVEL` | Application logging level (`INFO`, `DEBUG`) |
| `MAX_FILE_SIZE_MB` | Upload limit (default: 10) |
| `ALLOWED_ORIGINS` | CORS origins (default: http://localhost:5173) |

## Limitations
- **Informational only, not legal advice.**
- English-language documents assumed by default.
- OCR is a P1 extension point (graceful degradation for scanned PDFs currently returns text-layer only).
- In-memory state in single-process mode (Requires Redis for horizontal scaling).

## Legal Disclaimer
*ConsistencyMesh is an informational tool and does not constitute legal advice. AI-generated findings may not capture all relevant legal nuances. Users should consult qualified legal professionals before making decisions based on this analysis. The system does not determine which document provisions are legally controlling.*

## Example Workflow
Using the provided fixture documents:
1. **Upload**: Provide `MSA.pdf`, `SOW.pdf`, and `Amendment.pdf`.
2. **Analyze**: The system extracts text and identifies clauses across all three.
3. **Detect**: The AI flags that `SOW.pdf` states a 30-day payment term, while `MSA.pdf` requires 45 days. It also detects that `Amendment.pdf` overrides the liability cap in `MSA.pdf`.
4. **Report**: The output graph highlights the conflict (SOW vs MSA) and the valid override (Amendment vs MSA) with precise textual citations.
