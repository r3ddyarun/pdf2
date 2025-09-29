"""
API endpoint tests for PDF Redaction Service
"""

import pytest
import io
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.models import RedactionReason

client = TestClient(app)


class TestHealthEndpoints:
    """Test health and status endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "status" in data
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestFileUpload:
    """Test file upload functionality"""
    
    def create_test_pdf(self) -> bytes:
        """Create a simple test PDF content"""
        # This is a minimal PDF content for testing
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
    
    @patch('app.main.s3_service')
    def test_upload_valid_pdf(self, mock_s3_service):
        """Test uploading a valid PDF file"""
        # Mock S3 service
        mock_s3_service.generate_file_key.return_value = "test/path/test.pdf"
        mock_s3_service.upload_file.return_value = True
        mock_s3_service.s3_bucket_name = "test-bucket"
        
        # Create test file
        test_pdf = self.create_test_pdf()
        
        # Upload file
        files = {"file": ("test.pdf", io.BytesIO(test_pdf), "application/pdf")}
        response = client.post("/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert "file_id" in data
        assert data["filename"] == "test.pdf"
        assert data["file_size"] == len(test_pdf)
        assert data["s3_bucket"] == "test-bucket"
        assert data["s3_key"] == "test/path/test.pdf"
    
    def test_upload_invalid_file_type(self):
        """Test uploading non-PDF file"""
        files = {"file": ("test.txt", io.BytesIO(b"test content"), "text/plain")}
        response = client.post("/upload", files=files)
        
        assert response.status_code == 400
        assert "Only PDF files are allowed" in response.json()["detail"]
    
    def test_upload_file_too_large(self):
        """Test uploading file that exceeds size limit"""
        # Create large content (simulate > 50MB)
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        
        files = {"file": ("large.pdf", io.BytesIO(large_content), "application/pdf")}
        response = client.post("/upload", files=files)
        
        assert response.status_code == 413
        assert "File size exceeds maximum allowed size" in response.json()["detail"]


class TestFileProcessing:
    """Test file processing functionality"""
    
    @patch('app.main.s3_service')
    @patch('app.main.pdf_processor')
    @patch('app.main.clickhouse_client')
    def test_process_file_success(self, mock_clickhouse, mock_processor, mock_s3):
        """Test successful file processing"""
        # Mock S3 service
        mock_s3.download_file.return_value = b"test pdf content"
        
        # Mock PDF processor
        mock_result = {
            "file_id": "test-file-id",
            "redacted_file_id": "redacted-test-file-id",
            "redacted_s3_bucket": "test-bucket",
            "redacted_s3_key": "redacted/test.pdf",
            "total_pages": 1,
            "redaction_blocks": [],
            "processing_time_seconds": 1.5,
            "summary": {
                "total_redactions": 0,
                "redactions_by_reason": {},
                "pages_affected": 0,
                "confidence_scores": {"average": 0.0, "minimum": 0.0, "maximum": 0.0}
            },
            "created_at": "2023-01-01T00:00:00"
        }
        mock_processor.process_pdf.return_value = mock_result
        
        # Mock ClickHouse client
        mock_clickhouse.insert_redaction_result.return_value = None
        mock_clickhouse.insert_redaction_blocks.return_value = None
        mock_clickhouse.insert_metrics.return_value = None
        
        # Process file
        data = {"bucket": "test-bucket", "key": "test.pdf"}
        response = client.post("/process/test-file-id", json=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["file_id"] == "test-file-id"
        assert result["total_pages"] == 1
    
    @patch('app.main.s3_service')
    def test_process_file_not_found(self, mock_s3):
        """Test processing non-existent file"""
        # Mock S3 service to return None (file not found)
        mock_s3.download_file.return_value = None
        
        data = {"bucket": "test-bucket", "key": "nonexistent.pdf"}
        response = client.post("/process/test-file-id", json=data)
        
        assert response.status_code == 404
        assert "File not found in S3" in response.json()["detail"]


class TestFileDownload:
    """Test file download functionality"""
    
    @patch('app.main.s3_service')
    def test_download_file_success(self, mock_s3):
        """Test successful file download"""
        # Mock S3 service
        test_content = b"test pdf content"
        mock_s3.download_file.return_value = test_content
        
        # Download file
        data = {"bucket": "test-bucket", "key": "test.pdf"}
        response = client.post("/download", json=data)
        
        assert response.status_code == 200
        assert response.content == test_content
        assert response.headers["content-type"] == "application/pdf"
    
    @patch('app.main.s3_service')
    def test_download_file_not_found(self, mock_s3):
        """Test downloading non-existent file"""
        # Mock S3 service to return None (file not found)
        mock_s3.download_file.return_value = None
        
        data = {"bucket": "test-bucket", "key": "nonexistent.pdf"}
        response = client.post("/download", json=data)
        
        assert response.status_code == 404
        assert "File not found" in response.json()["detail"]


class TestResults:
    """Test results retrieval"""
    
    @patch('app.main.clickhouse_client')
    def test_get_results_success(self, mock_clickhouse):
        """Test successful results retrieval"""
        # Mock ClickHouse client
        mock_file_history = {
            "file_id": "test-file-id",
            "filename": "test.pdf",
            "total_pages": 1,
            "total_redactions": 2
        }
        mock_redaction_blocks = [
            {
                "page_number": 1,
                "reason": "email",
                "confidence": 0.95,
                "original_text": "test@example.com"
            }
        ]
        
        mock_clickhouse.get_file_history.return_value = mock_file_history
        mock_clickhouse.get_redaction_blocks.return_value = mock_redaction_blocks
        
        # Get results
        response = client.get("/results/test-file-id")
        
        assert response.status_code == 200
        data = response.json()
        assert data["file_id"] == "test-file-id"
        assert data["file_history"] == mock_file_history
        assert len(data["redaction_blocks"]) == 1
    
    @patch('app.main.clickhouse_client')
    def test_get_results_not_found(self, mock_clickhouse):
        """Test results retrieval for non-existent file"""
        # Mock ClickHouse client to return None
        mock_clickhouse.get_file_history.return_value = None
        
        response = client.get("/results/nonexistent-file-id")
        
        assert response.status_code == 404
        assert "File results not found" in response.json()["detail"]


class TestStatistics:
    """Test statistics endpoints"""
    
    @patch('app.main.clickhouse_client')
    def test_get_stats_success(self, mock_clickhouse):
        """Test successful statistics retrieval"""
        # Mock ClickHouse client
        mock_stats = {
            "total_files": 100,
            "avg_processing_time": 2.5,
            "total_redactions": 500,
            "successful_files": 95,
            "failed_files": 5
        }
        mock_clickhouse.get_processing_stats.return_value = mock_stats
        
        # Get statistics
        response = client.get("/stats?hours=24")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 100
        assert data["avg_processing_time"] == 2.5


class TestUploadURL:
    """Test presigned URL generation"""
    
    @patch('app.main.s3_service')
    def test_get_upload_url_success(self, mock_s3):
        """Test successful upload URL generation"""
        # Mock S3 service
        mock_s3.generate_file_key.return_value = "test/path/test.pdf"
        mock_s3.generate_presigned_url.return_value = "https://presigned-url.com"
        mock_s3.s3_bucket_name = "test-bucket"
        
        # Get upload URL
        response = client.get("/upload-url/test.pdf")
        
        assert response.status_code == 200
        data = response.json()
        assert "upload_url" in data
        assert data["s3_key"] == "test/path/test.pdf"
        assert data["bucket"] == "test-bucket"
        assert data["expires_in"] == 3600
    
    def test_get_upload_url_invalid_file_type(self):
        """Test upload URL generation for non-PDF file"""
        response = client.get("/upload-url/test.txt")
        
        assert response.status_code == 400
        assert "Only PDF files are allowed" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__])
