#!/usr/bin/env python3
"""
Startup script for Streamlit UI only
"""

import subprocess
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

if __name__ == "__main__":
    print("🎨 Starting PDF Redaction Service - Streamlit UI Only")
    print("=" * 60)
    print("🎨 Streamlit UI: http://localhost:8501")
    print("=" * 60)
    print("💡 To start FastAPI server separately, run: python start_api.py")
    print("=" * 60)
    print("⚠️  Note: Make sure FastAPI server is running on port 8000 for full functionality")
    print("=" * 60)
    
    # Start Streamlit with proper Python path
    try:
        # Set PYTHONPATH environment variable to include the project root
        env = os.environ.copy()
        project_root = os.path.dirname(__file__)
        env['PYTHONPATH'] = project_root
        
        print(f"📁 Project root: {project_root}")
        print(f"🐍 PYTHONPATH: {env['PYTHONPATH']}")
        
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "app/streamlit_app.py", 
            "--server.port", "8501"
        ], env=env)
    except KeyboardInterrupt:
        print("\n🛑 Streamlit UI stopped by user")
    except Exception as e:
        print(f"❌ Error starting Streamlit: {e}")
        sys.exit(1)
