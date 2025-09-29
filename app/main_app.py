"""
Main FastAPI application with modular API structure
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import sys

from app.config import settings
from app.database.clickhouse_client import clickhouse_client
from app.middleware.metrics import metrics_middleware
from app.utils.logging_config import setup_logging

# Import API routers
from app.api import (
    core_router,
    file_upload_router,
    file_processing_router,
    file_download_router,
    analytics_router
)

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting PDF Redaction Service...")
    
    # Initialize database
    try:
        clickhouse_client.create_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Streamlit is now started separately - no automatic startup
    logger.info("FastAPI server ready - Streamlit UI can be started separately on port 8501")
    
    yield
    
    # Shutdown
    logger.info("Shutting down PDF Redaction Service...")


# Create FastAPI app
app = FastAPI(
    title="PDF Redaction Service API",
    description="API for processing PDF files to detect and redact sensitive information",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add metrics middleware
app.middleware("http")(metrics_middleware)

# Include API routers
app.include_router(core_router)
app.include_router(file_upload_router)
app.include_router(file_processing_router)
app.include_router(file_download_router)
app.include_router(analytics_router)


@app.get("/ui", response_class=HTMLResponse)
async def streamlit_ui():
    """Redirect to Streamlit UI"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>PDF Redaction Service UI</title>
        <meta http-equiv="refresh" content="0; url=http://localhost:{settings.streamlit_port}">
    </head>
    <body>
        <p>Redirecting to Streamlit UI...</p>
        <p>If you are not redirected automatically, <a href="http://localhost:{settings.streamlit_port}">click here</a>.</p>
    </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main_app:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=True
    )
