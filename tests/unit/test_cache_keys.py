"""Unit tests for cache key construction and hashing."""
from __future__ import annotations

import pytest

from backend.state.keys import build_cache_key, build_job_id, content_hash


@pytest.mark.unit
def test_content_hash_deterministic() -> None:
    data = b"sample text content"
    h1 = content_hash(data)
    h2 = content_hash(data)
    assert isinstance(h1, str)
    assert len(h1) == 64
    assert h1 == h2


@pytest.mark.unit
def test_same_content_same_hash() -> None:
    data1 = b"identical content"
    data2 = b"identical content"
    assert content_hash(data1) == content_hash(data2)


@pytest.mark.unit
def test_different_content_different_hash() -> None:
    data1 = b"content A"
    data2 = b"content B"
    assert content_hash(data1) != content_hash(data2)


@pytest.mark.unit
def test_build_cache_key() -> None:
    c_hash = content_hash(b"test")
    key = build_cache_key(c_hash, "v1.0", "gemini-2.0-flash")
    assert isinstance(key, str)
    assert key.startswith("result_")
    assert len(key) == 7 + 64


@pytest.mark.unit
def test_build_job_id_deterministic_sorted() -> None:
    doc_hashes = ["hash_b", "hash_a"]
    job_id1 = build_job_id(doc_hashes, "v1.0")
    job_id2 = build_job_id(reversed(doc_hashes), "v1.0")
    assert job_id1 == job_id2


@pytest.mark.unit
def test_build_job_id_different_docs() -> None:
    job_id1 = build_job_id(["hash_a", "hash_b"], "v1.0")
    job_id2 = build_job_id(["hash_a", "hash_c"], "v1.0")
    assert job_id1 != job_id2
