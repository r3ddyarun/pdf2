"""
AWS S3 service for file storage and management
"""

import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from app.config import settings

logger = logging.getLogger(__name__)


class S3Service:
    """AWS S3 service for file operations"""
    
    def __init__(self):
        self.s3_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize S3 client"""
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region
            )
            logger.info("S3 client initialized successfully")
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    def generate_presigned_url(self, key: str, operation: str = 'put_object', 
                             expires_in: int = 3600) -> Optional[str]:
        """Generate presigned URL for S3 operations"""
        try:
            if operation == 'put_object':
                url = self.s3_client.generate_presigned_url(
                    'put_object',
                    Params={'Bucket': settings.s3_bucket_name, 'Key': key},
                    ExpiresIn=expires_in
                )
            elif operation == 'get_object':
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': settings.s3_bucket_name, 'Key': key},
                    ExpiresIn=expires_in
                )
            else:
                logger.error(f"Unsupported operation: {operation}")
                return None
            
            logger.info(f"Generated presigned URL for {operation} operation")
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None
    
    def upload_file(self, file_content: bytes, key: str, 
                   content_type: str = 'application/pdf') -> bool:
        """Upload file to S3"""
        try:
            self.s3_client.put_object(
                Bucket=settings.s3_bucket_name,
                Key=key,
                Body=file_content,
                ContentType=content_type
            )
            logger.info(f"File uploaded successfully: {key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload file: {e}")
            return False
    
    def download_file(self, key: str) -> Optional[bytes]:
        """Download file from S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=settings.s3_bucket_name,
                Key=key
            )
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"Failed to download file: {e}")
            return None
    
    def delete_file(self, key: str) -> bool:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(
                Bucket=settings.s3_bucket_name,
                Key=key
            )
            logger.info(f"File deleted successfully: {key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete file: {e}")
            return False
    
    def file_exists(self, key: str) -> bool:
        """Check if file exists in S3"""
        try:
            self.s3_client.head_object(
                Bucket=settings.s3_bucket_name,
                Key=key
            )
            return True
        except ClientError:
            return False
    
    def get_file_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Get file metadata from S3"""
        try:
            response = self.s3_client.head_object(
                Bucket=settings.s3_bucket_name,
                Key=key
            )
            return {
                'size': response['ContentLength'],
                'last_modified': response['LastModified'],
                'content_type': response.get('ContentType', 'application/pdf'),
                'etag': response['ETag']
            }
        except ClientError as e:
            logger.error(f"Failed to get file metadata: {e}")
            return None
    
    def generate_file_key(self, filename: str, prefix: str = "uploads") -> str:
        """Generate unique file key for S3"""
        timestamp = datetime.utcnow().strftime("%Y/%m/%d")
        file_id = str(uuid.uuid4())
        return f"{prefix}/{timestamp}/{file_id}_{filename}"
    
    def generate_redacted_file_key(self, original_key: str) -> str:
        """Generate key for redacted file"""
        # Replace uploads with redacted in the path
        return original_key.replace("uploads/", "redacted/")


# Global S3 service instance
s3_service = S3Service()
