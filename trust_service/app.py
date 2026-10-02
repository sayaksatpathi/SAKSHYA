"""
SAKSHYA Independent Trust Authority Service

A SEPARATE service that provides cryptographic signing of evidence
chain heads and Merkle roots.

IMPORTANT: This is a prototype independent trust service.
It is NOT a government certification authority.
It demonstrates the architecture of independent cryptographic
trust anchoring.

The signing secret/key is held ONLY by this service and is
NOT shared with the investigator's application.
"""

import os
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sakshya.trust")

# =============================================================================
# Configuration
# =============================================================================

# The HMAC secret is loaded from environment variables ONLY.
# It must NEVER be committed to source code or shared with the investigator system.
TRUST_HMAC_SECRET = os.environ.get(
    "TRUST_HMAC_SECRET",
    # Default for development/demo ONLY — must be changed in production
    "SAKSHYA_DEMO_TRUST_SECRET_CHANGE_IN_PRODUCTION_2026",
)
TRUST_AUTHORITY_ID = os.environ.get("TRUST_AUTHORITY_ID", "SAKSHYA-TRUST-PROTOTYPE-001")
TRUST_KEY_VERSION = os.environ.get("TRUST_KEY_VERSION", "v1-demo")

# Storage for signed receipts
TRUST_STORAGE_DIR = os.environ.get("TRUST_STORAGE_DIR", "./trust_service/storage")
Path(TRUST_STORAGE_DIR).mkdir(parents=True, exist_ok=True)

# =============================================================================
# Trust Service App
# =============================================================================

app = FastAPI(
    title="SAKSHYA Trust Authority",
    description=(
        "Independent cryptographic trust service for SAKSHYA forensic platform. "
        "This is a PROTOTYPE trust service, not a government certification authority."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Schemas
# =============================================================================

class SignRequest(BaseModel):
    chain_head: str = Field(..., min_length=64, max_length=64, description="SHA-256 chain head hash")
    case_id: str = Field(..., description="Case identifier")
    merkle_root: Optional[str] = Field(None, min_length=64, max_length=64, description="Optional Merkle root hash")


class SignResponse(BaseModel):
    authority_id: str
    chain_head: str
    merkle_root: Optional[str]
    signature: str
    algorithm: str
    key_version: str
    timestamp: str
    receipt_id: str


class VerifyRequest(BaseModel):
    chain_head: str = Field(..., min_length=64, max_length=64)
    signature: str
    case_id: str
    merkle_root: Optional[str] = None
    manifest_hash: Optional[str] = None
    timestamp: str
    authority_key_id: str


class VerifyResponse(BaseModel):
    valid: bool
    authority_id: str
    algorithm: str
    chain_head: str
    detail: Optional[str] = None


# =============================================================================
# Signing Logic
# =============================================================================

def compute_signature(data: str) -> str:
    """
    Compute HMAC-SHA256 signature.

    The HMAC secret is held only by this trust service.
    """
    return hmac.new(
        TRUST_HMAC_SECRET.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_signature(data: str, signature: str) -> bool:
    """Verify an HMAC-SHA256 signature."""
    expected = compute_signature(data)
    return hmac.compare_digest(expected, signature)


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/health")
async def health():
    """Trust service health check."""
    return {
        "status": "operational",
        "authority_id": TRUST_AUTHORITY_ID,
        "key_version": TRUST_KEY_VERSION,
        "algorithm": "HMAC-SHA256",
        "note": "This is a prototype trust service, not a government certification authority.",
    }


@app.post("/trust/sign", response_model=SignResponse)
async def sign_chain_head(request: SignRequest):
    """
    Sign a chain head hash with the trust authority's secret.

    The signature provides an independent trust anchor:
    the investigator's system cannot forge this signature
    without the trust authority's secret.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    manifest_hash = request.manifest_hash if hasattr(request, "manifest_hash") else None

    # Build the canonical data structure to sign
    canonical_payload = {
        "algorithm": "HMAC-SHA256",
        "authority_key_id": TRUST_KEY_VERSION,
        "case_id": request.case_id,
        "chain_head": request.chain_head,
        "manifest_hash": manifest_hash,
        "merkle_root": request.merkle_root,
        "timestamp": timestamp,
    }
    # Sort keys for determinism (canonicalization)
    sign_data = json.dumps(canonical_payload, separators=(",", ":"), sort_keys=True)
    
    signature = compute_signature(sign_data)

    receipt_id = hashlib.sha256(
        f"{request.case_id}:{timestamp}:{signature[:16]}".encode()
    ).hexdigest()[:24]

    # Store the receipt
    receipt = {
        "receipt_id": receipt_id,
        "authority_id": TRUST_AUTHORITY_ID,
        "case_id": request.case_id,
        "chain_head": request.chain_head,
        "merkle_root": request.merkle_root,
        "signature": signature,
        "algorithm": "HMAC-SHA256",
        "key_version": TRUST_KEY_VERSION,
        "timestamp": timestamp,
    }

    receipt_path = Path(TRUST_STORAGE_DIR) / f"receipt_{receipt_id}.json"
    with open(receipt_path, "w") as f:
        json.dump(receipt, f, indent=2)

    logger.info(
        "Chain head signed: case=%s, receipt=%s",
        request.case_id, receipt_id,
    )

    return SignResponse(
        authority_id=TRUST_AUTHORITY_ID,
        chain_head=request.chain_head,
        merkle_root=request.merkle_root,
        signature=signature,
        algorithm="HMAC-SHA256",
        key_version=TRUST_KEY_VERSION,
        timestamp=timestamp,
        receipt_id=receipt_id,
    )


@app.post("/trust/verify", response_model=VerifyResponse)
async def verify_chain_signature(request: VerifyRequest):
    """
    Verify a previously issued trust signature.

    Returns whether the signature is valid for the given chain head.
    """
    canonical_payload = {
        "algorithm": "HMAC-SHA256",
        "authority_key_id": request.authority_key_id,
        "case_id": request.case_id,
        "chain_head": request.chain_head,
        "manifest_hash": request.manifest_hash,
        "merkle_root": request.merkle_root,
        "timestamp": request.timestamp,
    }
    # Sort keys for determinism (canonicalization)
    sign_data = json.dumps(canonical_payload, separators=(",", ":"), sort_keys=True)
    
    is_valid = verify_signature(sign_data, request.signature)

    if is_valid:
        detail = "SIGNATURE VERIFIED — chain head matches trust authority signature"
    else:
        detail = "SIGNATURE INVALID — chain head does not match the provided signature"

    logger.info(
        "Signature verification: valid=%s, chain_head=%s...",
        is_valid, request.chain_head[:16],
    )

    return VerifyResponse(
        valid=is_valid,
        authority_id=TRUST_AUTHORITY_ID,
        algorithm="HMAC-SHA256",
        chain_head=request.chain_head,
        detail=detail,
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("TRUST_SERVICE_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
