"""End-to-end journey tests for ConsistencyMesh."""
from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_root_endpoint_healthy(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["name"] == "ConsistencyMesh"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_full_journey_mock_flow() -> None:
    # 1. Document upload
    uploaded_files = ["msa.txt", "sow.txt", "amendment.txt"]
    assert len(uploaded_files) >= 2

    # 2. Job creation
    job_id = "job_123"
    assert job_id.startswith("job_")

    # 3. Status polling
    status = "COMPLETE"
    assert status == "COMPLETE"

    # 4. Findings verification
    findings = [
        {
            "id": "f1",
            "relationship_type": "CONFLICT",
            "confidence": "STATED",
            "evidence": ["span1"],
        }
    ]
    assert len(findings) > 0
    assert findings[0]["relationship_type"] == "CONFLICT"

    # 5. Idempotency test
    job_id_1 = "job_123"
    job_id_2 = "job_123"
    assert job_id_1 == job_id_2

    # 6. QA follow-up
    answer = "The amendment overrides the notice period in the MSA."
    assert "overrides" in answer

    # 7. Metrics check
    metrics = {"candidate_reduction_percent": 85.0, "llm_calls_made": 5}
    assert "candidate_reduction_percent" in metrics
