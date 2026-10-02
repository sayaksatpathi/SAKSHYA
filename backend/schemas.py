"""
SAKSHYA API Schemas (Pydantic Models)

Defines request/response models for the REST API.
"""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field

# =============================================================================
# Auth Schemas
# =============================================================================

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "investigator"

class UserResponse(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}


# =============================================================================
# Case
# =============================================================================

class CaseCreate(BaseModel):
    case_number: str = Field(..., min_length=1, max_length=50, description="Unique case number")
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    investigator: str = Field(..., min_length=1, max_length=255)
    investigator_id: Optional[str] = None


class CaseResponse(BaseModel):
    id: str
    case_number: str
    title: str
    description: Optional[str]
    investigator: str
    investigator_id: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    evidence_count: int = 0

    model_config = {"from_attributes": True}


class CaseListResponse(BaseModel):
    cases: list["CaseResponse"]
    total: int


# =============================================================================
# Evidence
# =============================================================================

class EvidenceResponse(BaseModel):
    id: str
    case_id: str
    filename: str
    original_filename: str
    source_device: Optional[str]
    source_vendor: Optional[str]
    evidence_type: str
    acquisition_method: str
    size: int
    sha256: str
    mime_type: Optional[str]
    acquired_at: datetime
    acquired_by: Optional[str]
    meta_data: Optional[dict[str, Any]]
    status: str
    codec: Optional[str]
    resolution: Optional[str]
    fps: Optional[float]
    duration: Optional[float]
    has_audio: Optional[bool]
    container_format: Optional[str]
    segment_count: int = 0
    ai_result_count: int = 0

    model_config = {"from_attributes": True}


class EvidenceListResponse(BaseModel):
    evidence: list[EvidenceResponse]
    total: int


# =============================================================================
# Evidence Segment
# =============================================================================

class SegmentResponse(BaseModel):
    id: str
    evidence_id: str
    start_time: Optional[float]
    end_time: Optional[float]
    file_path: str
    sha256: str
    size: Optional[int]
    recovery_method: str
    source_offset: Optional[int]
    confidence: Optional[float]
    validation_status: str
    meta_data: Optional[dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# AI Result
# =============================================================================

class AIResultResponse(BaseModel):
    id: str
    evidence_id: str
    frame_number: Optional[int]
    timestamp: Optional[float]
    detection_type: str
    label: Optional[str]
    confidence: float
    bounding_box: Optional[list[float]]
    track_id: Optional[str]
    model_name: Optional[str]
    model_version: Optional[str]
    meta_data: Optional[dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


class AIResultListResponse(BaseModel):
    results: list[AIResultResponse]
    total: int
    mode: Optional[str] = None  # "real" | "demo" | None


# =============================================================================
# Forensic Finding
# =============================================================================

class ForensicFindingResponse(BaseModel):
    id: str
    evidence_id: str
    type: str
    frame_start: Optional[int]
    frame_end: Optional[int]
    timestamp_start: Optional[float]
    timestamp_end: Optional[float]
    severity: str
    description: str
    method: str
    parameters: Optional[dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# Chain of Custody
# =============================================================================

class ChainEventResponse(BaseModel):
    id: str
    case_id: str
    evidence_id: Optional[str]
    sequence_number: int
    event_type: str
    actor: str
    timestamp: datetime
    payload_hash: Optional[str]
    previous_hash: str
    event_hash: str
    meta_data: Optional[dict[str, Any]]

    model_config = {"from_attributes": True}


class ChainVerifyResponse(BaseModel):
    valid: bool
    total_events: int
    verified_events: int
    first_failure: Optional[int] = None
    failure_detail: Optional[str] = None


# =============================================================================
# Merkle Tree
# =============================================================================

class MerkleResponse(BaseModel):
    id: str
    case_id: str
    root_hash: str
    leaf_count: int
    algorithm: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MerkleProofResponse(BaseModel):
    leaf_hash: str
    root_hash: str
    proof: list[dict[str, str]]  # [{"position": "left"|"right", "hash": "..."}]
    valid: bool


class MerkleVerifyResponse(BaseModel):
    valid: bool
    computed_root: str
    stored_root: str
    leaf_count: int


# =============================================================================
# Trust
# =============================================================================

class TrustSignRequest(BaseModel):
    chain_head: str = Field(..., min_length=64, max_length=64)
    merkle_root: Optional[str] = Field(None, min_length=64, max_length=64)
    case_id: str


class TrustReceiptResponse(BaseModel):
    id: str
    case_id: str
    chain_head: str
    merkle_root: Optional[str]
    signature: str
    algorithm: str
    authority_id: str
    key_version: Optional[str]
    timestamp: datetime
    verification_status: Optional[str]

    model_config = {"from_attributes": True}


class TrustVerifyResponse(BaseModel):
    valid: bool
    authority_id: str
    algorithm: str
    chain_head: str
    signature: str
    detail: Optional[str] = None


# =============================================================================
# Job
# =============================================================================

class JobResponse(BaseModel):
    id: str
    case_id: Optional[str]
    evidence_id: Optional[str]
    job_type: str
    status: str
    progress: Optional[float]
    result: Optional[dict[str, Any]]
    error: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# Timeline
# =============================================================================

class TimelineEvent(BaseModel):
    timestamp: float  # seconds into video, or epoch
    event_type: str
    label: str
    confidence: Optional[float] = None
    camera: Optional[str] = None
    frame_number: Optional[int] = None
    bounding_box: Optional[list[float]] = None

class CaseTimelineEvent(BaseModel):
    id: str
    timestamp: datetime
    type: str
    title: str
    description: str
    case_id: str
    evidence_id: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    hash: str

class CaseTimelineResponse(BaseModel):
    events: list[CaseTimelineEvent]
    total: int

    evidence_id: Optional[str] = None
    meta_data: Optional[dict[str, Any]] = None


class TimelineResponse(BaseModel):
    events: list[TimelineEvent]
    total: int


# =============================================================================
# Health
# =============================================================================

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    trust_service: str
    models_available: dict[str, bool]


# =============================================================================
# Error
# =============================================================================

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None


# =============================================================================
# Electronic Record Certificate (BSA §63(4))
# =============================================================================

class ElectronicRecordCertificateCreate(BaseModel):
    evidence_id: str
    electronic_record_identifier: str
    electronic_record_description: Optional[str] = None
    source_device_id: Optional[str] = "NOT PROVIDED"
    source_device_type: Optional[str] = "NOT PROVIDED"
    source_device_description: Optional[str] = "NOT PROVIDED"
    method_of_production: Optional[str] = "NOT RECORDED"
    device_operational_status: Optional[str] = "NOT VERIFIED"
    regular_use_context: Optional[str] = "NOT RECORDED"
    information_fed_in_ordinary_course: Optional[str] = "NOT RECORDED"
    derivation_relationship: Optional[str] = "NOT APPLICABLE"
    signatory_name: Optional[str] = "NOT PROVIDED"
    signatory_role: Optional[str] = "NOT PROVIDED"
    signatory_organization: Optional[str] = "NOT PROVIDED"
    signatory_address: Optional[str] = "NOT PROVIDED"
    signatory_contact: Optional[str] = "NOT PROVIDED"

class ElectronicRecordCertificateResponse(BaseModel):
    id: str
    certificate_id: str
    case_id: str
    evidence_id: str
    electronic_record_identifier: str
    electronic_record_description: Optional[str]
    record_format: str
    record_size: int
    record_sha256: str
    source_device_id: Optional[str]
    source_device_type: Optional[str]
    source_device_description: Optional[str]
    software_used: Optional[str]
    software_version: Optional[str]
    date_of_acquisition: Optional[datetime]
    date_of_generation: datetime
    method_of_production: Optional[str]
    device_operational_status: Optional[str]
    regular_use_context: Optional[str]
    information_fed_in_ordinary_course: Optional[str]
    derivation_relationship: Optional[str]
    analysis_id: Optional[str]
    certificate_status: str
    signatory_name: Optional[str]
    signatory_role: Optional[str]
    signatory_organization: Optional[str]
    signatory_address: Optional[str]
    signatory_contact: Optional[str]
    signature_status: str
    signature_method: Optional[str]
    certificate_content_hash: Optional[str]
    certificate_pdf_sha256: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

class CertificateVerifyResponse(BaseModel):
    certificate_exists: bool
    certificate_content_hash_valid: bool
    evidence_hash_matches: bool
    analysis_hash_matches: bool
    merkle_root_matches: bool
    trust_reference_valid: bool
    report_hash_matches: bool
    signature_status: str
    overall_integrity_status: str

