#!/usr/bin/env python3
"""
Debug script to isolate the process API issue
"""

import requests
import json
import os

API_BASE_URL = "http://localhost:8000"
TEST_PDF_PATH = "docs/pdfredact.pdf"

def debug_process():
    """Debug the process API step by step"""
    
    print("🔍 Debugging Process API")
    print("=" * 40)
    
    # Step 1: Upload file
    print("1. Uploading file...")
    with open(TEST_PDF_PATH, 'rb') as f:
        files = {'file': (os.path.basename(TEST_PDF_PATH), f, 'application/pdf')}
        upload_response = requests.post(f"{API_BASE_URL}/upload", files=files)
    
    if upload_response.status_code != 200:
        print(f"❌ Upload failed: {upload_response.text}")
        return
    
    upload_data = upload_response.json()
    print(f"✅ Upload successful: {upload_data['file_id']}")
    
    # Step 2: Test S3 download directly
    print("\n2. Testing S3 download...")
    try:
        from app.services.s3_service import s3_service
        file_content = s3_service.download_file(upload_data['s3_key'])
        if file_content:
            print(f"✅ S3 download successful: {len(file_content)} bytes")
        else:
            print("❌ S3 download failed")
            return
    except Exception as e:
        print(f"❌ S3 download error: {e}")
        return
    
    # Step 3: Test PDF processing directly
    print("\n3. Testing PDF processing...")
    try:
        from app.services.pdf_processor import pdf_processor
        result = pdf_processor.process_pdf(file_content, upload_data['file_id'])
        print(f"✅ PDF processing successful: {result['total_pages']} pages")
    except Exception as e:
        print(f"❌ PDF processing error: {e}")
        return
    
    # Step 4: Test database operations
    print("\n4. Testing database operations...")
    try:
        from app.database.clickhouse_client import clickhouse_client
        from datetime import datetime
        
        # Test inserting metrics
        metrics_data = {
            'timestamp': datetime.utcnow(),
            'file_id': upload_data['file_id'],
            'processing_time': 1.0,
            'file_size': len(file_content),
            'redaction_count': 0,
            'success': 1,
            'error_message': None
        }
        clickhouse_client.insert_metrics(metrics_data)
        print("✅ Database operations successful")
    except Exception as e:
        print(f"❌ Database error: {e}")
        return
    
    # Step 5: Test process API with detailed error
    print("\n5. Testing process API...")
    process_data = {
        "file_id": upload_data["file_id"],
        "bucket": upload_data["s3_bucket"],
        "key": upload_data["s3_key"]
    }
    
    try:
        process_response = requests.post(
            f"{API_BASE_URL}/process",
            json=process_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"Status Code: {process_response.status_code}")
        print(f"Response: {process_response.text}")
        
        if process_response.status_code == 200:
            print("✅ Process API successful!")
        else:
            print("❌ Process API failed")
            
    except Exception as e:
        print(f"❌ Process API error: {e}")

if __name__ == "__main__":
    debug_process()
