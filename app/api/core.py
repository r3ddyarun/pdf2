"""
Core API endpoints (health, root, etc.)
"""

import logging
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["core"])


@router.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with API information"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PDF Redaction Service API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .header { color: #2c3e50; }
            .endpoint { background: #f8f9fa; padding: 10px; margin: 5px 0; border-left: 4px solid #007bff; }
            .method { font-weight: bold; color: #28a745; }
        </style>
    </head>
    <body>
        <h1 class="header">🔒 PDF Redaction Service API</h1>
        <p>Welcome to the PDF Redaction Service API. This service processes PDF files to detect and redact sensitive information.</p>
        
        <h2>Available Endpoints:</h2>
        
        <div class="endpoint">
            <span class="method">GET</span> <code>/health</code> - Health check endpoint
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span> <code>/upload</code> - Upload PDF file for processing
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> <code>/upload-url/{filename}</code> - Get presigned URL for direct upload
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span> <code>/process</code> - Process uploaded PDF file
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span> <code>/process/{file_id}</code> - Process file by ID
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> <code>/download/{file_id}</code> - Download redacted file by ID
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span> <code>/download</code> - Download file from S3
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> <code>/results/{file_id}</code> - Get processing results
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> <code>/stats</code> - Get processing statistics
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> <code>/ui</code> - Streamlit UI interface
        </div>
        
        <h2>Documentation:</h2>
        <p>API documentation is available at <a href="/docs">/docs</a> (Swagger UI) or <a href="/redoc">/redoc</a> (ReDoc).</p>
        
        <h2>Features:</h2>
        <ul>
            <li>🔍 Automatic detection of sensitive information (emails, phones, credit cards, SSNs)</li>
            <li>🖍️ Redaction of detected content</li>
            <li>📊 Detailed processing statistics and analytics</li>
            <li>☁️ S3 integration for file storage</li>
            <li>📈 ClickHouse database for analytics</li>
            <li>🎨 Streamlit web interface</li>
        </ul>
    </body>
    </html>
    """


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "pdf-redaction-api"}
