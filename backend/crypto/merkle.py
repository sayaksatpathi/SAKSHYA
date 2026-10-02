"""
SAKSHYA Merkle Tree Implementation

Provides efficient integrity verification for grouped evidence hashes.
Used to create a single root hash representing all evidence in a case.
"""

from backend.crypto.hashing import sha256_string


class MerkleTree:
    """
    A binary Merkle tree built from leaf hashes.

    Each leaf is a SHA-256 hash (e.g., of evidence or chain events).
    Internal nodes are SHA-256(left_child || right_child).
    If the number of leaves is odd, the last leaf is duplicated.
    """

    def __init__(self, leaves: list[str]):
        """
        Build a Merkle tree from an ordered list of leaf hashes.

        Args:
            leaves: List of hex-encoded SHA-256 hashes.

        Raises:
            ValueError: If no leaves are provided.
        """
        if not leaves:
            raise ValueError("Cannot build Merkle tree with zero leaves")

        self._leaves = list(leaves)
        self._tree: list[list[str]] = []
        self._build()

    @property
    def root(self) -> str:
        """The Merkle root hash."""
        return self._tree[-1][0]

    @property
    def leaf_count(self) -> int:
        """Number of leaves."""
        return len(self._leaves)

    @property
    def leaves(self) -> list[str]:
        """Ordered list of leaf hashes."""
        return list(self._leaves)

    def _build(self) -> None:
        """Construct the tree bottom-up."""
        current_level = list(self._leaves)
        self._tree = [current_level]

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                # Duplicate last leaf if odd count
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                parent = sha256_string(left + right)
                next_level.append(parent)
            self._tree.append(next_level)
            current_level = next_level

    def get_proof(self, leaf_index: int) -> list[dict[str, str]]:
        """
        Generate a Merkle proof for the leaf at the given index.

        Args:
            leaf_index: Zero-based index into the original leaf list.

        Returns:
            List of proof steps, each with 'position' ('left' or 'right')
            and 'hash'.

        Raises:
            IndexError: If leaf_index is out of range.
        """
        if leaf_index < 0 or leaf_index >= len(self._leaves):
            raise IndexError(f"Leaf index {leaf_index} out of range [0, {len(self._leaves)})")

        proof = []
        idx = leaf_index

        for level in self._tree[:-1]:  # skip root level
            if idx % 2 == 0:
                # sibling is on the right
                sibling_idx = idx + 1
                if sibling_idx < len(level):
                    proof.append({"position": "right", "hash": level[sibling_idx]})
                else:
                    # odd count — sibling is self (duplicated)
                    proof.append({"position": "right", "hash": level[idx]})
            else:
                # sibling is on the left
                proof.append({"position": "left", "hash": level[idx - 1]})
            idx //= 2

        return proof

    @staticmethod
    def verify_proof(leaf_hash: str, proof: list[dict[str, str]], expected_root: str) -> bool:
        """
        Verify a Merkle proof.

        Args:
            leaf_hash: The hash of the leaf to verify.
            proof: The proof path from get_proof().
            expected_root: The expected Merkle root.

        Returns:
            True if the proof is valid.
        """
        current = leaf_hash
        for step in proof:
            if step["position"] == "right":
                current = sha256_string(current + step["hash"])
            else:
                current = sha256_string(step["hash"] + current)
        return current == expected_root


def build_merkle_root(hashes: list[str]) -> str:
    """
    Convenience function: build a tree and return just the root.

    Args:
        hashes: List of hex-encoded SHA-256 leaf hashes.

    Returns:
        The Merkle root hash.
    """
    tree = MerkleTree(hashes)
    return tree.root
