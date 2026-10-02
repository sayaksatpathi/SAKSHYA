"""
SAKSHYA — Main FastAPI Application

Vendor-Agnostic CCTV/DVR/NVR Forensic Evidence & AI Investigation Platform
Smart India Hackathon 2026 · SIH26150 · Team Aroeminds
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend import SAKSHYA_VERSION
from backend.config import settings
from backend.database import init_db
from backend.api import auth, cases, evidence, chain, merkle, trust, analysis, jobs, health, report, ai, investigation, cameras, certificates

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    # Startup
    logger.info("SAKSHYA v%s starting up", SAKSHYA_VERSION)
    settings.ensure_directories()
    init_db()

    # Initialize AI engine lazily (don't fail if models are missing)
    try:
        from backend.ai.engine import ai_engine
        ai_engine.initialize(settings.model_base_path)
    except Exception as e:
        logger.warning("AI engine initialization deferred: %s", e)

    yield

    # Shutdown
    logger.info("SAKSHYA shutting down")


app = FastAPI(
    title="SAKSHYA",
    description=(
        "Vendor-Agnostic CCTV/DVR/NVR Forensic Evidence & AI Investigation Platform. "
        "Smart India Hackathon 2026 · SIH26150 · Team Aroeminds"
    ),
    version=SAKSHYA_VERSION,
    lifespan=lifespan,
)

# CORS — allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Depends
from backend.auth import get_current_investigator, get_current_auditor, get_current_user

# --- API Routes ---
# Public / Unauthenticated
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(health.router, tags=["Health"])

# Investigator Routes (Admins also have access)
app.include_router(cases.router, prefix="/api", tags=["Cases"], dependencies=[Depends(get_current_investigator)])
app.include_router(evidence.router, prefix="/api", tags=["Evidence"], dependencies=[Depends(get_current_investigator)])
app.include_router(analysis.router, prefix="/api", tags=["AI Analysis"], dependencies=[Depends(get_current_investigator)])
app.include_router(jobs.router, prefix="/api", tags=["Jobs"], dependencies=[Depends(get_current_investigator)])
app.include_router(ai.router, prefix="/api", tags=["AI"], dependencies=[Depends(get_current_investigator)])
app.include_router(investigation.router, prefix="/api", tags=["Investigation"], dependencies=[Depends(get_current_investigator)])
app.include_router(cameras.router, prefix="/api", tags=["Cameras"], dependencies=[Depends(get_current_investigator)])

# Auditor / Verification Routes (Admins and Investigators might also need read access depending on design, 
# but for SIH let's use get_current_user so anyone logged in can verify hashes)
app.include_router(chain.router, prefix="/api", tags=["Chain of Custody"], dependencies=[Depends(get_current_user)])
app.include_router(merkle.router, prefix="/api", tags=["Merkle Tree"], dependencies=[Depends(get_current_user)])
app.include_router(trust.router, prefix="/api", tags=["Trust"], dependencies=[Depends(get_current_user)])
app.include_router(report.router, prefix="/api", tags=["Reports"], dependencies=[Depends(get_current_user)])
app.include_router(certificates.router, prefix="/api", tags=["Certificates"])

app.mount("/", StaticFiles(directory=".", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.sakshya_host,
        port=settings.sakshya_port,
        reload=settings.sakshya_debug,
    )
