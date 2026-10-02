# SAKSHYA Evidence Lifecycle

This document traces the path of a piece of forensic evidence from ingest to final reporting. It clearly distinguishes original evidence from derived artifacts.

```text
Source Evidence
      ↓
Ingest (Acquisition Service)
      ↓
SHA-256 (Integrity Checkpoint)
      ↓
Protected Evidence Copy (Read-Only logical storage)
      ↓
Metadata (Stored alongside, separated from raw file)
      ↓
Derived Processing (e.g. format conversion, segmentation)
      ↓
AI Analysis (Investigative assistance: embeddings, YOLO, ANPR)
      ↓
Ledger Events (Append-only provenance)
      ↓
Merkle Root (Aggregate integrity over cases)
      ↓
Trust Receipt (Independent cryptographic anchor)
      ↓
Export Manifest
      ↓
Report (PDF with cryptographic hashes)
```

## Derived Artifacts vs Original Evidence
- **Original Evidence**: The raw file (e.g., MP4) ingested. Hashed immediately and never modified in-place.
- **Derived Artifacts**: Segments, frames, and metadata. These are stored separately and linked relationally to the original evidence via the database and the append-only ledger.
