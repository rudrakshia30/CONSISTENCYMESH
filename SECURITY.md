# Security

## Threat Model
ConsistencyMesh assumes the following primary threats in its deployment environment:
- **Malicious file uploads**: Uploads containing executables, zip bombs, or oversized files intended to cause denial of service or remote code execution.
- **Prompt injection**: Malicious instructions embedded within document content to subvert the AI model's intended behavior.
- **Cache poisoning**: Crafted inputs designed to pollute the cache with incorrect or malicious results.
- **Cross-session data leakage**: Unauthorized access to another user's session or analysis data.
- **XSS (Cross-Site Scripting)**: Malicious scripts embedded via LLM-generated output or document extraction.
- **API abuse**: Excessive API requests attempting to evade rate limits or cause DoS.
- **Secret exposure**: Accidental logging of API keys or sensitive credentials.

## Controls
For each threat in the model, we have implemented specific controls:

1. **Upload Validation**: File signatures (magic bytes) and sizes are strictly verified. Zip bomb protections are in place.
   - *Implementation*: `backend/security/validation.py`
   - *Tests*: `tests/security/test_upload_validation.py`

2. **Prompt Injection Defense**: A nonce-based prompt isolation technique is used alongside robust delimiter framing to separate instructions from content.
   - *Implementation*: `backend/security/prompt_guard.py`
   - *Tests*: `tests/security/test_prompt_injection.py`

3. **Cache Key Security**: Cache keys are generated using SHA-256 hashes of the file content, model configuration, and prompt versions, rendering cache poisoning computationally infeasible.
   - *Implementation*: `backend/state/keys.py`
   - *Tests*: `tests/unit/test_cache_keys.py`

4. **Cross-Session Isolation**: Data is partitioned by session/job IDs. The `JobManager` and `DocumentService` strictly enforce these boundaries.
   - *Implementation*: Enforced in JobManager and DocumentService
   - *Tests*: `tests/security/test_cross_session.py`

5. **Output Sanitization**: All AI-generated output is sanitized before being returned to the client to prevent XSS.
   - *Implementation*: `backend/security/sanitize.py`
   - *Tests*: `tests/security/test_sanitization.py`

6. **Rate Limiting**: API endpoints are protected using token bucket or similar rate limiting strategies to prevent abuse.
   - *Implementation*: `backend/security/rate_limit.py`
   - *Tests*: `tests/security/test_rate_limiting.py`

7. **Secret Management**: All secrets are managed via `pydantic-settings` environment variables. A `SecretSafeFormatter` ensures logs never expose these values.

8. **Safe Error Handling**: Generic error messages are sent to clients while full stack traces and context are logged server-side.
   - *Implementation*: `backend/core/errors.py`

9. **Path Traversal**: File storage uses content-hash keys rather than user-provided filenames, and `sanitize_filename` is used when filenames are required.

10. **Adversarial Test Documents**: Our test suite includes fixture documents containing prompt injection attempts to continuously verify defenses.
    - *Tests*: `test_prompt_injection.py`

## Responsible AI
ConsistencyMesh enforces responsible AI practices:
- **Legal-safety language discipline**: The system is tuned to avoid using deterministic legal language where human review is required.
- **No adjudicative language**: The AI does not make final legal judgments or adjudicate disputes.
- **Mandatory disclaimer**: A disclaimer is prominently displayed in the UI and documented in the README, stating that the tool assists but does not replace professional legal review.
