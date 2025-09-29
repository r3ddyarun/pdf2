#!/usr/bin/env python3
"""
Production startup script for PDF Redaction Service
"""

import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """Check if all requirements are met"""
    print("🔍 Checking requirements...")
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ is required")
        return False
    
    # Check if .env exists
    if not Path(".env").exists():
        print("⚠️  .env file not found. Creating from template...")
        if Path("env.example").exists():
            subprocess.run(["cp", "env.example", ".env"])
            print("✅ Created .env file from template")
            print("⚠️  Please edit .env with your configuration")
        else:
            print("❌ env.example not found")
            return False
    
    # Check AWS credentials
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file) as f:
            content = f.read()
            if "your_access_key_here" in content or "your_secret_key_here" in content:
                print("⚠️  Please configure AWS credentials in .env file")
                return False
    
    print("✅ Requirements check passed")
    return True

def start_production():
    """Start the application in production mode"""
    print("🚀 Starting PDF Redaction Service in production mode")
    print("=" * 60)
    
    if not check_requirements():
        print("❌ Requirements check failed. Please fix the issues above.")
        return
    
    # Set production environment variables
    os.environ["DEBUG"] = "false"
    os.environ["LOG_LEVEL"] = "INFO"
    os.environ["RELOAD"] = "false"
    
    print("📡 Starting Gunicorn server...")
    print("🌐 Application will be available at: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🎨 Streamlit UI: http://localhost:8000/ui")
    print("=" * 60)
    
    # Start Gunicorn
    try:
        subprocess.run([
            "gunicorn",
            "app.combined_app:app",
            "-w", "4",
            "-k", "uvicorn.workers.UvicornWorker",
            "--bind", "0.0.0.0:8000",
            "--access-logfile", "-",
            "--error-logfile", "-",
            "--log-level", "info"
        ])
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    start_production()
