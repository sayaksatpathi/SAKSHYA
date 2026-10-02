"""
SAKSHYA Database Models

Complete relational schema for forensic evidence management, chain of custody,
AI results, and cryptographic integrity verification.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, Boolean,
    ForeignKey, Index, JSON, BigInteger,
)
from sqlalchemy.orm import relationship
from backend.database import Base


def _uuid() -> str:
    """Generate a UUID4 string for primary keys."""
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    """Current UTC timestamp."""
    return datetime.now(timezone.utc)


# =============================================================================
# Camera
# =============================================================================

class Camera(Base):
    """A camera entity that produces evidence."""
    __tablename__ = "cameras"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    location = Column(String(512), nullable=True)
    source = Column(String(255), nullable=True)
    timezone = Column(String(50), nullable=True)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    
    case = relationship("Case")
    evidence = relationship("Evidence", back_populates="camera")

# =============================================================================
# Case
# =============================================================================

class Case(Base):
    """A forensic investigation case."""
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=_uuid)
    case_number = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    investigator = Column(String(255), nullable=False)
    investigator_id = Column(String(50), nullable=True)
    status = Column(String(30), nullable=False, default="OPEN")
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    evidence = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")
    cameras = relationship("Camera", back_populates="case", cascade="all, delete-orphan")
    chain_events = relationship("ChainEvent", back_populates="case", cascade="all, delete-orphan")
    merkle_records = relationship("MerkleRecord", back_populates="case", cascade="all, delete-orphan")
    trust_receipts = relationship("TrustReceipt", back_populates="case", cascade="all, delete-orphan")


# =============================================================================
# Evidence
# =============================================================================

class Evidence(Base):
    """An ingested piece of evidence (video file, image, disk image, etc.)."""
    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True, default=_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    camera_id = Column(String(36), ForeignKey("cameras.id"), nullable=True, index=True)
    filename = Column(String(512), nullable=False)
    original_filename = Column(String(512), nullable=False)
    source_device = Column(String(255), nullable=True)
    source_vendor = Column(String(255), nullable=True, default="Unknown")
    evidence_type = Column(String(50), nullable=False, default="video")
    acquisition_method = Column(String(100), nullable=False, default="file_upload")
    size = Column(BigInteger, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    mime_type = Column(String(100), nullable=True)
    acquired_at = Column(DateTime, nullable=False, default=_utcnow)
    acquired_by = Column(String(255), nullable=True)
    meta_data = Column(JSON, nullable=True)  # FFprobe meta_data, codec info, etc.
    status = Column(String(30), nullable=False, default="INGESTED")
    storage_path = Column(String(1024), nullable=False)

    # Video-specific meta_data (denormalized for quick access)
    codec = Column(String(50), nullable=True)
    resolution = Column(String(30), nullable=True)
    fps = Column(Float, nullable=True)
    duration = Column(Float, nullable=True)
    has_audio = Column(Boolean, nullable=True)
    container_format = Column(String(50), nullable=True)

    # Relationships
    case = relationship("Case", back_populates="evidence")
    camera = relationship("Camera", back_populates="evidence")
    segments = relationship("EvidenceSegment", back_populates="evidence", cascade="all, delete-orphan")
    ai_results = relationship("AIResult", back_populates="evidence", cascade="all, delete-orphan")
    forensic_findings = relationship("ForensicFinding", back_populates="evidence", cascade="all, delete-orphan")
    chain_events = relationship("ChainEvent", back_populates="evidence")

    __table_args__ = (
        Index("ix_evidence_case_status", "case_id", "status"),
    )


# =============================================================================
# Evidence Segment (recovered / split segments)
# =============================================================================

class EvidenceSegment(Base):
    """A recovered or split segment of evidence."""
    __tablename__ = "evidence_segments"

    id = Column(String(36), primary_key=True, default=_uuid)
    evidence_id = Column(String(36), ForeignKey("evidence.id"), nullable=False, index=True)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    file_path = Column(String(1024), nullable=False)
    sha256 = Column(String(64), nullable=False)
    size = Column(BigInteger, nullable=True)
    recovery_method = Column(String(100), nullable=False, default="direct")
    source_offset = Column(BigInteger, nullable=True)  # byte offset in source
    confidence = Column(Float, nullable=True, default=1.0)
    validation_status = Column(String(30), nullable=False, default="PENDING")
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    # Relationships
    evidence = relationship("Evidence", back_populates="segments")


# =============================================================================
# AI Result
# =============================================================================

class AIResult(Base):
    """An AI detection / analysis result for a piece of evidence."""
    __tablename__ = "ai_results"

    id = Column(String(36), primary_key=True, default=_uuid)
    evidence_id = Column(String(36), ForeignKey("evidence.id"), nullable=False, index=True)
    frame_number = Column(Integer, nullable=True)
    timestamp = Column(Float, nullable=True)  # seconds into the video
    detection_type = Column(String(50), nullable=False)  # face, person, vehicle, plate, etc.
    label = Column(String(255), nullable=True)
    confidence = Column(Float, nullable=False)
    bounding_box = Column(JSON, nullable=True)  # [x, y, w, h]
    track_id = Column(String(50), nullable=True)
    embedding_reference = Column(String(255), nullable=True)  # reference to stored embedding
    model_name = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)
    meta_data = Column(JSON, nullable=True)  # extra inference details
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    # Relationships
    evidence = relationship("Evidence", back_populates="ai_results")

    __table_args__ = (
        Index("ix_ai_results_type", "evidence_id", "detection_type"),
        Index("ix_ai_results_track", "evidence_id", "track_id"),
    )


# =============================================================================
# Chain of Custody Event
# =============================================================================

class ChainEvent(Base):
    """An append-only chain-of-custody event."""
    __tablename__ = "chain_events"

    id = Column(String(36), primary_key=True, default=_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    evidence_id = Column(String(36), ForeignKey("evidence.id"), nullable=True)
    sequence_number = Column(Integer, nullable=False)  # monotonic within a case
    event_type = Column(String(100), nullable=False)
    actor = Column(String(255), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=_utcnow)
    payload_hash = Column(String(64), nullable=True)  # SHA-256 of event payload
    previous_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False, unique=True)
    meta_data = Column(JSON, nullable=True)

    # Relationships
    case = relationship("Case", back_populates="chain_events")
    evidence = relationship("Evidence", back_populates="chain_events")

    __table_args__ = (
        Index("ix_chain_case_seq", "case_id", "sequence_number"),
    )


# =============================================================================
# Merkle Record
# =============================================================================

class MerkleRecord(Base):
    """A Merkle tree root computed over evidence/chain hashes."""
    __tablename__ = "merkle_records"

    id = Column(String(36), primary_key=True, default=_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    root_hash = Column(String(64), nullable=False)
    leaf_count = Column(Integer, nullable=False)
    leaves = Column(JSON, nullable=True)  # ordered list of leaf hashes
    algorithm = Column(String(20), nullable=False, default="SHA-256")
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    # Relationships
    case = relationship("Case", back_populates="merkle_records")


# =============================================================================
# Trust Receipt
# =============================================================================

class TrustReceipt(Base):
    """A signed receipt from the independent trust authority."""
    __tablename__ = "trust_receipts"

    id = Column(String(36), primary_key=True, default=_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    chain_head = Column(String(64), nullable=False)
    merkle_root = Column(String(64), nullable=True)
    signature = Column(Text, nullable=False)
    algorithm = Column(String(50), nullable=False)
    authority_id = Column(String(255), nullable=False)
    key_version = Column(String(50), nullable=True)
    timestamp = Column(DateTime, nullable=False, default=_utcnow)
    verification_status = Column(String(30), nullable=True, default="UNVERIFIED")
    meta_data = Column(JSON, nullable=True)

    # Relationships
    case = relationship("Case", back_populates="trust_receipts")


# =============================================================================
# Users & Roles (Authentication)
# =============================================================================

class User(Base):
    """SAKSHYA User with role-based access control."""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="investigator", nullable=False)  # admin, investigator, auditor
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utcnow)


# =============================================================================
# Forensic Finding
# =============================================================================

class ForensicFinding(Base):
    """An anomaly or finding detected during video forensics or AI analysis."""
    __tablename__ = "forensic_findings"

    id = Column(String(36), primary_key=True, default=_uuid)
    evidence_id = Column(String(36), ForeignKey("evidence.id"), nullable=False, index=True)
    type = Column(String(100), nullable=False) # e.g., DUPLICATE_FRAMES, TIMESTAMP_JUMP
    frame_start = Column(Integer, nullable=True)
    frame_end = Column(Integer, nullable=True)
    timestamp_start = Column(Float, nullable=True)
    timestamp_end = Column(Float, nullable=True)
    severity = Column(String(20), nullable=False, default="MEDIUM")
    description = Column(Text, nullable=False)
    method = Column(String(100), nullable=False)
    parameters = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    evidence = relationship("Evidence")


# =============================================================================
# Background Job
# =============================================================================

class Job(Base):
    """A background processing job (analysis, recovery, etc.)."""
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=_uuid)
    case_id = Column(String(36), nullable=True, index=True)
    evidence_id = Column(String(36), nullable=True, index=True)
    job_type = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="QUEUED")
    progress = Column(Float, nullable=True, default=0.0)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=_utcnow)


# =============================================================================
# Electronic Record Certificate (BSA §63(4))
# =============================================================================

class ElectronicRecordCertificate(Base):
    """BSA Section 63(4)-oriented electronic-record certificate draft."""
    __tablename__ = "electronic_record_certificates"

    id = Column(String(36), primary_key=True, default=_uuid)
    certificate_id = Column(String(100), unique=True, nullable=False, index=True)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    evidence_id = Column(String(36), ForeignKey("evidence.id"), nullable=False, index=True)
    
    electronic_record_identifier = Column(String(512), nullable=False)
    electronic_record_description = Column(Text, nullable=True)
    
    record_format = Column(String(100), nullable=False)
    record_size = Column(BigInteger, nullable=False)
    record_sha256 = Column(String(64), nullable=False)
    
    source_device_id = Column(String(255), nullable=True, default="NOT PROVIDED")
    source_device_type = Column(String(255), nullable=True, default="NOT PROVIDED")
    source_device_description = Column(Text, nullable=True, default="NOT PROVIDED")
    
    software_used = Column(String(255), nullable=True)
    software_version = Column(String(255), nullable=True)
    
    date_of_acquisition = Column(DateTime, nullable=True)
    date_of_generation = Column(DateTime, nullable=False, default=_utcnow)
    
    method_of_production = Column(String(255), nullable=True, default="NOT RECORDED")
    device_operational_status = Column(String(255), nullable=True, default="NOT VERIFIED")
    regular_use_context = Column(Text, nullable=True, default="NOT RECORDED")
    information_fed_in_ordinary_course = Column(Text, nullable=True, default="NOT RECORDED")
    derivation_relationship = Column(Text, nullable=True, default="NOT APPLICABLE")
    
    analysis_id = Column(String(36), nullable=True)
    certificate_status = Column(String(50), nullable=False, default="REVIEW_REQUIRED")
    
    signatory_name = Column(String(255), nullable=True, default="NOT PROVIDED")
    signatory_role = Column(String(255), nullable=True, default="NOT PROVIDED")
    signatory_organization = Column(String(255), nullable=True, default="NOT PROVIDED")
    signatory_address = Column(Text, nullable=True, default="NOT PROVIDED")
    signatory_contact = Column(String(255), nullable=True, default="NOT PROVIDED")
    
    signature_status = Column(String(50), nullable=False, default="UNSIGNED")
    signature_method = Column(String(100), nullable=True, default="NOT APPLICABLE")
    
    certificate_content_hash = Column(String(64), nullable=True)
    certificate_pdf_sha256 = Column(String(64), nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    
    case = relationship("Case")
    evidence = relationship("Evidence")

