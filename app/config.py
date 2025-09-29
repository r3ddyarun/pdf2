"""
Configuration management for the PDF Redaction Service
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "PDF Redaction Service"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    api_port: int = 8000  # FastAPI port
    streamlit_port: int = 8501  # Streamlit port
    reload: bool = False
    
    # File Upload
    max_file_size_mb: int = 50
    allowed_extensions: str = "pdf"  # Will be converted to list
    
    # AWS
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "pdf-redaction-bucket"
    
    # ClickHouse
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_database: str = "pdf_redaction"
    clickhouse_user: str = "default"
    clickhouse_password: Optional[str] = None
    clickhouse_secure: Optional[str] = None
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    @validator('max_file_size_mb')
    def validate_file_size(cls, v):
        if v <= 0 or v > 100:
            raise ValueError('File size must be between 1 and 100 MB')
        return v
    
    @validator('allowed_extensions')
    def validate_extensions(cls, v):
        if isinstance(v, str):
            v = [v]
        if not v or 'pdf' not in v:
            raise ValueError('PDF must be in allowed extensions')
        return v
    
    @property
    def max_file_size_bytes(self) -> int:
        """Convert MB to bytes"""
        return self.max_file_size_mb * 1024 * 1024
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
