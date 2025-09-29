"""
File Download API endpoints
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import Response, StreamingResponse

from app.models import FileDownloadRequest
from app.services.s3_service import s3_service
from app.database.clickhouse_client import clickhouse_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["file-download"])


def get_current_user():
    """Simple authentication - replace with proper auth in production"""
    # For now, accept any token or no token
    # In production, implement proper JWT validation
    return {"user_id": "demo_user", "username": "demo"}


@router.get("/download/{file_id}")
async def download_file_by_id(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Download file by file ID - direct download without additional API call"""
    
    try:
        logger.info(f"Direct download request for file ID: {file_id}")
        
        # Get file information from database
        result = await get_results(file_id, current_user)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_id}"
            )
        
        # Extract download information
        redacted_bucket = result.get("redacted_s3_bucket")
        redacted_key = result.get("redacted_s3_key")
        
        if not redacted_bucket or not redacted_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Redacted file information not available"
            )
        
        # Download file from S3
        file_content = s3_service.download_file(redacted_key)
        
        if not file_content:
            logger.warning(f"File not found in S3: {redacted_key}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Redacted file not found: {redacted_key}"
            )
        
        # Generate filename
        filename = f"redacted_{file_id}.pdf"
        logger.info(f"Successfully downloaded file: {filename} ({len(file_content)} bytes)")
        
        # Return file directly
        return Response(
            content=file_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(file_content))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download file {file_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file download"
        )


@router.post("/download")
async def download_file(
    request: FileDownloadRequest,
    current_user: dict = Depends(get_current_user)
):
    """Download file from S3"""
    
    try:
        logger.info(f"Download request for file: {request.key} from bucket: {request.bucket}")
        
        # Validate request
        if not request.key or not request.bucket:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both bucket and key are required for download"
            )
        
        file_content = s3_service.download_file(request.key)
        
        if not file_content:
            logger.warning(f"File not found in S3: {request.key}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {request.key}"
            )
        
        # Extract filename from key
        filename = request.key.split('/')[-1] if '/' in request.key else request.key
        if not filename.endswith('.pdf'):
            filename += '.pdf'
        
        logger.info(f"Successfully downloaded file: {filename} ({len(file_content)} bytes)")
        
        # Create streaming response
        def iter_file():
            yield file_content
        
        return StreamingResponse(
            iter_file(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=redacted_{filename}",
                "Content-Length": str(len(file_content))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download file {request.key}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file download"
        )


async def get_results(file_id: str, current_user: dict):
    """Get processing results for a file - helper function"""
    
    try:
        # Get file history
        file_history = clickhouse_client.get_file_history(file_id)
        
        if not file_history:
            return None
        
        # Get the most recent result (first in the list since it's ordered by created_at DESC)
        latest_result = file_history[0] if file_history else {}
        
        # Get redaction blocks
        redaction_blocks = clickhouse_client.get_redaction_blocks(file_id)
        
        # Build response with all necessary fields for download
        result = {
            "file_id": file_id,
            "file_history": file_history,
            "redaction_blocks": redaction_blocks,
            # Include download-related fields from the latest result
            "filename": latest_result.get("filename"),
            "file_size": latest_result.get("file_size"),
            "s3_bucket": latest_result.get("s3_bucket"),
            "s3_key": latest_result.get("s3_key"),
            "redacted_s3_bucket": latest_result.get("redacted_s3_bucket"),
            "redacted_s3_key": latest_result.get("redacted_s3_key"),
            "total_pages": latest_result.get("total_pages"),
            "processing_time_seconds": latest_result.get("processing_time_seconds"),
            "total_redactions": latest_result.get("total_redactions"),
            "redactions_by_reason": latest_result.get("redactions_by_reason"),
            "confidence_scores": latest_result.get("confidence_scores"),
            "created_at": latest_result.get("created_at")
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get results for file {file_id}: {e}")
        return None
