"""
SAKSHYA Cryptographic Utilities

Core hashing and canonicalization functions used throughout the
evidence integrity pipeline.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, BinaryIO


def sha256_file(file_path: str | Path, chunk_size: int = 8192) -> str:
    """
    Compute SHA-256 hash of a file.

    Reads the file in chunks to handle large evidence files without
    loading them entirely into memory.

    Args:
        file_path: Path to the file to hash.
        chunk_size: Read buffer size in bytes.

    Returns:
        Hex-encoded SHA-256 digest.
    """
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def sha256_stream(stream: BinaryIO, chunk_size: int = 8192) -> str:
    """Compute SHA-256 hash from a file-like stream."""
    hasher = hashlib.sha256()
    while True:
        chunk = stream.read(chunk_size)
        if not chunk:
            break
        hasher.update(chunk)
    return hasher.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 hash of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_string(data: str) -> str:
    """Compute SHA-256 hash of a UTF-8 string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def canonicalize_json(data: dict[str, Any]) -> str:
    """
    Produce a canonical JSON string for deterministic hashing.

    Keys are sorted, no extra whitespace, ASCII-escaped.
    This ensures the same logical data always produces the same hash.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def hash_event(event_data: dict[str, Any]) -> str:
    """
    Compute the SHA-256 hash of a chain event's canonical JSON.

    Args:
        event_data: Dictionary of event fields (excluding event_hash).

    Returns:
        Hex-encoded SHA-256 digest.
    """
    canonical = canonicalize_json(event_data)
    return sha256_string(canonical)
