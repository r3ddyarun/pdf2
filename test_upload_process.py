#!/usr/bin/env python3
"""
Test script to verify upload and process API integration
"""

import requests
import json
import time
import os
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_PDF_PATH = "docs/pdfredact.pdf"  # Use the existing test PDF

def test_upload_and_process():
    """Test the complete upload and process workflow"""
    
    print("🧪 Testing Upload and Process API Integration")
    print("=" * 50)
    
    # Check if test PDF exists
    if not os.path.exists(TEST_PDF_PATH):
        print(f"❌ Test PDF not found at {TEST_PDF_PATH}")
        return False
    
    try:
        # Step 1: Upload file
        print("📤 Step 1: Uploading PDF file...")
        with open(TEST_PDF_PATH, 'rb') as f:
            files = {'file': (os.path.basename(TEST_PDF_PATH), f, 'application/pdf')}
            upload_response = requests.post(f"{API_BASE_URL}/upload", files=files)
        
        if upload_response.status_code != 200:
            print(f"❌ Upload failed: {upload_response.status_code} - {upload_response.text}")
            return False
        
        upload_data = upload_response.json()
        print(f"✅ Upload successful!")
        print(f"   File ID: {upload_data['file_id']}")
        print(f"   S3 Bucket: {upload_data['s3_bucket']}")
        print(f"   S3 Key: {upload_data['s3_key']}")
        
        # Step 2: Process file using the new process API
        print("\n🔄 Step 2: Processing PDF file...")
        process_data = {
            "file_id": upload_data["file_id"],
            "bucket": upload_data["s3_bucket"],
            "key": upload_data["s3_key"]
        }
        
        process_response = requests.post(
            f"{API_BASE_URL}/process",
            json=process_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if process_response.status_code != 200:
            print(f"❌ Process failed: {process_response.status_code} - {process_response.text}")
            print(f"   Request data: {json.dumps(process_data, indent=2)}")
            return False
        
        process_data = process_response.json()
        print(f"✅ Processing successful!")
        print(f"   Total pages: {process_data['total_pages']}")
        print(f"   Total redactions: {process_data['summary']['total_redactions']}")
        print(f"   Processing time: {process_data['processing_time_seconds']:.2f}s")
        
        # Step 3: Test alternative process endpoint (by file_id only)
        print("\n🔄 Step 3: Testing process by file_id only...")
        process_by_id_response = requests.post(f"{API_BASE_URL}/process/{upload_data['file_id']}")
        
        if process_by_id_response.status_code != 200:
            print(f"❌ Process by ID failed: {process_by_id_response.status_code} - {process_by_id_response.text}")
            return False
        
        print("✅ Process by file_id successful!")
        
        # Step 4: Get results
        print("\n📊 Step 4: Getting processing results...")
        results_response = requests.get(f"{API_BASE_URL}/results/{upload_data['file_id']}")
        
        if results_response.status_code == 200:
            results_data = results_response.json()
            print(f"✅ Results retrieved successfully!")
            print(f"   File history entries: {len(results_data.get('file_history', []))}")
            print(f"   Redaction blocks: {len(results_data.get('redaction_blocks', []))}")
        else:
            print(f"⚠️  Results retrieval failed: {results_response.status_code}")
        
        print("\n🎉 All tests passed! Upload and process integration is working correctly.")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server. Make sure the server is running on port 8000.")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

def test_health_check():
    """Test health check endpoint"""
    print("🏥 Testing health check...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

if __name__ == "__main__":
    print("Starting API Integration Tests")
    print("=" * 50)
    
    # Test health check first
    if not test_health_check():
        print("\n❌ Health check failed. Please start the server first.")
        exit(1)
    
    print()
    
    # Test upload and process
    success = test_upload_and_process()
    
    if success:
        print("\n✅ All tests completed successfully!")
        exit(0)
    else:
        print("\n❌ Some tests failed!")
        exit(1)
