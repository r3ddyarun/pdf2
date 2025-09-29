"""
File Upload API endpoints
"""

import logging
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, status
from fastapi.responses import JSONResponse

from app.models import FileUploadResponse
from app.services.s3_service import s3_service
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["file-upload"])


def get_current_user():
    """Simple authentication - replace with proper auth in production"""
    # For now, accept any token or no token
    # In production, implement proper JWT validation
    return {"user_id": "demo_user", "username": "demo"}


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload PDF file for processing"""
    
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed"
            )
        
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        
        # Read file content
        file_content = await file.read()
        
        # Validate file size (e.g., max 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds maximum allowed size of 50MB"
            )
        
        # Generate S3 key
        s3_key = f"uploads/{file_id}/{file.filename}"
        
        # Upload to S3
        upload_success = s3_service.upload_file(file_content, s3_key, file.content_type)
        
        if not upload_success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to storage"
            )
        
        logger.info(f"File uploaded successfully: {file_id}")
        
        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            file_size=len(file_content),
            s3_bucket=settings.s3_bucket_name,
            s3_key=s3_key
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file upload"
        )


@router.get("/upload-url/{filename}")
async def get_upload_url(
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Get presigned URL for direct file upload to S3"""
    
    try:
        # Validate filename
        if not filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed"
            )
        
        # Generate unique file ID and S3 key
        file_id = str(uuid.uuid4())
        s3_key = f"uploads/{file_id}/{filename}"
        
        # Generate presigned URL for upload
        presigned_url = s3_service.get_presigned_upload_url(s3_key)
        
        if not presigned_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate upload URL"
            )
        
        return {
            "file_id": file_id,
            "filename": filename,
            "upload_url": presigned_url,
            "s3_key": s3_key
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate upload URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
