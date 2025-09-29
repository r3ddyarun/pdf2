#!/usr/bin/env python3
"""
Startup script for FastAPI server only
"""

import uvicorn
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

if __name__ == "__main__":
    print("🔒 Starting PDF Redaction Service - FastAPI Server Only")
    print("=" * 60)
    print("📡 FastAPI API: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("💚 Health Check: http://localhost:8000/health")
    print("🔗 UI Redirect: http://localhost:8000/ui (will redirect to Streamlit)")
    print("=" * 60)
    print("💡 To start Streamlit UI separately, run: python start_ui.py")
    print("=" * 60)
    
    # Start only the FastAPI application
    uvicorn.run(
        "app.main_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
