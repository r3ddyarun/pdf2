#!/usr/bin/env python3
"""
Demo script to show the combined FastAPI + Streamlit PDF Redaction Service
"""

import requests
import json
import time

def demo_api():
    """Demonstrate the API functionality"""
    base_url = "http://localhost:8000"
    
    print("🔒 PDF Redaction Service - API Demo")
    print("=" * 50)
    
    # Health check
    print("1. Checking service health...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Service is healthy")
            print(f"   Response: {response.json()}")
        else:
            print("❌ Service health check failed")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to service. Please start the server first.")
        print("   Run: python start_combined.py")
        return
    
    print()
    
    # Get statistics
    print("2. Getting processing statistics...")
    try:
        response = requests.get(f"{base_url}/stats")
        if response.status_code == 200:
            stats = response.json()
            print("✅ Statistics retrieved")
            print(f"   Stats: {json.dumps(stats, indent=2)}")
        else:
            print("❌ Failed to get statistics")
    except Exception as e:
        print(f"❌ Error getting statistics: {e}")
    
    print()
    
    # Test upload URL generation
    print("3. Testing upload URL generation...")
    try:
        response = requests.get(f"{base_url}/upload-url/test.pdf")
        if response.status_code == 200:
            upload_data = response.json()
            print("✅ Upload URL generated")
            print(f"   Bucket: {upload_data['bucket']}")
            print(f"   Key: {upload_data['s3_key']}")
            print(f"   Expires in: {upload_data['expires_in']} seconds")
        else:
            print("❌ Failed to generate upload URL")
    except Exception as e:
        print(f"❌ Error generating upload URL: {e}")
    
    print()
    print("🌐 Web Interface:")
    print(f"   Main App: {base_url}")
    print(f"   Streamlit UI: {base_url}/ui")
    print(f"   API Docs: {base_url}/docs")
    print()
    print("📝 To test file upload and processing:")
    print("   1. Open the Streamlit UI at the URL above")
    print("   2. Upload a PDF file")
    print("   3. Click 'Upload and Process'")
    print("   4. View the redaction results and download the processed file")

def demo_streamlit_features():
    """Show Streamlit features"""
    print("🎨 Streamlit UI Features:")
    print("=" * 30)
    print("• File upload with drag-and-drop interface")
    print("• Real-time processing status updates")
    print("• Interactive charts and visualizations")
    print("• Detailed redaction results table")
    print("• Direct download of redacted files")
    print("• Processing statistics dashboard")
    print("• Health monitoring")

if __name__ == "__main__":
    demo_api()
    print()
    demo_streamlit_features()
