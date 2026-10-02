"""
SAKSHYA Configuration Module

Loads settings from environment variables with sensible defaults.
All secrets and configurable paths are externalized here.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application-wide configuration loaded from environment / .env file."""

    # --- Application ---
    sakshya_version: str = Field(default="0.1.0")
    sakshya_env: str = Field(default="development")
    sakshya_debug: bool = Field(default=True)
    sakshya_host: str = Field(default="0.0.0.0")
    sakshya_port: int = Field(default=8000)
    sakshya_secret_key: str = Field(default="CHANGE_ME_TO_A_RANDOM_SECRET")

    # --- Database ---
    database_url: str = Field(default="sqlite:///./storage/sakshya.db")

    # --- Storage Paths ---
    evidence_storage_path: str = Field(default="./storage/evidence")
    export_storage_path: str = Field(default="./storage/exports")
    temp_storage_path: str = Field(default="./storage/temp")

    # --- AI Models ---
    model_base_path: str = Field(default="./models")
    sakshya_ai_mode: str = Field(default="real")  # real | demo
    detection_confidence: float = Field(default=0.35)
    yolo_iou: float = Field(default=0.45)
    frame_sample_rate: int = Field(default=5)
    max_analysis_frames: int = Field(default=0)  # 0 = unlimited
    max_video_duration: int = Field(default=3600)
    max_upload_size: int = Field(default=2_147_483_648)  # 2 GB

    # --- Trust Service ---
    trust_service_url: str = Field(default="http://localhost:8001")
    trust_authority_id: str = Field(default="SAKSHYA-TRUST-PROTOTYPE-001")

    # --- Authentication (simple demo) ---
    default_investigator: str = Field(default="Demo Investigator")
    default_investigator_role: str = Field(default="Lead Investigator")
    default_investigator_id: str = Field(default="INV-001")

    # --- Logging ---
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    def ensure_directories(self) -> None:
        """Create required storage directories if they don't exist."""
        for path_str in [
            self.evidence_storage_path,
            self.export_storage_path,
            self.temp_storage_path,
            self.model_base_path,
        ]:
            Path(path_str).mkdir(parents=True, exist_ok=True)

        # Ensure database directory exists
        db_path = self.database_url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)


# Singleton settings instance
settings = Settings()
