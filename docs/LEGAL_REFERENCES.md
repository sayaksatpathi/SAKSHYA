# SAKSHYA Legal References

## Bharatiya Sakshya Adhiniyam, 2023

SAKSHYA implements a structured electronic-record management system designed around the principles established in the **Bharatiya Sakshya Adhiniyam, 2023 (BSA)**.

> **Disclaimer:** SAKSHYA is a technical forensic platform. It manages hashes, metadata, and data integrity relationships. It **does not** provide legal advice. The generation of a certificate draft or report does not guarantee legal admissibility or compliance. A responsible person must review, complete, and properly authenticate the factual assertions according to court procedures.

### Section 63: Admissibility of Electronic Records

**Section 63(1)**  
Declares that information contained in an electronic record (printed, stored, recorded, or copied) shall be deemed a document, and if the conditions under this section are satisfied, it is admissible in proceedings without further proof of the original.

**Section 63(2)**  
Establishes the core conditions for admissibility:
* **(a)** The computer or communication device producing the record was in regular use by a person having lawful control.
* **(b)** The information was regularly fed into the device in the ordinary course of activities.
* **(c)** The device was operating properly during the material part of the period (or any malfunction did not affect the accuracy of the data).
* **(d)** The reproduction is derived from the original information fed into the device.

*SAKSHYA handles these via strict tracking of `derivation_relationship`, explicit fields for operational status, and ensuring unknown/unverified facts are recorded as `NOT VERIFIED` or `NOT RECORDED` rather than assumed true.*

**Section 63(3)**  
Addresses systems involving multiple computers, networks, or interrelated devices over a period, treating them collectively as a single device for the purposes of the act.

**Section 63(4)**  
Requires a certificate for the electronic record to be submitted in evidence. The certificate must:
* **(a)** Identify the electronic record and describe how it was produced.
* **(b)** Give particulars of the device(s) involved in production.
* **(c)** Deal with the conditions mentioned in Section 63(2).
* **(d)** Be signed by a person in charge of the device or an expert (the "responsible person").

*SAKSHYA generates a **BSA Section 63(4)-oriented certificate draft** that structures this information, pulling available hashes, timestamps, and metadata into a standardized format for review and signature by the responsible party.*

### Authoritative Source
Always refer to the official and current statutory text.
* **India Code:** [https://www.indiacode.nic.in/](https://www.indiacode.nic.in/)

### SAKSHYA's Role
SAKSHYA's core contribution is maintaining the **cryptographic integrity** of the electronic record. When a certificate draft is created:
1. The SAKSHYA ledger records an tamper-evident `BSA_CERTIFICATE_CREATED` event.
2. The certificate receives a canonical `certificate_content_hash`.
3. The certificate explicitly binds to the original `evidence_sha256` and any derived AI `analysis_hash`.
4. The Merkle root and Trust receipts cryptographically prove the record existed in exactly that form at that time.
