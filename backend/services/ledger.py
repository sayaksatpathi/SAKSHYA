"""
SAKSHYA Chain-of-Custody Ledger Service

Implements an append-only chain of custody events with SHA-256 linking.
Each event hash depends on the previous event hash, creating an
ordered, tamper-evident log.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.models import ChainEvent
from backend.crypto.hashing import canonicalize_json, sha256_string

logger = logging.getLogger(__name__)

# Genesis hash — the "previous hash" for the first event in any case chain.
GENESIS_HASH = "0" * 64


class LedgerService:
    """Manages the append-only chain-of-custody ledger."""

    def __init__(self, db: Session):
        self.db = db

    def append_event(
        self,
        case_id: str,
        event_type: str,
        actor: str,
        evidence_id: Optional[str] = None,
        meta_data: Optional[dict[str, Any]] = None,
    ) -> ChainEvent:
        """
        Append a new event to the case's chain of custody.

        The event_hash is computed as SHA-256 of the canonical JSON
        of event data including the previous event's hash.

        Args:
            case_id: The case this event belongs to.
            event_type: Type of event (e.g., EVIDENCE_INGESTED, ANALYSIS_STARTED).
            actor: Who performed the action.
            evidence_id: Optional related evidence ID.
            meta_data: Optional additional event data.

        Returns:
            The newly created ChainEvent.
        """
        # Get the latest event for this case to determine the previous hash
        latest = (
            self.db.query(ChainEvent)
            .filter(ChainEvent.case_id == case_id)
            .order_by(ChainEvent.sequence_number.desc())
            .first()
        )

        previous_hash = latest.event_hash if latest else GENESIS_HASH
        sequence_number = (latest.sequence_number + 1) if latest else 1

        now = datetime.now(timezone.utc)

        # Build the canonical event data for hashing
        event_data = {
            "case_id": case_id,
            "evidence_id": evidence_id,
            "sequence_number": sequence_number,
            "event_type": event_type,
            "actor": actor,
            "timestamp": now.isoformat(),
            "previous_hash": previous_hash,
        }

        if meta_data:
            event_data["meta_data"] = meta_data

        # Compute payload hash (hash of just the meta_data/payload)
        payload_hash = None
        if meta_data:
            payload_hash = sha256_string(canonicalize_json(meta_data))

        # Compute event hash (hash of the full canonical event)
        event_hash = sha256_string(canonicalize_json(event_data))

        event = ChainEvent(
            case_id=case_id,
            evidence_id=evidence_id,
            sequence_number=sequence_number,
            event_type=event_type,
            actor=actor,
            timestamp=now,
            payload_hash=payload_hash,
            previous_hash=previous_hash,
            event_hash=event_hash,
            meta_data=meta_data,
        )

        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        logger.info(
            "Chain event appended",
            extra={
                "case_id": case_id,
                "event_type": event_type,
                "sequence": sequence_number,
                "event_hash": event_hash[:16] + "...",
            },
        )

        return event

    def get_chain(self, case_id: str) -> list[ChainEvent]:
        """Get all chain events for a case, ordered by sequence."""
        return (
            self.db.query(ChainEvent)
            .filter(ChainEvent.case_id == case_id)
            .order_by(ChainEvent.sequence_number.asc())
            .all()
        )

    def get_chain_head(self, case_id: str) -> Optional[str]:
        """Get the most recent event hash (chain head) for a case."""
        latest = (
            self.db.query(ChainEvent)
            .filter(ChainEvent.case_id == case_id)
            .order_by(ChainEvent.sequence_number.desc())
            .first()
        )
        return latest.event_hash if latest else None

    def verify_chain(self, case_id: str) -> dict:
        """
        Verify the integrity of the entire chain for a case.

        Recomputes each event hash and checks linkage.

        Returns:
            Dictionary with:
                - valid: bool
                - total_events: int
                - verified_events: int
                - first_failure: Optional[int] (sequence number)
                - failure_detail: Optional[str]
        """
        events = self.get_chain(case_id)

        if not events:
            return {
                "valid": True,
                "total_events": 0,
                "verified_events": 0,
                "first_failure": None,
                "failure_detail": None,
            }

        verified = 0
        expected_previous = GENESIS_HASH

        for event in events:
            # Check previous hash linkage
            if event.previous_hash != expected_previous:
                return {
                    "valid": False,
                    "total_events": len(events),
                    "verified_events": verified,
                    "first_failure": event.sequence_number,
                    "failure_detail": (
                        f"Event #{event.sequence_number}: previous_hash mismatch. "
                        f"Expected {expected_previous[:16]}..., "
                        f"got {event.previous_hash[:16]}..."
                    ),
                }

            # Recompute event hash
            event_data = {
                "case_id": event.case_id,
                "evidence_id": event.evidence_id,
                "sequence_number": event.sequence_number,
                "event_type": event.event_type,
                "actor": event.actor,
                "timestamp": event.timestamp.replace(tzinfo=timezone.utc).isoformat() if event.timestamp else None,
                "previous_hash": event.previous_hash,
            }
            if event.meta_data:
                event_data["meta_data"] = event.meta_data

            recomputed_hash = sha256_string(canonicalize_json(event_data))

            if recomputed_hash != event.event_hash:
                return {
                    "valid": False,
                    "total_events": len(events),
                    "verified_events": verified,
                    "first_failure": event.sequence_number,
                    "failure_detail": (
                        f"Event #{event.sequence_number}: event_hash mismatch. "
                        f"Stored {event.event_hash[:16]}..., "
                        f"recomputed {recomputed_hash[:16]}..."
                    ),
                }

            expected_previous = event.event_hash
            verified += 1

        return {
            "valid": True,
            "total_events": len(events),
            "verified_events": verified,
            "first_failure": None,
            "failure_detail": None,
        }

    def get_event_count(self, case_id: str) -> int:
        """Get the total number of chain events for a case."""
        return (
            self.db.query(func.count(ChainEvent.id))
            .filter(ChainEvent.case_id == case_id)
            .scalar() or 0
        )
