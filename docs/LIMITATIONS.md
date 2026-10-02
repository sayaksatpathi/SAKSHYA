# SAKSHYA Limitations & Future Work

## 1. Browser-Level E2E Testing
Currently, the environment does not support Playwright or Cypress for automated browser-level End-to-End testing. While full-stack API integration has been validated using FastAPI's `TestClient` mimicking browser interactions, comprehensive browser UI automation (e.g., clicking elements, visual regression testing) is a limitation and should be implemented in the future once the test environment allows.

## 2. Model Availability
If AI models for Face Search or Cross-Camera Re-ID are not installed, the platform gracefully degrades and reports `MODEL UNAVAILABLE` instead of fabricating synthetic results. This ensures strict adherence to forensic integrity but limits capabilities in unprovisioned environments.

## 3. Storage Scalability
Currently, evidence is stored directly on the local filesystem (`temp` and `storage`). For large-scale production, this should be migrated to an S3-compatible blob storage with proper access controls and lifecycle management.

## 4. Job Concurrency
While a `Job` model exists for tracking background tasks, complex operations like video analysis currently block synchronously or run without robust concurrent locking. Implementing Celery or a robust message queue (e.g., Redis/RabbitMQ) is necessary for high-volume concurrent processing to prevent duplicate processing of the same evidence.
