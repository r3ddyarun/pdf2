# Startup Guide - Separate Servers

## Overview
The PDF Redaction Service now runs with separate FastAPI and Streamlit servers for better control and debugging.

## Starting the Services

### Option 1: Start FastAPI Server Only
```bash
python start_api.py
```
- **Port**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Option 2: Start Streamlit UI Only
```bash
python start_ui.py
```
- **Port**: http://localhost:8501
- **Note**: Requires FastAPI server running on port 8000 for full functionality

**Alternative (if startup script has issues):**
```bash
PYTHONPATH=/Users/arunreddy/Documents/GitHub/pdf2 streamlit run app/streamlit_app.py --server.port 8501
```

### Option 3: Start Both Services (Separate Terminals)

**Terminal 1 - FastAPI Server:**
```bash
python start_api.py
```

**Terminal 2 - Streamlit UI:**
```bash
python start_ui.py
```

## Service Communication

- **Streamlit UI** (port 8501) makes API calls to **FastAPI** (port 8000)
- The `/ui` endpoint on FastAPI redirects to Streamlit UI
- Both services can be started/stopped independently

## Benefits of Separate Servers

1. **Better Debugging**: Can restart one service without affecting the other
2. **Development Flexibility**: Work on API or UI independently
3. **Resource Management**: Better control over resource usage
4. **Scaling**: Can scale services independently in production
5. **Error Isolation**: Issues in one service don't crash the other

## Port Configuration

- **FastAPI API**: Port 8000
- **Streamlit UI**: Port 8501
- **UI Redirect**: http://localhost:8000/ui → http://localhost:8501

## Stopping Services

- **FastAPI**: Press `Ctrl+C` in the terminal running `start_api.py`
- **Streamlit**: Press `Ctrl+C` in the terminal running `start_ui.py`

## Troubleshooting

### Port Already in Use
```bash
# Kill processes on specific ports
lsof -ti:8000 | xargs kill -9  # FastAPI port
lsof -ti:8501 | xargs kill -9  # Streamlit port
```

### Check Running Services
```bash
# Check what's running on the ports
lsof -i:8000
lsof -i:8501
```

### Module Import Errors
If you get `ModuleNotFoundError: No module named 'app'`:

**Solution 1: Use the startup script**
```bash
python start_ui.py
```

**Solution 2: Set PYTHONPATH manually**
```bash
PYTHONPATH=/Users/arunreddy/Documents/GitHub/pdf2 streamlit run app/streamlit_app.py --server.port 8501
```

**Solution 3: Use absolute path**
```bash
cd /Users/arunreddy/Documents/GitHub/pdf2
streamlit run app/streamlit_app.py --server.port 8501
```

### Architecture Compatibility Issues
If you encounter numpy/streamlit architecture errors (x86_64 vs arm64):
- This is a Python environment issue, not a code issue
- Use the direct streamlit command with PYTHONPATH
- Consider using a virtual environment with proper architecture packages

## Full Functionality

For full application functionality:
1. Start FastAPI server: `python start_api.py`
2. Start Streamlit UI: `python start_ui.py`
3. Access UI at: http://localhost:8501
