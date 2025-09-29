"""
File Processing API endpoints
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status

from app.models import RedactionResult
from app.services.s3_service import s3_service
from app.services.pdf_processor import pdf_processor
from app.database.clickhouse_client import clickhouse_client
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["file-processing"])


def get_current_user():
    """Simple authentication - replace with proper auth in production"""
    # For now, accept any token or no token
    # In production, implement proper JWT validation
    return {"user_id": "demo_user", "username": "demo"}


@router.post("/process", response_model=RedactionResult)
async def process_file(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """Process PDF file for content detection and redaction"""
    
    start_time = time.time()
    
    try:
        # Extract request data
        file_id = request.get("file_id")
        bucket = request.get("bucket")
        key = request.get("key")
        
        if not all([file_id, bucket, key]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields: file_id, bucket, key"
            )
        
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
        
        # Build API response
        api_response = {
            'file_id': file_id,
            'redacted_file_id': f"redacted_{file_id}",
            'redacted_s3_bucket': settings.s3_bucket_name,
            'redacted_s3_key': redacted_key,
            'total_pages': result['total_pages'],
            'redaction_blocks': redaction_blocks_dict,
            'processing_time_seconds': result['processing_time_seconds'],
            'summary': result['summary'],
            'created_at': result['created_at'],
            'status': 'success'  # Add status field for UI
        }
        return api_response
        
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


@router.post("/process/{file_id}", response_model=RedactionResult)
async def process_file_by_id(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Process PDF file by file ID (downloads from existing upload)"""
    
    start_time = time.time()
    
    try:
        # Get file information from database
        file_history = clickhouse_client.get_file_history(file_id)
        
        if not file_history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Get the most recent file record
        latest_file = file_history[0]
        bucket = latest_file.get("s3_bucket")
        key = latest_file.get("s3_key")
        
        if not bucket or not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File location not found"
            )
        
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
            'filename': latest_file.get("filename", f"{file_id}.pdf"),
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
        
        api_response = {
            'file_id': file_id,
            'redacted_file_id': f"redacted_{file_id}",
            'redacted_s3_bucket': settings.s3_bucket_name,
            'redacted_s3_key': redacted_key,
            'total_pages': result['total_pages'],
            'redaction_blocks': redaction_blocks_dict,
            'processing_time_seconds': result['processing_time_seconds'],
            'summary': result['summary'],
            'created_at': result['created_at'],
            'status': 'success'  # Add status field for UI
        }
        return api_response
        
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
