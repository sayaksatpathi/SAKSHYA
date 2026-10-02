"""
SAKSHYA Trust Service Client

Communicates with the independent trust authority to obtain
signed receipts for chain heads and Merkle roots.

The trust service is intentionally separate from the main application
to provide an independent trust anchor.
"""

import logging
from typing import Optional
import httpx

from backend.config import settings

logger = logging.getLogger(__name__)


class TrustClient:
    """
    Client for the independent SAKSHYA Trust Authority.

    WARNING: This prototype trust service is NOT a government
    certification authority. It is a demonstration of the
    independent trust-sealing architecture.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.trust_service_url).rstrip("/")

    async def sign(self, chain_head: str, case_id: str, merkle_root: Optional[str] = None) -> dict:
        """
        Request a trust signature from the authority.

        Args:
            chain_head: The chain head hash to sign.
            case_id: Case identifier.
            merkle_root: Optional Merkle root to include.

        Returns:
            Trust receipt dictionary.

        Raises:
            TrustServiceUnavailable: If the trust service cannot be reached.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/trust/sign",
                    json={
                        "chain_head": chain_head,
                        "case_id": case_id,
                        "merkle_root": merkle_root,
                    },
                )
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError:
            logger.warning("Trust service unavailable at %s", self.base_url)
            raise TrustServiceUnavailable(
                f"Trust service unavailable at {self.base_url}. "
                f"Core forensic functions continue operating. "
                f"TRUST SEAL: NOT AVAILABLE"
            )
        except httpx.HTTPStatusError as e:
            logger.error("Trust service error: %s", e.response.text)
            raise TrustServiceError(f"Trust service returned error: {e.response.status_code}")
        except Exception as e:
            logger.error("Trust service communication error: %s", e)
            raise TrustServiceUnavailable(f"Trust service error: {e}")

    async def verify(self, chain_head: str, signature: str, case_id: str, timestamp: str, authority_key_id: str, merkle_root: Optional[str] = None, manifest_hash: Optional[str] = None) -> dict:
        """
        Verify a trust signature.

        Args:
            chain_head: The original chain head that was signed.
            signature: The signature to verify.
            case_id: The case ID.
            timestamp: The timestamp from the receipt.
            authority_key_id: The authority key version from the receipt.
            merkle_root: Optional Merkle root from the receipt.
            manifest_hash: Optional manifest hash from the receipt.

        Returns:
            Verification result dictionary.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/trust/verify",
                    json={
                        "chain_head": chain_head,
                        "signature": signature,
                        "case_id": case_id,
                        "timestamp": timestamp,
                        "authority_key_id": authority_key_id,
                        "merkle_root": merkle_root,
                        "manifest_hash": manifest_hash,
                    },
                )
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError:
            logger.warning("Trust service unavailable at %s", self.base_url)
            raise TrustServiceUnavailable(
                f"Trust service unavailable. TRUST SEAL: NOT AVAILABLE"
            )
        except Exception as e:
            logger.error("Trust verification error: %s", e)
            raise TrustServiceUnavailable(f"Trust service error: {e}")

    async def health(self) -> dict:
        """Check trust service health."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return response.json()
        except Exception:
            return {"status": "unavailable"}


class TrustServiceUnavailable(Exception):
    """Raised when the trust service cannot be reached."""
    pass


class TrustServiceError(Exception):
    """Raised when the trust service returns an error."""
    pass
