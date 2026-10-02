# SAKSHYA Data Provenance Architecture

SAKSHYA guarantees the authenticity and traceability of digital evidence through a multi-tiered provenance lifecycle, ensuring admissibility in a legal context.

## 1. Safe Ingestion & Isolation
* **Sanitization:** Files uploaded are renamed using `os.path.basename` and strict character filters to prevent path traversal and shell injection vulnerabilities.
* **Working Copy Isolation:** The original evidence file is ingested, hashed (SHA-256), and moved to an tamper-evident `storage/` directory. All AI analyses and metadata extraction happen on this tamper-evident reference without modifying the original bytes.

## 2. Event Ledger (Chain of Custody)
Every significant operation is recorded in the `chain_events` table as an append-only ledger:
* `EVIDENCE_INGESTED`
* `ANALYSIS_COMPLETED`
* `FORENSIC_FINDING`
Each event holds the timestamp, actor, and previous hash, forming an internal blockchain-style linked list of actions.

## 3. Merkle Tree Integrity
Once evidence for a case is compiled, the system hashes all individual evidence chunks/files and computes a Merkle Tree Root. The Merkle structure proves that no evidence was inserted, modified, or deleted without altering the root.

## 4. Trust Receipt Sealing
The Merkle root is sent to an independent `trust_service` which acts as an external Certificate Authority. It issues a `TrustReceipt` containing:
* Merkle Root
* Cryptographic RSA Signature
* Authority ID
This ensures non-repudiation; the system itself cannot forge a valid receipt without the external private key.

## 5. Verification & Tamper Detection
When a case is finalized, the PDF Report includes the signature and hashes. 
Any subsequent verification request recalculates the SHA-256 hash of the evidence. If even a single byte differs (simulated via the Tamper endpoint), the hash mismatch breaks the Merkle tree and invalidates the Trust Receipt, definitively proving tampering.
