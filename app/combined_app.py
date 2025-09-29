"""
Combined FastAPI + Streamlit application
"""

import logging
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import io
import streamlit as st
from streamlit.web import cli as stcli
import sys
import threading
from contextlib import asynccontextmanager
import requests
import pandas as pd
import plotly.express as px

from app.config import settings
from app.models import (
    FileUploadResponse, RedactionResult, ErrorResponse, 
    FileDownloadRequest, MetricsData
)
from app.services.s3_service import s3_service
from app.services.pdf_processor import pdf_processor
from app.database.clickhouse_client import clickhouse_client
from app.middleware.metrics import metrics_middleware
from app.utils.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer(auto_error=False)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Simple authentication - replace with proper auth in production"""
    # For now, accept any token or no token
    # In production, implement proper JWT validation
    return {"user_id": "demo_user", "username": "demo"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting PDF Redaction Service")
    try:
        # Initialize database tables
        clickhouse_client.create_tables()
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down PDF Redaction Service")
    clickhouse_client.close()


# Initialize FastAPI app with lifespan
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise PDF Redaction Service with AI-powered content detection",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add metrics middleware
app.middleware("http")(metrics_middleware)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with file upload interface"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PDF Redaction Service</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f0f2f6;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
            }
            .header {
                text-align: center;
                margin-bottom: 30px;
                padding: 20px;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .upload-section {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .upload-area {
                border: 2px dashed #1f77b4;
                border-radius: 10px;
                padding: 40px;
                text-align: center;
                margin: 20px 0;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .upload-area:hover {
                border-color: #1565c0;
                background-color: #f8f9ff;
            }
            .upload-area.dragover {
                border-color: #1565c0;
                background-color: #f0f7ff;
            }
            .file-input {
                display: none;
            }
            .upload-btn {
                padding: 12px 24px;
                background: #1f77b4;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                cursor: pointer;
                font-size: 16px;
                transition: background-color 0.3s;
            }
            .upload-btn:hover {
                background: #1565c0;
            }
            .upload-btn:disabled {
                background: #ccc;
                cursor: not-allowed;
            }
            .progress-bar {
                width: 100%;
                height: 20px;
                background-color: #f0f0f0;
                border-radius: 10px;
                overflow: hidden;
                margin: 20px 0;
                display: none;
            }
            .progress-fill {
                height: 100%;
                background-color: #1f77b4;
                width: 0%;
                transition: width 0.3s ease;
            }
            .result-section {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-top: 20px;
                display: none;
            }
            .success-message {
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                color: #155724;
                padding: 15px;
                border-radius: 5px;
                margin: 10px 0;
            }
            .error-message {
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                color: #721c24;
                padding: 15px;
                border-radius: 5px;
                margin: 10px 0;
            }
            .nav-links {
                text-align: center;
                margin-top: 20px;
            }
            .nav-link {
                color: #1f77b4;
                text-decoration: none;
                margin: 0 10px;
            }
            .nav-link:hover {
                text-decoration: underline;
            }
            .file-info {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔒 PDF Redaction Service</h1>
                <p>Upload PDF files to automatically detect and redact sensitive information</p>
            </div>
            
            <div class="upload-section">
                <h2>📄 Upload PDF File</h2>
                <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                    <div>
                        <p style="font-size: 18px; margin-bottom: 10px;">📁 Click to select PDF file or drag and drop</p>
                        <p style="color: #666;">Maximum file size: 50MB</p>
                    </div>
                </div>
                
                <input type="file" id="fileInput" class="file-input" accept=".pdf" />
                
                <div class="file-info" id="fileInfo" style="display: none;">
                    <p><strong>Selected file:</strong> <span id="fileName"></span></p>
                    <p><strong>File size:</strong> <span id="fileSize"></span></p>
                </div>
                
                <div class="progress-bar" id="progressBar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                
                <div style="text-align: center;">
                    <button class="upload-btn" id="uploadBtn" onclick="uploadFile()" disabled>
                        🔄 Process PDF
                    </button>
                </div>
            </div>
            
            <div class="result-section" id="resultSection">
                <h3>📊 Processing Results</h3>
                <div id="resultContent"></div>
            </div>
            
            <div class="nav-links">
                <a href="/docs" class="nav-link">📚 API Documentation</a>
                <a href="/health" class="nav-link">💚 Health Check</a>
                <a href="/stats" class="nav-link">📊 Statistics</a>
            </div>
        </div>

        <script>
            let selectedFile = null;
            
            // File input handling
            document.getElementById('fileInput').addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    selectedFile = file;
                    showFileInfo(file);
                    document.getElementById('uploadBtn').disabled = false;
                }
            });
            
            // Drag and drop handling
            const uploadArea = document.querySelector('.upload-area');
            
            uploadArea.addEventListener('dragover', function(e) {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });
            
            uploadArea.addEventListener('dragleave', function(e) {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
            });
            
            uploadArea.addEventListener('drop', function(e) {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    const file = files[0];
                    if (file.type === 'application/pdf') {
                        selectedFile = file;
                        showFileInfo(file);
                        document.getElementById('uploadBtn').disabled = false;
                    } else {
                        alert('Please select a PDF file.');
                    }
                }
            });
            
            function showFileInfo(file) {
                document.getElementById('fileName').textContent = file.name;
                document.getElementById('fileSize').textContent = formatFileSize(file.size);
                document.getElementById('fileInfo').style.display = 'block';
            }
            
            function formatFileSize(bytes) {
                if (bytes === 0) return '0 Bytes';
                const k = 1024;
                const sizes = ['Bytes', 'KB', 'MB', 'GB'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
            }
            
            async function uploadFile() {
                if (!selectedFile) {
                    alert('Please select a file first.');
                    return;
                }
                
                const uploadBtn = document.getElementById('uploadBtn');
                const progressBar = document.getElementById('progressBar');
                const progressFill = document.getElementById('progressFill');
                const resultSection = document.getElementById('resultSection');
                const resultContent = document.getElementById('resultContent');
                
                // Reset UI
                uploadBtn.disabled = true;
                uploadBtn.textContent = '🔄 Processing...';
                progressBar.style.display = 'block';
                progressFill.style.width = '0%';
                resultSection.style.display = 'none';
                
                try {
                    // Upload file
                    const formData = new FormData();
                    formData.append('file', selectedFile);
                    
                    progressFill.style.width = '30%';
                    
                    const uploadResponse = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!uploadResponse.ok) {
                        throw new Error(`Upload failed: ${uploadResponse.statusText}`);
                    }
                    
                    const uploadResult = await uploadResponse.json();
                    progressFill.style.width = '60%';
                    
                    // Process file
                    const processResponse = await fetch('/process', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            file_id: uploadResult.file_id,
                            bucket: uploadResult.s3_bucket,
                            key: uploadResult.s3_key
                        })
                    });
                    
                    if (!processResponse.ok) {
                        throw new Error(`Processing failed: ${processResponse.statusText}`);
                    }
                    
                    const processResult = await processResponse.json();
                    progressFill.style.width = '100%';
                    
                    // Show results
                    showResults(processResult);
                    
                } catch (error) {
                    showError('Processing failed: ' + error.message);
                } finally {
                    uploadBtn.disabled = false;
                    uploadBtn.textContent = '🔄 Process PDF';
                }
            }
            
            function showResults(result) {
                const resultContent = document.getElementById('resultContent');
                const resultSection = document.getElementById('resultSection');
                
                let html = '<div class="success-message">✅ File processed successfully!</div>';
                
                html += '<div class="file-info">';
                html += '<h4>📋 Processing Summary</h4>';
                html += `<p><strong>Total pages:</strong> ${result.total_pages}</p>`;
                html += `<p><strong>Processing time:</strong> ${result.processing_time_seconds.toFixed(2)}s</p>`;
                html += `<p><strong>Total redactions:</strong> ${result.total_redactions}</p>`;
                html += '</div>';
                
                if (result.redactions_by_reason && Object.keys(result.redactions_by_reason).length > 0) {
                    html += '<div class="file-info">';
                    html += '<h4>🔍 Redaction Details</h4>';
                    for (const [reason, count] of Object.entries(result.redactions_by_reason)) {
                        html += `<p><strong>${reason}:</strong> ${count} redactions</p>`;
                    }
                    html += '</div>';
                }
                
                if (result.redacted_s3_bucket && result.redacted_s3_key) {
                    html += '<div class="file-info">';
                    html += '<h4>📥 Download</h4>';
                    html += `<a href="/download/${result.file_id}" class="upload-btn" style="display: inline-block; text-decoration: none;">📄 Download Redacted PDF</a>`;
                    html += '</div>';
                }
                
                resultContent.innerHTML = html;
                resultSection.style.display = 'block';
            }
            
            function showError(message) {
                const resultContent = document.getElementById('resultContent');
                const resultSection = document.getElementById('resultSection');
                
                resultContent.innerHTML = `<div class="error-message">❌ ${message}</div>`;
                resultSection.style.display = 'block';
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}


@app.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload PDF file to S3 and return file information"""
    
    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Check file size
    file_content = await file.read()
    if len(file_content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {settings.max_file_size_mb}MB"
        )
    
    try:
        # Generate unique file ID and S3 key
        file_id = str(uuid.uuid4())
        s3_key = s3_service.generate_file_key(file.filename)
        
        # Upload to S3
        upload_success = s3_service.upload_file(file_content, s3_key)
        
        if not upload_success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to S3"
            )
        
        # Create response
        response = FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            file_size=len(file_content),
            s3_bucket=settings.s3_bucket_name,
            s3_key=s3_key
        )
        
        logger.info(f"File uploaded successfully: {file_id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file upload"
        )


@app.get("/upload-url/{filename}")
async def get_upload_url(
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Get presigned URL for direct S3 upload"""
    
    if not filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    try:
        s3_key = s3_service.generate_file_key(filename)
        presigned_url = s3_service.generate_presigned_url(s3_key, 'put_object')
        
        if not presigned_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate upload URL"
            )
        
        return {
            "upload_url": presigned_url,
            "s3_key": s3_key,
            "bucket": settings.s3_bucket_name,
            "expires_in": 3600
        }
        
    except Exception as e:
        logger.error(f"Failed to generate upload URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/process", response_model=RedactionResult)
async def process_file(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """Process PDF file for content detection and redaction"""
    
    start_time = time.time()
    
    try:
        file_id = request.get("file_id")
        if not file_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="file_id is required"
            )
        
        # Get S3 information from request or retrieve from database
        bucket = request.get("bucket")
        key = request.get("key")
        
        if not bucket or not key:
            # Try to get from database if not provided
            file_history = clickhouse_client.get_file_history(file_id)
            if not file_history:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File information not found"
                )
            # Use the most recent file info
            latest_file = file_history[0]
            bucket = latest_file.get("s3_bucket")
            key = latest_file.get("s3_key")
        
        # Download file from S3
        file_content = s3_service.download_file(key)
        
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found in S3"
            )
        
        # Process PDF (no side effects in processor)
        result = pdf_processor.process_pdf(file_content, file_id)

        # Upload redacted bytes to S3
        redacted_key = s3_service.generate_redacted_file_key(f"{file_id}.pdf")
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
        # Build API response
        api_response = {
            'file_id': file_id,
            'redacted_file_id': f"redacted_{file_id}",
            'redacted_s3_bucket': settings.s3_bucket_name,
            'redacted_s3_key': redacted_key,
            'total_pages': result['total_pages'],
            'redaction_blocks': result['redaction_blocks'],
            'processing_time_seconds': result['processing_time_seconds'],
            'summary': result['summary'],
            'created_at': result['created_at'],
        }
        return RedactionResult(**api_response)
        
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


@app.post("/process/{file_id}", response_model=RedactionResult)
async def process_file_by_id(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Process PDF file by file_id only (retrieves S3 info from database)"""
    
    start_time = time.time()
    
    try:
        # Get file information from database
        file_history = clickhouse_client.get_file_history(file_id)
        if not file_history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Use the most recent file info
        latest_file = file_history[0]
        bucket = latest_file.get("s3_bucket")
        key = latest_file.get("s3_key")
        
        if not bucket or not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File S3 information not found"
            )
        
        # Download file from S3
        file_content = s3_service.download_file(key)
        
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found in S3"
            )
        
        # Process PDF (no side effects in processor)
        result = pdf_processor.process_pdf(file_content, file_id)

        # Upload redacted bytes to S3
        redacted_key = s3_service.generate_redacted_file_key(f"{file_id}.pdf")
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
        api_response = {
            'file_id': file_id,
            'redacted_file_id': f"redacted_{file_id}",
            'redacted_s3_bucket': settings.s3_bucket_name,
            'redacted_s3_key': redacted_key,
            'total_pages': result['total_pages'],
            'redaction_blocks': result['redaction_blocks'],
            'processing_time_seconds': result['processing_time_seconds'],
            'summary': result['summary'],
            'created_at': result['created_at'],
        }
        return RedactionResult(**api_response)
        
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


@app.get("/download/{file_id}")
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


@app.post("/download")
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


@app.get("/results/{file_id}")
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
        
        # Get redaction blocks
        redaction_blocks = clickhouse_client.get_redaction_blocks(file_id)
        
        return {
            "file_id": file_id,
            "file_history": file_history,
            "redaction_blocks": redaction_blocks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get results for file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/stats")
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


# Streamlit app function
def create_streamlit_app():
    """Create and configure Streamlit app"""
    
    # Configure Streamlit page
    st.set_page_config(
        page_title="PDF Redaction Service",
        page_icon="🔒",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # API Configuration
    API_BASE_URL = f"http://localhost:{settings.port}"
    
    # Custom CSS
    st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }
        .section-header {
            font-size: 1.5rem;
            font-weight: bold;
            color: #2c3e50;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        .success-message {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 1rem;
            border-radius: 0.25rem;
            margin: 1rem 0;
        }
        .error-message {
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            padding: 1rem;
            border-radius: 0.25rem;
            margin: 1rem 0;
        }
        .info-box {
            background-color: #e7f3ff;
            border: 1px solid #b8daff;
            color: #004085;
            padding: 1rem;
            border-radius: 0.25rem;
            margin: 1rem 0;
        }
    </style>
    """, unsafe_allow_html=True)
    
    def make_api_request(method: str, endpoint: str, data: Optional[Dict] = None, files: Optional[Dict] = None) -> Optional[Dict]:
        """Make API request to the backend"""
        try:
            url = f"{API_BASE_URL}{endpoint}"
            
            if method.upper() == "GET":
                response = requests.get(url)
            elif method.upper() == "POST":
                if files:
                    response = requests.post(url, files=files)
                else:
                    response = requests.post(url, json=data)
            else:
                st.error(f"Unsupported HTTP method: {method}")
                return None
            
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"API Error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to the API server. Please ensure the backend is running.")
            return None
        except Exception as e:
            st.error(f"Error making API request: {str(e)}")
            return None
    
    def display_file_upload():
        """Display file upload interface"""
        st.markdown('<div class="section-header">📄 Upload PDF File</div>', unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            help="Upload a PDF file for content detection and redaction. Maximum file size: 50MB"
        )
        
        if uploaded_file is not None:
            # Display file info
            file_details = {
                "Filename": uploaded_file.name,
                "File size": f"{uploaded_file.size / 1024 / 1024:.2f} MB",
                "File type": uploaded_file.type
            }
            
            st.info("**File Information:**")
            for key, value in file_details.items():
                st.write(f"**{key}:** {value}")
            
            # Upload button
            if st.button("Upload and Process", type="primary"):
                with st.spinner("Uploading file..."):
                    # Upload file
                    files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                    upload_response = make_api_request("POST", "/upload", files=files)
                    
                    if upload_response:
                        st.session_state.upload_response = upload_response
                        
                        # Process file
                        with st.spinner("Processing PDF for content detection..."):
                            process_data = {
                                "file_id": upload_response["file_id"],
                                "bucket": upload_response["s3_bucket"],
                                "key": upload_response["s3_key"]
                            }
                            process_response = make_api_request("POST", "/process", data=process_data)
                            
                            if process_response:
                                st.session_state.process_response = process_response
                                st.success("File processed successfully!")
                                st.rerun()
    
    def display_results():
        """Display processing results"""
        if "process_response" not in st.session_state:
            return
        
        st.markdown('<div class="section-header">📊 Processing Results</div>', unsafe_allow_html=True)
        
        response = st.session_state.process_response
        
        # Debug information (can be removed in production)
        if st.checkbox("Show Debug Information", value=False):
            st.json(response)
        
        # Check if processing was successful
        processing_status = response.get("status", "unknown")
        if processing_status == "error":
            st.error("❌ Processing failed. Please try again.")
            return
        elif processing_status == "success":
            st.success("✅ Processing completed successfully!")
        
        # Summary metrics with safe access
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_pages = response.get("total_pages", 0)
            st.metric("Total Pages", total_pages)
        
        with col2:
            summary = response.get("summary", {})
            total_redactions = summary.get("total_redactions", 0)
            st.metric("Total Redactions", total_redactions)
        
        with col3:
            pages_affected = summary.get("pages_affected", 0)
            st.metric("Pages Affected", pages_affected)
        
        with col4:
            confidence_scores = summary.get("confidence_scores", {})
            avg_confidence = confidence_scores.get("average", 0.0)
            st.metric("Avg Confidence", f"{avg_confidence:.2%}")
        
        # Redactions by reason
        st.markdown("**Redactions by Category:**")
        redactions_by_reason = summary.get("redactions_by_reason", {})
        
        if redactions_by_reason:
            # Format reason names for better display
            formatted_reasons = []
            for reason, count in redactions_by_reason.items():
                # Convert snake_case to Title Case
                formatted_reason = reason.replace('_', ' ').title()
                formatted_reasons.append((formatted_reason, count))
            
            df_reasons = pd.DataFrame(
                formatted_reasons,
                columns=["Reason", "Count"]
            )
            
            # Create pie chart
            fig = px.pie(
                df_reasons, 
                values="Count", 
                names="Reason",
                title="Distribution of Redactions by Type"
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
            
            # Display table
            st.dataframe(df_reasons, use_container_width=True)
        else:
            st.info("No redactions were found in the document.")
        
        # Redaction blocks details
        redaction_blocks = response.get("redaction_blocks", [])
        if redaction_blocks:
            st.markdown("**Detailed Redaction Information:**")
            
            blocks_data = []
            for block in redaction_blocks:
                # Format reason for display
                reason = block.get("reason", "N/A")
                if reason != "N/A":
                    reason = reason.replace('_', ' ').title()
                
                blocks_data.append({
                    "Page": block.get("page_number", "N/A"),
                    "Reason": reason,
                    "Confidence": f"{block.get('confidence', 0):.2%}",
                    "X": f"{block.get('x', 0):.1f}",
                    "Y": f"{block.get('y', 0):.1f}",
                    "Width": f"{block.get('width', 0):.1f}",
                    "Height": f"{block.get('height', 0):.1f}",
                    "Original Text": block.get("original_text", "N/A")
                })
            
            df_blocks = pd.DataFrame(blocks_data)
            st.dataframe(df_blocks, use_container_width=True)
        
        # Download redacted file
        st.markdown("**Download Redacted File:**")
        
        file_id = response.get("file_id", "unknown")
        
        # Create download options
        col1, col2 = st.columns(2)
        
        with col1:
            # Direct download link (simpler approach)
            download_url = f"{API_BASE_URL}/download/{file_id}"
            st.markdown(f"""
            <a href="{download_url}" target="_blank">
                <button style="
                    background-color: #4CAF50;
                    border: none;
                    color: white;
                    padding: 10px 20px;
                    text-align: center;
                    text-decoration: none;
                    display: inline-block;
                    font-size: 16px;
                    margin: 4px 2px;
                    cursor: pointer;
                    border-radius: 4px;
                ">📥 Direct Download</button>
            </a>
            """, unsafe_allow_html=True)
            st.caption("Click to download directly (opens in new tab)")
        
        with col2:
            # Advanced download with validation
            if st.button("📋 Advanced Download", type="secondary"):
                # Check if download data is available
                redacted_bucket = response.get("redacted_s3_bucket")
                redacted_key = response.get("redacted_s3_key")
                
                if not redacted_bucket or not redacted_key:
                    st.warning("⚠️ Redacted file information is not available for download.")
                    return
                
                # Create download button with improved UX
                try:
                    with st.spinner("Preparing download..."):
                        download_data = {
                            "bucket": redacted_bucket,
                            "key": redacted_key
                        }
                        
                        response_download = requests.post(f"{API_BASE_URL}/download", json=download_data)
                        
                        if response_download.status_code == 200:
                            # Generate filename
                            filename = f"redacted_{file_id}.pdf"
                            
                            # Display download button
                            st.download_button(
                                label="📥 Download Redacted PDF",
                                data=response_download.content,
                                file_name=filename,
                                mime="application/pdf",
                                type="primary",
                                help="Click to download the redacted PDF file"
                            )
                            
                            # Show file info
                            file_size = len(response_download.content)
                            st.info(f"📄 File ready for download: {filename} ({file_size:,} bytes)")
                            
                        elif response_download.status_code == 404:
                            st.error("❌ Redacted file not found. The file may have been deleted or moved.")
                        elif response_download.status_code == 500:
                            st.error("❌ Server error occurred while preparing download. Please try again.")
                        else:
                            st.error(f"❌ Download failed with status {response_download.status_code}")
                            
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to the server. Please ensure the backend is running.")
                except requests.exceptions.Timeout:
                    st.error("❌ Download request timed out. Please try again.")
                except Exception as e:
                    st.error(f"❌ Error downloading file: {str(e)}")
        
        st.info("💡 **Tip**: Use 'Direct Download' for quick access, or 'Advanced Download' for validation and detailed information.")
    
    def display_sidebar():
        """Display sidebar with navigation and info"""
        st.sidebar.title("🔒 PDF Redaction Service")
        
        st.sidebar.markdown("### Navigation")
        page = st.sidebar.radio(
            "Select page:",
            ["Upload & Process", "Statistics"]
        )
        
        st.sidebar.markdown("---")
        
        # Service status
        st.sidebar.markdown("### Service Status")
        if st.sidebar.button("Check Health"):
            health = make_api_request("GET", "/health")
            if health:
                st.sidebar.success("✅ Service is healthy")
            else:
                st.sidebar.error("❌ Service is down")
        
        st.sidebar.markdown("---")
        
        # Information
        st.sidebar.markdown("### About")
        st.sidebar.info("""
        This service automatically detects and redacts sensitive information from PDF documents including:
        
        - Email addresses
        - Social Security Numbers
        - Credit card numbers
        - Phone numbers
        - Dates of birth
        - Account numbers
        
        **File Size Limit:** 50MB
        **Supported Format:** PDF only
        """)
        
        return page
    
    def main():
        """Main Streamlit application function"""
        st.markdown('<div class="main-header">🔒 PDF Redaction Service</div>', unsafe_allow_html=True)
        
        # Display sidebar and get selected page
        page = display_sidebar()
        
        # Display appropriate page content
        if page == "Upload & Process":
            display_file_upload()
            
            # Clear session button
            if st.button("Clear Session", help="Clear all uploaded files and results"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
            
            display_results()
        
        elif page == "Statistics":
            st.markdown('<div class="section-header">📈 Processing Statistics</div>', unsafe_allow_html=True)
            
            # Time range selector
            time_range = st.selectbox(
                "Select time range:",
                ["Last 24 hours", "Last 7 days", "Last 30 days"],
                key="time_range"
            )
            
            hours_map = {"Last 24 hours": 24, "Last 7 days": 168, "Last 30 days": 720}
            hours = hours_map[time_range]
            
            if st.button("Refresh Statistics"):
                with st.spinner("Loading statistics..."):
                    stats = make_api_request("GET", f"/stats?hours={hours}")
                    
                    if stats:
                        st.session_state.stats = stats
                        st.rerun()
            
            if "stats" in st.session_state:
                stats = st.session_state.stats
                
                # Display metrics
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.metric("Total Files", stats.get("total_files", 0))
                
                with col2:
                    st.metric("Successful", stats.get("successful_files", 0))
                
                with col3:
                    st.metric("Failed", stats.get("failed_files", 0))
                
                with col4:
                    avg_time = stats.get("avg_processing_time", 0)
                    st.metric("Avg Processing Time", f"{avg_time:.2f}s" if avg_time else "N/A")
                
                with col5:
                    st.metric("Total Redactions", stats.get("total_redactions", 0))
    
    return main


# Create Streamlit app instance
streamlit_app = create_streamlit_app()


@app.get("/ui")
async def streamlit_ui():
    """Redirect to Streamlit UI"""
    # For now, redirect to the main page with instructions
    # In a real deployment, you'd run Streamlit on a separate port
    return {
        "message": "Streamlit UI is integrated into the main interface",
        "access_url": "/",
        "api_docs": "/docs",
        "note": "The Streamlit functionality is available through the main interface at http://localhost:8000"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.combined_app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )
