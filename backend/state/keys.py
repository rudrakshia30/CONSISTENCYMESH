from __future__ import annotations

import hashlib


def content_hash(data: bytes) -> str:
    """
    Compute the SHA-256 hex digest of the given binary content.

    Args:
        data: The binary data to hash.

    Returns:
        The SHA-256 hexadecimal digest string.
    """
    return hashlib.sha256(data).hexdigest()


def build_cache_key(
    content_hash_str: str,
    prompt_version: str,
    model_config: str,
    prefix: str = 'result'
) -> str:
    """
    Construct a deterministic, safe cache key from input parameters.

    Uses SHA-256 to ensure the resulting key does not contain raw user-supplied
    strings and is of uniform length.

    Args:
        content_hash_str: The hash of the input content.
        prompt_version: The version string of the prompt used.
        model_config: A string representation of the model configuration.
        prefix: An optional prefix to distinguish different types of cache entries.

    Returns:
        A SHA-256 based cache key string.
    """
    raw_key = f"{prefix}:{content_hash_str}:{prompt_version}:{model_config}".encode()
    return f"{prefix}_{hashlib.sha256(raw_key).hexdigest()}"


def build_job_id(document_hashes: list[str], prompt_version: str) -> str:
    """
    Create a deterministic job ID from sorted document content hashes and prompt version.

    Args:
        document_hashes: A list of content hashes for the documents in the job.
        prompt_version: The version string of the prompt used.

    Returns:
        A deterministic, SHA-256 based job ID string.
    """
    sorted_hashes = sorted(document_hashes)
    combined_str = ":".join(sorted_hashes) + f":{prompt_version}"
    return f"job_{hashlib.sha256(combined_str.encode('utf-8')).hexdigest()}"
