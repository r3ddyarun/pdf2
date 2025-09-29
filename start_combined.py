#!/usr/bin/env python3
"""
Startup script for the combined FastAPI + Streamlit PDF Redaction Service
"""

import uvicorn
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

if __name__ == "__main__":
    print("🔒 Starting PDF Redaction Service (Combined FastAPI + Streamlit)")
    print("=" * 60)
    print("📡 FastAPI API: http://localhost:8000")
    print("🎨 Streamlit UI: http://localhost:8501")
    print("🔗 UI Redirect: http://localhost:8000/ui")
    print("📚 API Docs: http://localhost:8000/docs")
    print("💚 Health Check: http://localhost:8000/health")
    print("=" * 60)
    
    # Start the combined application
    uvicorn.run(
        "app.combined_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
