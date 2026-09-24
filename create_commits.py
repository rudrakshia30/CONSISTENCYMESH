import subprocess
import sys

commits = [
    # 1-10: Project config & root docs
    ("pyproject.toml", "chore: configure pyproject tools and dependencies"),
    ("requirements.txt", "chore: add backend python dependencies"),
    (".gitignore", "chore: configure repository gitignore rules"),
    (".env.example", "chore: add example environment configuration"),
    ("render.yaml", "chore: add render blueprint configuration"),
    ("SECURITY.md", "docs: add security baseline and threat model"),
    ("CONTRIBUTING.md", "docs: add repository contribution guidelines"),
    ("README.md", "docs: add project overview and system architecture"),
    (".github/workflows/ci.yml", "ci: add automated testing workflow"),
    ("docs/.gitkeep", "chore: add docs directory placeholder"),

    # 11-17: Core & models
    ("backend/__init__.py", "feat(backend): add backend package init"),
    ("backend/core/__init__.py", "feat(core): add core module init"),
    ("backend/core/config.py", "feat(core): add system settings configuration"),
    ("backend/core/errors.py", "feat(core): add domain exception hierarchy"),
    ("backend/core/logging.py", "feat(core): add structured logging and metrics"),
    ("backend/models/__init__.py", "feat(models): add models module init"),
    ("backend/models/schemas.py", "feat(models): add domain schemas and value objects"),

    # 18-22: Security
    ("backend/security/__init__.py", "feat(security): add security module init"),
    ("backend/security/validation.py", "feat(security): add upload file validation"),
    ("backend/security/prompt_guard.py", "feat(security): add prompt injection guard"),
    ("backend/security/sanitize.py", "feat(security): add output sanitization utilities"),
    ("backend/security/rate_limit.py", "feat(security): add request rate limiter"),

    # 23-27: State & cache
    ("backend/state/__init__.py", "feat(state): add state module init"),
    ("backend/state/base.py", "feat(state): add state and cache store interfaces"),
    ("backend/state/local_store.py", "feat(state): add in-memory state store"),
    ("backend/state/redis_store.py", "feat(state): add redis state store implementation"),
    ("backend/state/keys.py", "feat(state): add cache key construction utilities"),

    # 28-35: Prompts & Providers
    ("backend/prompts/__init__.py", "feat(prompts): add prompts module init"),
    ("backend/prompts/consistency_judge.py", "feat(prompts): add consistency judge prompt template"),
    ("backend/prompts/candidate_classifier.py", "feat(prompts): add candidate classifier prompt"),
    ("backend/prompts/qa_prompt.py", "feat(prompts): add follow-up qa prompt template"),
    ("backend/providers/__init__.py", "feat(providers): add providers module init"),
    ("backend/providers/base.py", "feat(providers): add llm provider interface"),
    ("backend/providers/mock_provider.py", "feat(providers): add deterministic mock provider"),
    ("backend/providers/gemini_provider.py", "feat(providers): add google gemini async provider"),

    # 36-42: Parsing & Segmentation
    ("backend/parsing/__init__.py", "feat(parsing): add parsing module init"),
    ("backend/parsing/extractor.py", "feat(parsing): add text extractor interface"),
    ("backend/parsing/text_layer_extractor.py", "feat(parsing): add pdf and docx extractors"),
    ("backend/parsing/ocr_extension.py", "feat(parsing): add ocr extension stub"),
    ("backend/parsing/metadata.py", "feat(parsing): add metadata and numeric attribute extraction"),
    ("backend/parsing/segmenter.py", "feat(parsing): add clause segmentation engine"),
    ("backend/parsing/intent.py", "feat(parsing): add query intent extraction"),

    # 43-47: Matching & Retrieval
    ("backend/matching/__init__.py", "feat(matching): add matching module init"),
    ("backend/matching/candidate_generator.py", "feat(matching): add candidate pair generator"),
    ("backend/matching/scoring.py", "feat(matching): add composite candidate scorer"),
    ("backend/matching/thresholds.py", "feat(matching): add matching threshold definitions"),
    ("backend/matching/retrieval.py", "feat(matching): add staged hybrid retrieval engine"),

    # 48-52: Services
    ("backend/services/__init__.py", "feat(services): add services module init"),
    ("backend/services/evidence_validator.py", "feat(services): add evidence validation layer"),
    ("backend/services/document_service.py", "feat(services): add document management service"),
    ("backend/services/consistency_engine.py", "feat(services): add consistency analysis engine"),
    ("backend/services/qa_service.py", "feat(services): add grounded qa service"),

    # 53-60: Jobs, API & Entrypoint
    ("backend/jobs/__init__.py", "feat(jobs): add jobs module init"),
    ("backend/jobs/job_manager.py", "feat(jobs): add async job manager"),
    ("backend/jobs/worker.py", "feat(jobs): add background job worker"),
    ("backend/api/__init__.py", "feat(api): add api module init"),
    ("backend/api/documents.py", "feat(api): add document upload routes"),
    ("backend/api/analysis.py", "feat(api): add analysis job routes"),
    ("backend/api/qa.py", "feat(api): add follow-up qa routes"),
    ("backend/main.py", "feat(backend): add fastapi main application entrypoint"),

    # 61-68: Fixtures & Scripts & Docs
    ("fixtures/sample_documents/.gitkeep", "chore: add sample documents placeholder"),
    ("fixtures/sample_documents/msa_acme_techstar.txt", "test(fixtures): add master services agreement fixture"),
    ("fixtures/sample_documents/sow_001_data_platform.txt", "test(fixtures): add statement of work fixture"),
    ("fixtures/sample_documents/amendment_001.txt", "test(fixtures): add agreement amendment fixture"),
    ("docs/ARCHITECTURE.md", "docs: add detailed system architecture documentation"),
    ("docs/BENCHMARKS.md", "docs: add retrieval quality benchmark results"),
    ("scripts/.gitkeep", "chore: add scripts directory placeholder"),
    ("scripts/benchmark.py", "tools: add benchmarking and evaluation script"),

    # 69-97: Frontend
    ("frontend/.gitignore", "chore(frontend): configure frontend gitignore"),
    ("frontend/package.json", "chore(frontend): add package dependencies"),
    ("frontend/package-lock.json", "chore(frontend): add package lock file"),
    ("frontend/tsconfig.json", "chore(frontend): configure tsconfig compiler options"),
    ("frontend/vite.config.ts", "chore(frontend): configure vite build configuration"),
    ("frontend/vercel.json", "chore(frontend): add vercel routing configuration"),
    ("frontend/index.html", "feat(frontend): add html entrypoint"),
    ("frontend/public/favicon.svg", "feat(frontend): add favicon asset"),
    ("frontend/public/icons.svg", "feat(frontend): add svg icon sprite"),
    ("frontend/src/assets/hero.png", "feat(frontend): add hero image asset"),
    ("frontend/src/assets/typescript.svg", "feat(frontend): add typescript logo asset"),
    ("frontend/src/assets/vite.svg", "feat(frontend): add vite logo asset"),
    ("frontend/src/index.css", "feat(frontend): add base styles and theme design tokens"),
    ("frontend/src/style.css", "feat(frontend): add utility styling"),
    ("frontend/src/counter.ts", "feat(frontend): add counter utility helper"),
    ("frontend/src/accessibility/index.ts", "feat(frontend): add screen reader accessibility helpers"),
    ("frontend/src/services/api.ts", "feat(frontend): add api client service"),
    ("frontend/src/components/Disclaimer.tsx", "feat(frontend): add legal safety disclaimer component"),
    ("frontend/src/components/UploadWorkspace.tsx", "feat(frontend): add document upload workspace component"),
    ("frontend/src/components/AnalysisProgress.tsx", "feat(frontend): add job progress visualizer component"),
    ("frontend/src/components/ConsistencyReport.tsx", "feat(frontend): add findings report component"),
    ("frontend/src/components/EvidenceViewer.tsx", "feat(frontend): add evidence detail viewer component"),
    ("frontend/src/components/RelationshipGraph.tsx", "feat(frontend): add document relationship graph component"),
    ("frontend/src/components/QAPanel.tsx", "feat(frontend): add interactive qa panel component"),
    ("frontend/src/components/MetricsPanel.tsx", "feat(frontend): add job performance metrics panel"),
    ("frontend/src/App.tsx", "feat(frontend): add main application flow router"),
    ("frontend/src/main.tsx", "feat(frontend): add application mount entrypoint"),
    ("frontend/src/test-setup.ts", "test(frontend): add vitest test setup configuration"),
    ("frontend/src/App.test.tsx", "test(frontend): add main application component tests"),

    # 98-128: Tests
    ("tests/__init__.py", "test: add tests root package init"),
    ("tests/unit/__init__.py", "test: add unit tests package init"),
    ("tests/unit/test_schemas.py", "test(unit): add schema validation unit tests"),
    ("tests/unit/test_metadata.py", "test(unit): add metadata extraction unit tests"),
    ("tests/unit/test_segmenter.py", "test(unit): add clause segmenter unit tests"),
    ("tests/unit/test_candidate_generator.py", "test(unit): add candidate pair generator unit tests"),
    ("tests/unit/test_scoring.py", "test(unit): add candidate scoring unit tests"),
    ("tests/unit/test_evidence_validator.py", "test(unit): add evidence validator unit tests"),
    ("tests/unit/test_cache_keys.py", "test(unit): add cache key construction unit tests"),
    ("tests/unit/test_logging.py", "test(unit): add structured logging and metrics unit tests"),
    ("tests/unit/test_mock_provider.py", "test(unit): add mock llm provider unit tests"),
    ("tests/unit/test_state_store.py", "test(unit): add local state store unit tests"),
    ("tests/security/__init__.py", "test: add security tests package init"),
    ("tests/security/test_upload_validation.py", "test(security): add upload validation security tests"),
    ("tests/security/test_prompt_injection.py", "test(security): add prompt injection defense tests"),
    ("tests/security/test_sanitization.py", "test(security): add output sanitization security tests"),
    ("tests/security/test_rate_limiting.py", "test(security): add rate limiter security tests"),
    ("tests/security/test_cross_session.py", "test(security): add cross session isolation security tests"),
    ("tests/integration/__init__.py", "test: add integration tests package init"),
    ("tests/integration/test_upload_pipeline.py", "test(integration): add document upload pipeline tests"),
    ("tests/integration/test_provider_factory.py", "test(integration): add provider factory integration tests"),
    ("tests/integration/test_job_manager.py", "test(integration): add job manager integration tests"),
    ("tests/integration/test_qa_grounding_bug.py", "test(integration): add grounding bug regression tests"),
    ("tests/performance/__init__.py", "test: add performance tests package init"),
    ("tests/performance/test_candidate_reduction.py", "test(performance): add candidate reduction performance tests"),
    ("tests/performance/test_cache_behavior.py", "test(performance): add caching behavior performance tests"),
    ("tests/performance/test_concurrency.py", "test(performance): add bounded concurrency tests"),
    ("tests/accessibility/__init__.py", "test: add accessibility tests package init"),
    ("tests/accessibility/test_semantic_html.py", "test(accessibility): add semantic html accessibility tests"),
    ("tests/e2e/__init__.py", "test: add e2e tests package init"),
    ("tests/e2e/test_full_journey.py", "test(e2e): add end-to-end user journey tests"),
]

print(f"Total planned commits: {len(commits)}")

for i, (filepath, msg) in enumerate(commits, 1):
    # Stage single file
    add_res = subprocess.run(["git", "add", "--", filepath], capture_output=True, text=True)
    if add_res.returncode != 0:
        print(f"Error adding {filepath}: {add_res.stderr}")
        sys.exit(1)
    
    # Commit
    commit_res = subprocess.run(["git", "commit", "-m", msg], capture_output=True, text=True)
    if commit_res.returncode != 0:
        print(f"Error committing {filepath}: {commit_res.stderr}")
        sys.exit(1)
    
    print(f"[{i}/{len(commits)}] Created commit: {filepath} -> {msg}")

print("All commits successfully created!")
