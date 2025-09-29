"""
Pytest configuration and fixtures
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """FastAPI test client fixture"""
    return TestClient(app)


@pytest.fixture
def mock_s3_service():
    """Mock S3 service fixture"""
    with patch('app.services.s3_service.s3_service') as mock:
        mock.generate_file_key.return_value = "test/path/test.pdf"
        mock.generate_presigned_url.return_value = "https://presigned-url.com"
        mock.upload_file.return_value = True
        mock.download_file.return_value = b"test file content"
        mock.file_exists.return_value = True
        mock.s3_bucket_name = "test-bucket"
        yield mock


@pytest.fixture
def mock_clickhouse_client():
    """Mock ClickHouse client fixture"""
    with patch('app.database.clickhouse_client.clickhouse_client') as mock:
        mock.create_tables.return_value = None
        mock.insert_redaction_result.return_value = None
        mock.insert_redaction_blocks.return_value = None
        mock.insert_metrics.return_value = None
        mock.get_file_history.return_value = {
            "file_id": "test-file-id",
            "filename": "test.pdf",
            "total_pages": 1,
            "total_redactions": 2
        }
        mock.get_redaction_blocks.return_value = []
        mock.get_processing_stats.return_value = {
            "total_files": 100,
            "avg_processing_time": 2.5,
            "total_redactions": 500,
            "successful_files": 95,
            "failed_files": 5
        }
        mock.close.return_value = None
        yield mock


@pytest.fixture
def mock_pdf_processor():
    """Mock PDF processor fixture"""
    with patch('app.services.pdf_processor.pdf_processor') as mock:
        mock.process_pdf.return_value = {
            "file_id": "test-file-id",
            "total_pages": 1,
            "redaction_blocks": [],
            "processing_time_seconds": 1.5,
            "summary": {
                "total_redactions": 0,
                "redactions_by_reason": {},
                "pages_affected": 0,
                "confidence_scores": {"average": 0.0, "minimum": 0.0, "maximum": 0.0}
            },
            "created_at": "2023-01-01T00:00:00",
            "redacted_bytes": b"redacted-pdf-content"
        }
        yield mock


@pytest.fixture
def sample_pdf_content():
    """Sample PDF content for testing"""
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Test PDF Content) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
300
%%EOF"""


@pytest.fixture
def temp_file():
    """Temporary file fixture"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as f:
        yield f.name
    os.unlink(f.name)


@pytest.fixture(autouse=True)
def mock_aws_credentials():
    """Mock AWS credentials for all tests"""
    with patch.dict(os.environ, {
        'AWS_ACCESS_KEY_ID': 'test-access-key',
        'AWS_SECRET_ACCESS_KEY': 'test-secret-key',
        'AWS_REGION': 'us-east-1',
        'S3_BUCKET_NAME': 'test-bucket'
    }):
        yield


@pytest.fixture(autouse=True)
def mock_clickhouse_config():
    """Mock ClickHouse configuration for all tests"""
    with patch.dict(os.environ, {
        'CLICKHOUSE_HOST': 'localhost',
        'CLICKHOUSE_PORT': '9000',
        'CLICKHOUSE_DATABASE': 'test_db',
        'CLICKHOUSE_USER': 'test_user',
        'CLICKHOUSE_PASSWORD': 'test_password'
    }):
        yield


@pytest.fixture
def mock_settings():
    """Mock application settings"""
    with patch('app.config.settings') as mock:
        mock.app_name = "Test PDF Redaction Service"
        mock.app_version = "1.0.0"
        mock.debug = True
        mock.log_level = "INFO"
        mock.host = "0.0.0.0"
        mock.port = 8000
        mock.reload = False
        mock.max_file_size_mb = 50
        mock.max_file_size_bytes = 50 * 1024 * 1024
        mock.allowed_extensions = ["pdf"]
        mock.aws_access_key_id = "test-access-key"
        mock.aws_secret_access_key = "test-secret-key"
        mock.aws_region = "us-east-1"
        mock.s3_bucket_name = "test-bucket"
        mock.clickhouse_host = "localhost"
        mock.clickhouse_port = 9000
        mock.clickhouse_database = "test_db"
        mock.clickhouse_user = "test_user"
        mock.clickhouse_password = "test_password"
        mock.secret_key = "test-secret-key"
        mock.algorithm = "HS256"
        mock.access_token_expire_minutes = 30
        mock.enable_metrics = True
        mock.metrics_port = 9090
        yield mock
