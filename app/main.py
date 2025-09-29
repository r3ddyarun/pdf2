"""
FastAPI main application for PDF Redaction Service
"""

import logging
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
import io
import subprocess
import threading
import time

from app.config import settings
from app.models import (
    FileUploadResponse, RedactionResult, ErrorResponse, 
    FileDownloadRequest, MetricsData
)
from app.services.s3_service import s3_service
from app.services.pdf_processor import pdf_processor
from app.database.clickhouse_client import clickhouse_client
from app.middleware.metrics import metrics_middleware
from app.utils.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise PDF Redaction Service with AI-powered content detection",
    docs_url="/docs",
    redoc_url="/redoc"
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

# Security
security = HTTPBearer(auto_error=False)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Simple authentication - replace with proper auth in production"""
    # For now, accept any token or no token
    # In production, implement proper JWT validation
    return {"user_id": "demo_user", "username": "demo"}


def start_streamlit_app():
    """Start Streamlit app in background thread"""
    def run_streamlit():
        try:
            # Start Streamlit on port 8501
            subprocess.run([
                "streamlit", "run", "app/streamlit_app.py",
                "--server.port=8501",
                "--server.address=0.0.0.0",
                "--server.headless=true",
                "--server.enableCORS=false",
                "--server.enableXsrfProtection=false"
            ], check=True)
        except Exception as e:
            logger.error(f"Failed to start Streamlit: {e}")
    
    # Start Streamlit in background thread
    streamlit_thread = threading.Thread(target=run_streamlit, daemon=True)
    streamlit_thread.start()
    logger.info("Streamlit app started on port 8501")


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting PDF Redaction Service")
    try:
        # Initialize database tables
        clickhouse_client.create_tables()
        
        # Start Streamlit app in background
        start_streamlit_app()
        
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down PDF Redaction Service")
    clickhouse_client.close()


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "message": "PDF Redaction Service",
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}


@app.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload PDF file to S3 and return file information"""
    
    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Check file size
    file_content = await file.read()
    if len(file_content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {settings.max_file_size_mb}MB"
        )
    
    try:
        # Generate unique file ID and S3 key
        file_id = str(uuid.uuid4())
        s3_key = s3_service.generate_file_key(file.filename)
        
        # Upload to S3
        upload_success = s3_service.upload_file(file_content, s3_key)
        
        if not upload_success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to S3"
            )
        
        # Create response
        response = FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            file_size=len(file_content),
            s3_bucket=s3_service.s3_bucket_name,
            s3_key=s3_key
        )
        
        logger.info(f"File uploaded successfully: {file_id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file upload"
        )


@app.get("/upload-url/{filename}")
async def get_upload_url(
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Get presigned URL for direct S3 upload"""
    
    if not filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    try:
        s3_key = s3_service.generate_file_key(filename)
        presigned_url = s3_service.generate_presigned_url(s3_key, 'put_object')
        
        if not presigned_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate upload URL"
            )
        
        return {
            "upload_url": presigned_url,
            "s3_key": s3_key,
            "bucket": s3_service.s3_bucket_name,
            "expires_in": 3600
        }
        
    except Exception as e:
        logger.error(f"Failed to generate upload URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/process/{file_id}", response_model=RedactionResult)
async def process_file(
    file_id: str,
    bucket: str,
    key: str,
    current_user: dict = Depends(get_current_user)
):
    """Process PDF file for content detection and redaction"""
    
    start_time = time.time()
    
    try:
        # Download file from S3
        file_content = s3_service.download_file(key)
        
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found in S3"
            )
        
        # Process PDF
        result = pdf_processor.process_pdf(file_content, file_id)
        
        # Upload redacted file to S3
        redacted_key = f"redacted/{file_id}.pdf"
        upload_ok = s3_service.upload_file(result['redacted_bytes'], redacted_key, 'application/pdf')
        if not upload_ok:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload redacted file to S3"
            )
        
        # Store results in database
        db_data = {
            'file_id': file_id,
            'filename': f"{file_id}.pdf",
            'file_size': len(file_content),
            's3_bucket': bucket,
            's3_key': key,
            'redacted_s3_bucket': settings.s3_bucket_name,
            'redacted_s3_key': redacted_key,
            'total_pages': result['total_pages'],
            'processing_time_seconds': result['processing_time_seconds'],
            'total_redactions': result['summary']['total_redactions'],
            'redactions_by_reason': result['summary']['redactions_by_reason'],
            'confidence_scores': result['summary']['confidence_scores']
        }
        
        clickhouse_client.insert_redaction_result(db_data)
        
        # Store redaction blocks
        blocks_data = []
        for block in result['redaction_blocks']:
            blocks_data.append({
                'page_number': block.page_number,
                'x': block.x,
                'y': block.y,
                'width': block.width,
                'height': block.height,
                'reason': block.reason.value,
                'confidence': block.confidence,
                'original_text': block.original_text
            })
        
        clickhouse_client.insert_redaction_blocks(file_id, blocks_data)
        
        # Store metrics
        metrics_data = {
            'timestamp': datetime.utcnow(),
            'file_id': file_id,
            'processing_time': result['processing_time_seconds'],
            'file_size': len(file_content),
            'redaction_count': result['summary']['total_redactions'],
            'success': 1,
            'error_message': None
        }
        
        clickhouse_client.insert_metrics(metrics_data)
        
        logger.info(f"File processed successfully: {file_id}")
        
        # Convert redaction blocks to dictionaries for JSON serialization
        redaction_blocks_dict = []
        for block in result['redaction_blocks']:
            redaction_blocks_dict.append({
                'page_number': block.page_number,
                'x': block.x,
                'y': block.y,
                'width': block.width,
                'height': block.height,
                'reason': block.reason.value,
                'confidence': block.confidence,
                'original_text': block.original_text
            })
        
        # Create response with redacted file information
        response_data = {
            'file_id': file_id,
            'redacted_file_id': file_id,
            'redacted_s3_bucket': settings.s3_bucket_name,
            'redacted_s3_key': redacted_key,
            'total_pages': result['total_pages'],
            'redaction_blocks': redaction_blocks_dict,
            'processing_time_seconds': result['processing_time_seconds'],
            'summary': result['summary'],
            'created_at': result['created_at'],
            'status': 'success'  # Add status field for UI
        }
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process file {file_id}: {e}")
        
        # Store failure metrics
        metrics_data = {
            'timestamp': datetime.utcnow(),
            'file_id': file_id,
            'processing_time': time.time() - start_time,
            'file_size': 0,
            'redaction_count': 0,
            'success': 0,
            'error_message': str(e)
        }
        
        clickhouse_client.insert_metrics(metrics_data)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file processing"
        )


@app.post("/download")
async def download_file(
    request: FileDownloadRequest,
    current_user: dict = Depends(get_current_user)
):
    """Download file from S3"""
    
    try:
        file_content = s3_service.download_file(request.key)
        
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Create streaming response
        def iter_file():
            yield file_content
        
        return StreamingResponse(
            iter_file(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=redacted_{request.key.split('/')[-1]}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file download"
        )


@app.get("/results/{file_id}")
async def get_results(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get processing results for a file"""
    
    try:
        # Get file history
        file_history = clickhouse_client.get_file_history(file_id)
        
        if not file_history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File results not found"
            )
        
        # Get redaction blocks
        redaction_blocks = clickhouse_client.get_redaction_blocks(file_id)
        
        return {
            "file_id": file_id,
            "file_history": file_history,
            "redaction_blocks": redaction_blocks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get results for file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/stats")
async def get_processing_stats(
    hours: int = 24,
    current_user: dict = Depends(get_current_user)
):
    """Get processing statistics"""
    
    try:
        stats = clickhouse_client.get_processing_stats(hours)
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get processing stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )
