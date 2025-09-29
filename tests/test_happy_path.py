"""
End-to-end happy path test: upload then process
"""

import io
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.combined_app import app


def _minimal_pdf_bytes() -> bytes:
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


client = TestClient(app)


@patch("app.combined_app.clickhouse_client")
@patch("app.combined_app.pdf_processor")
@patch("app.combined_app.s3_service")
def test_happy_upload_then_process(mock_s3, mock_pdf, mock_clickhouse):
    # Mock S3
    mock_s3.generate_file_key.return_value = "uploads/test/test.pdf"
    mock_s3.generate_redacted_file_key.return_value = "redacted/test.pdf"
    mock_s3.upload_file.return_value = True
    mock_s3.download_file.return_value = b"pdf-bytes"

    # Mock PDF processor result (now returns redacted_bytes, no S3/DB)
    mock_pdf.process_pdf.return_value = {
        "file_id": "test-file-id",
        "total_pages": 1,
        "redaction_blocks": [],
        "processing_time_seconds": 0.12,
        "summary": {
            "total_redactions": 0,
            "redactions_by_reason": {},
            "pages_affected": 0,
            "confidence_scores": {"average": 0.0, "minimum": 0.0, "maximum": 0.0},
        },
        "created_at": "2025-01-01T00:00:00",
        "redacted_bytes": b"redacted-pdf-content",
    }

    # Mock ClickHouse insertions to no-op
    mock_clickhouse.insert_redaction_result.return_value = None
    mock_clickhouse.insert_redaction_blocks.return_value = None
    mock_clickhouse.insert_metrics.return_value = None

    # 1) Upload
    files = {"file": ("test.pdf", io.BytesIO(_minimal_pdf_bytes()), "application/pdf")}
    upload_resp = client.post("/upload", files=files)
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    assert "file_id" in upload_data
    assert upload_data["s3_key"] == "uploads/test/test.pdf"

    # 2) Process using new JSON body format
    process_body = {
        "file_id": upload_data["file_id"],
        "bucket": upload_data["s3_bucket"],
        "key": upload_data["s3_key"],
    }
    process_resp = client.post("/process", json=process_body)
    assert process_resp.status_code == 200
    result = process_resp.json()
    assert result["file_id"] == mock_pdf.process_pdf.return_value["file_id"]
    assert result["total_pages"] == 1

    # Ensure S3 upload and DB writes were attempted
    assert mock_s3.upload_file.called  # Should upload redacted bytes
    assert mock_clickhouse.insert_redaction_result.called
    assert mock_clickhouse.insert_redaction_blocks.called
    assert mock_clickhouse.insert_metrics.called


