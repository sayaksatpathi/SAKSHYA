"""
SAKSHYA Tests — Cryptographic Integrity

Tests for SHA-256, canonicalization, chain verification,
Merkle tree, and trust signatures.
"""

import hashlib
import json
import pytest

from backend.crypto.hashing import (
    sha256_bytes, sha256_string, sha256_file,
    canonicalize_json, hash_event,
)
from backend.crypto.merkle import MerkleTree, build_merkle_root


# =============================================================================
# SHA-256 Tests
# =============================================================================

class TestSHA256:
    """SHA-256 hashing correctness tests."""

    def test_sha256_bytes_known_value(self):
        """Test SHA-256 of known input produces expected output."""
        data = b"SAKSHYA Evidence Platform"
        expected = hashlib.sha256(data).hexdigest()
        assert sha256_bytes(data) == expected

    def test_sha256_empty_bytes(self):
        """Test SHA-256 of empty bytes."""
        expected = hashlib.sha256(b"").hexdigest()
        assert sha256_bytes(b"") == expected

    def test_sha256_string(self):
        """Test SHA-256 of string input."""
        data = "test evidence hash"
        expected = hashlib.sha256(data.encode("utf-8")).hexdigest()
        assert sha256_string(data) == expected

    def test_sha256_file(self, tmp_path):
        """Test SHA-256 of a file."""
        test_file = tmp_path / "test.bin"
        content = b"evidence file content for hashing"
        test_file.write_bytes(content)

        expected = hashlib.sha256(content).hexdigest()
        assert sha256_file(test_file) == expected

    def test_sha256_large_file(self, tmp_path):
        """Test SHA-256 of a large file (read in chunks)."""
        test_file = tmp_path / "large.bin"
        # 100KB of data
        content = b"x" * 100_000
        test_file.write_bytes(content)

        expected = hashlib.sha256(content).hexdigest()
        assert sha256_file(test_file) == expected

    def test_sha256_deterministic(self):
        """Same input always produces the same hash."""
        data = b"deterministic test"
        h1 = sha256_bytes(data)
        h2 = sha256_bytes(data)
        assert h1 == h2

    def test_sha256_different_inputs(self):
        """Different inputs produce different hashes."""
        h1 = sha256_bytes(b"evidence A")
        h2 = sha256_bytes(b"evidence B")
        assert h1 != h2


# =============================================================================
# Canonicalization Tests
# =============================================================================

class TestCanonicalization:
    """JSON canonicalization tests."""

    def test_canonical_sorts_keys(self):
        """Keys must be sorted in canonical JSON."""
        data = {"z": 1, "a": 2, "m": 3}
        result = canonicalize_json(data)
        assert result == '{"a":2,"m":3,"z":1}'

    def test_canonical_no_whitespace(self):
        """Canonical JSON has no extra whitespace."""
        data = {"key": "value"}
        result = canonicalize_json(data)
        assert " " not in result.replace('"', "").replace(":", "").replace(",", "")

    def test_canonical_deterministic(self):
        """Same data always produces the same canonical form."""
        data = {"event": "INGESTED", "case": "001", "hash": "abc123"}
        r1 = canonicalize_json(data)
        r2 = canonicalize_json(data)
        assert r1 == r2

    def test_canonical_different_key_order(self):
        """Different key insertion order produces the same result."""
        d1 = {"b": 1, "a": 2}
        d2 = {"a": 2, "b": 1}
        assert canonicalize_json(d1) == canonicalize_json(d2)


# =============================================================================
# Event Hash Tests
# =============================================================================

class TestEventHash:
    """Chain event hashing tests."""

    def test_event_hash_deterministic(self):
        """Same event data always produces the same hash."""
        event = {
            "case_id": "case-001",
            "event_type": "EVIDENCE_INGESTED",
            "actor": "investigator",
            "timestamp": "2026-01-01T00:00:00",
            "previous_hash": "0" * 64,
        }
        h1 = hash_event(event)
        h2 = hash_event(event)
        assert h1 == h2

    def test_event_hash_changes_with_data(self):
        """Changing event data changes the hash."""
        base = {
            "case_id": "case-001",
            "event_type": "EVIDENCE_INGESTED",
            "actor": "investigator",
            "timestamp": "2026-01-01T00:00:00",
            "previous_hash": "0" * 64,
        }
        modified = {**base, "actor": "different_investigator"}
        assert hash_event(base) != hash_event(modified)

    def test_event_hash_is_sha256(self):
        """Event hash should be a valid SHA-256 hex string."""
        event = {"test": "data"}
        h = hash_event(event)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


# =============================================================================
# Merkle Tree Tests
# =============================================================================

class TestMerkleTree:
    """Merkle tree construction and verification tests."""

    def test_single_leaf(self):
        """Tree with one leaf: root equals the leaf itself (no merging needed)."""
        leaf = sha256_string("evidence1")
        tree = MerkleTree([leaf])
        assert tree.root == leaf
        assert tree.leaf_count == 1

    def test_two_leaves(self):
        """Tree with two leaves."""
        a = sha256_string("evidence1")
        b = sha256_string("evidence2")
        tree = MerkleTree([a, b])
        expected_root = sha256_string(a + b)
        assert tree.root == expected_root

    def test_four_leaves(self):
        """Tree with four leaves (balanced)."""
        leaves = [sha256_string(f"evidence{i}") for i in range(4)]
        tree = MerkleTree(leaves)
        ab = sha256_string(leaves[0] + leaves[1])
        cd = sha256_string(leaves[2] + leaves[3])
        expected_root = sha256_string(ab + cd)
        assert tree.root == expected_root

    def test_odd_leaves_duplicate(self):
        """Tree with odd leaves duplicates the last leaf."""
        leaves = [sha256_string(f"e{i}") for i in range(3)]
        tree = MerkleTree(leaves)
        ab = sha256_string(leaves[0] + leaves[1])
        cc = sha256_string(leaves[2] + leaves[2])
        expected_root = sha256_string(ab + cc)
        assert tree.root == expected_root

    def test_empty_leaves_raises(self):
        """Empty leaf list should raise ValueError."""
        with pytest.raises(ValueError, match="zero leaves"):
            MerkleTree([])

    def test_proof_valid(self):
        """Merkle proof should verify correctly."""
        leaves = [sha256_string(f"evidence{i}") for i in range(4)]
        tree = MerkleTree(leaves)

        for i in range(len(leaves)):
            proof = tree.get_proof(i)
            assert MerkleTree.verify_proof(leaves[i], proof, tree.root)

    def test_proof_invalid_leaf(self):
        """Proof should fail for a tampered leaf."""
        leaves = [sha256_string(f"evidence{i}") for i in range(4)]
        tree = MerkleTree(leaves)
        proof = tree.get_proof(0)

        tampered_leaf = sha256_string("tampered")
        assert not MerkleTree.verify_proof(tampered_leaf, proof, tree.root)

    def test_proof_invalid_root(self):
        """Proof should fail against a wrong root."""
        leaves = [sha256_string(f"evidence{i}") for i in range(4)]
        tree = MerkleTree(leaves)
        proof = tree.get_proof(0)

        wrong_root = sha256_string("wrong_root")
        assert not MerkleTree.verify_proof(leaves[0], proof, wrong_root)

    def test_build_merkle_root_convenience(self):
        """build_merkle_root convenience function should work."""
        leaves = [sha256_string(f"e{i}") for i in range(5)]
        root = build_merkle_root(leaves)
        tree = MerkleTree(leaves)
        assert root == tree.root

    def test_deterministic_root(self):
        """Same leaves always produce the same root."""
        leaves = [sha256_string(f"e{i}") for i in range(3)]
        r1 = build_merkle_root(leaves)
        r2 = build_merkle_root(leaves)
        assert r1 == r2

    def test_leaf_order_matters(self):
        """Different leaf order produces different root."""
        a = sha256_string("a")
        b = sha256_string("b")
        r1 = build_merkle_root([a, b])
        r2 = build_merkle_root([b, a])
        assert r1 != r2


# =============================================================================
# Tamper Detection Tests (Security)
# =============================================================================

class TestTamperDetection:
    """Tests that verify tamper detection works correctly."""

    def test_tampered_evidence_file(self, tmp_path):
        """Modifying evidence file after hashing must be detected."""
        evidence_file = tmp_path / "evidence.mp4"
        evidence_file.write_bytes(b"original evidence content")

        original_hash = sha256_file(evidence_file)

        # Tamper with the file
        evidence_file.write_bytes(b"tampered evidence content")

        new_hash = sha256_file(evidence_file)

        assert original_hash != new_hash, "INTEGRITY FAILURE must be detectable"

    def test_tampered_merkle_leaf(self):
        """Modifying a Merkle leaf must be detected."""
        leaves = [sha256_string(f"evidence{i}") for i in range(4)]
        tree = MerkleTree(leaves)
        original_root = tree.root

        # Tamper with a leaf
        tampered_leaves = list(leaves)
        tampered_leaves[2] = sha256_string("tampered_evidence")
        tampered_tree = MerkleTree(tampered_leaves)

        assert original_root != tampered_tree.root, "MERKLE VERIFICATION must detect changes"

    def test_tampered_event_in_chain(self):
        """Modifying a chain event's hash should be detectable."""
        event1 = {
            "case_id": "case-001",
            "event_type": "EVIDENCE_INGESTED",
            "previous_hash": "0" * 64,
        }
        event1_hash = hash_event(event1)

        event2 = {
            "case_id": "case-001",
            "event_type": "ANALYSIS_COMPLETED",
            "previous_hash": event1_hash,
        }
        event2_hash = hash_event(event2)

        # Tamper with event1
        tampered_event1 = {**event1, "event_type": "FORGED_EVENT"}
        tampered_hash = hash_event(tampered_event1)

        # The chain is broken because event2's previous_hash
        # no longer matches
        assert tampered_hash != event1_hash
        assert event2["previous_hash"] != tampered_hash
