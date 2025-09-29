"""
Analytics and Statistics API endpoints
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, status

from app.database.clickhouse_client import clickhouse_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["analytics"])


def get_current_user():
    """Simple authentication - replace with proper auth in production"""
    # For now, accept any token or no token
    # In production, implement proper JWT validation
    return {"user_id": "demo_user", "username": "demo"}


@router.get("/results/{file_id}")
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get results for file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/stats")
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
