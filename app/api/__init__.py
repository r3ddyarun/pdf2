"""
API package for PDF Redaction Service
"""

from .core import router as core_router
from .file_upload import router as file_upload_router
from .file_processing import router as file_processing_router
from .file_download import router as file_download_router
from .analytics import router as analytics_router

__all__ = [
    "core_router",
    "file_upload_router", 
    "file_processing_router",
    "file_download_router",
    "analytics_router"
]
