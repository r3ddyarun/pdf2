"""
Pydantic models for API requests and responses
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator


class RedactionReason(str, Enum):
    """Types of content that can be redacted"""
    EMAIL = "email"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    PHONE_NUMBER = "phone_number"
    DATE_OF_BIRTH = "date_of_birth"
    ADDRESS = "address"
    NAME = "name"
    ACCOUNT_NUMBER = "account_number"
    CUSTOM = "custom"


class RedactionBlock(BaseModel):
    """Represents a redacted block in the document"""
    page_number: int = Field(..., description="Page number where redaction occurs")
    x: float = Field(..., description="X coordinate of redaction block")
    y: float = Field(..., description="Y coordinate of redaction block")
    width: float = Field(..., description="Width of redaction block")
    height: float = Field(..., description="Height of redaction block")
    reason: RedactionReason = Field(..., description="Reason for redaction")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    original_text: Optional[str] = Field(None, description="Original text that was redacted")


class FileUploadResponse(BaseModel):
    """Response for file upload"""
    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    s3_bucket: str = Field(..., description="S3 bucket name")
    s3_key: str = Field(..., description="S3 object key")


class RedactionResult(BaseModel):
    """Result of PDF redaction process"""
    file_id: str = Field(..., description="Original file ID")
    redacted_file_id: str = Field(..., description="Redacted file ID")
    redacted_s3_bucket: str = Field(..., description="S3 bucket for redacted file")
    redacted_s3_key: str = Field(..., description="S3 key for redacted file")
    total_pages: int = Field(..., description="Total pages in document")
    redaction_blocks: List[RedactionBlock] = Field(..., description="List of redaction blocks")
    processing_time_seconds: float = Field(..., description="Processing time in seconds")
    summary: Dict[str, Any] = Field(..., description="Summary statistics")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RedactionSummary(BaseModel):
    """Summary of redaction results"""
    total_redactions: int = Field(..., description="Total number of redactions")
    redactions_by_reason: Dict[RedactionReason, int] = Field(..., description="Redactions grouped by reason")
    pages_affected: int = Field(..., description="Number of pages with redactions")
    confidence_scores: Dict[str, float] = Field(..., description="Confidence score statistics")


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FileDownloadRequest(BaseModel):
    """Request model for file download"""
    bucket: str = Field(..., description="S3 bucket name")
    key: str = Field(..., description="S3 object key")


class MetricsData(BaseModel):
    """Metrics data model"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    file_id: str = Field(..., description="File ID")
    processing_time: float = Field(..., description="Processing time in seconds")
    file_size: int = Field(..., description="File size in bytes")
    redaction_count: int = Field(..., description="Number of redactions performed")
    success: bool = Field(..., description="Whether processing was successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")
