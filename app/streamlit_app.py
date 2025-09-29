"""
Streamlit UI for PDF Redaction Service
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from typing import Dict, Any, Optional
import logging

from app.config import settings

# Configure Streamlit page FIRST - must be the first streamlit command
st.set_page_config(
    page_title="PDF Redaction Service",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Setup logging
logger = logging.getLogger(__name__)

# API Configuration
API_BASE_URL = f"http://localhost:{settings.api_port}"

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
            elif data is not None:
                response = requests.post(url, json=data)
            else:
                # Allow POST with no body (e.g., /process/{file_id})
                response = requests.post(url)
        else:
            st.error(f"Unsupported HTTP method: {method}")
            return None
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to the API server. Please ensure the backend is running on port 8000.")
        return None
    except Exception as e:
        st.error(f"Error making API request: {str(e)}")
        return None


def display_file_upload():
    """Display file upload interface"""
    st.markdown('<div class="section-header">📁 Upload PDF File</div>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type="pdf",
        help="Upload a PDF file to process for content detection and redaction"
    )
    
    if uploaded_file is not None:
        # Display file info
        st.info(f"📄 **File:** {uploaded_file.name} ({uploaded_file.size:,} bytes)")
        
        # Process file button
        if st.button("🚀 Process PDF", type="primary"):
            with st.spinner("Processing PDF file..."):
                # Upload file to API
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                
                upload_response = make_api_request("POST", "/upload", files=files)
                
                if upload_response and upload_response.get("file_id"):
                    # Call process-by-id endpoint
                    file_id = upload_response["file_id"]
                    process_response = make_api_request("POST", f"/process")
                    
                    if process_response:
                        # Store response in session state
                        st.session_state.process_response = process_response
                        st.session_state.file_processed = True
                        
                        st.success("✅ File processed successfully!")
                        st.rerun()
                else:
                    st.error("Upload failed. Please try again.")


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
        # Handle case where average might be None or invalid
        if avg_confidence is None or not isinstance(avg_confidence, (int, float)):
            avg_confidence = 0.0
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
            # Ensure block is a dictionary
            if not isinstance(block, dict):
                continue
                
            # Format reason for display
            reason = block.get("reason", "N/A")
            if reason != "N/A" and reason:
                reason = str(reason).replace('_', ' ').title()
            
            # Get confidence with safe conversion
            confidence = block.get("confidence", 0)
            if not isinstance(confidence, (int, float)):
                confidence = 0.0
            
            # Get numeric values with safe conversion
            page_num = block.get("page_number", "N/A")
            x_coord = block.get("x", 0)
            y_coord = block.get("y", 0)
            width = block.get("width", 0)
            height = block.get("height", 0)
            original_text = block.get("original_text", "N/A")
            
            blocks_data.append({
                "Page": page_num,
                "Reason": reason,
                "Confidence": f"{confidence:.2%}",
                "X": f"{float(x_coord):.1f}" if isinstance(x_coord, (int, float)) else "0.0",
                "Y": f"{float(y_coord):.1f}" if isinstance(y_coord, (int, float)) else "0.0",
                "Width": f"{float(width):.1f}" if isinstance(width, (int, float)) else "0.0",
                "Height": f"{float(height):.1f}" if isinstance(height, (int, float)) else "0.0",
                "Original Text": str(original_text) if original_text else "N/A"
            })
        
        df_blocks = pd.DataFrame(blocks_data)
        st.dataframe(df_blocks, use_container_width=True)
        
        # Confidence distribution chart
        confidences = []
        for block in redaction_blocks:
            confidence = block.get("confidence", 0)
            if isinstance(confidence, (int, float)) and confidence > 0:
                confidences.append(confidence)
        
        if confidences:
            fig_confidence = px.histogram(
                x=confidences,
                nbins=20,
                title="Confidence Score Distribution",
                labels={"x": "Confidence Score", "y": "Count"}
            )
            st.plotly_chart(fig_confidence, use_container_width=True)
        else:
            st.info("No confidence scores available for visualization")
    
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


def display_statistics():
    """Display processing statistics"""
    st.markdown('<div class="section-header">📈 Processing Statistics</div>', unsafe_allow_html=True)
    
    # Get stats from API
    stats = make_api_request("GET", "/stats")
    
    if stats:
        # Display key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Files Processed", stats.get("total_files", 0))
        
        with col2:
            st.metric("Success Rate", f"{stats.get('success_rate', 0):.1%}")
        
        with col3:
            st.metric("Average Processing Time", f"{stats.get('avg_processing_time', 0):.2f}s")
        
        with col4:
            st.metric("Total Redactions", stats.get("total_redactions", 0))
        
        # Display charts if available
        if "processing_times" in stats:
            st.markdown("**Processing Time Distribution:**")
            fig = px.histogram(
                x=stats["processing_times"],
                nbins=20,
                title="Processing Time Distribution",
                labels={"x": "Processing Time (seconds)", "y": "Count"}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.warning("Unable to retrieve statistics from the API.")


def display_sidebar():
    """Display sidebar with navigation and info"""
    st.sidebar.title("🔒 PDF Redaction Service")
    
    # Navigation
    page = st.sidebar.selectbox(
        "Navigate",
        ["Upload & Process", "Statistics"],
        index=0
    )
    
    # File processing status
    if "file_processed" in st.session_state and st.session_state.file_processed:
        st.sidebar.success("✅ File processed successfully!")
        
        # Clear results button
        if st.sidebar.button("🔄 Process New File"):
            # Clear session state
            for key in ["process_response", "file_processed"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    # API Status
    st.sidebar.markdown("---")
    st.sidebar.markdown("**API Status**")
    
    try:
        health_response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if health_response.status_code == 200:
            st.sidebar.success("🟢 API Online")
        else:
            st.sidebar.error("🔴 API Error")
    except:
        st.sidebar.error("🔴 API Offline")
    
    # Information
    st.sidebar.markdown("---")
    st.sidebar.markdown("**About**")
    st.sidebar.info("""
    This service processes PDF files to detect and redact sensitive information including:
    
    • Email addresses
    • Phone numbers
    • Credit card numbers
    • SSNs
    • Custom patterns
    """)
    
    return page


def create_streamlit_app():
    """Create and configure Streamlit app"""
    
    # Main header
    st.markdown('<div class="main-header">🔒 PDF Redaction Service</div>', unsafe_allow_html=True)
    
    # Sidebar navigation
    page = display_sidebar()
    
    # Main content based on selected page
    if page == "Upload & Process":
        display_file_upload()
        
        # Show results if available
        if "file_processed" in st.session_state and st.session_state.file_processed:
            display_results()
    
    elif page == "Statistics":
        display_statistics()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "PDF Redaction Service - Secure Document Processing"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    create_streamlit_app()
