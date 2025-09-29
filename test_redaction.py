#!/usr/bin/env python3
"""
Test PDF Redaction Service

This script demonstrates how to use the generated test PDFs to test the PDF redaction service.
It uploads and processes various types of test PDFs to verify the service functionality.

Usage:
    python test_redaction.py [--server-url URL] [--test-dir DIR]
"""

import os
import sys
import argparse
import requests
import time
import json
from pathlib import Path
from typing import List, Dict, Any


class PDFRedactionTester:
    """Test the PDF redaction service with various test files"""
    
    def __init__(self, server_url: str = "http://localhost:8000", test_dir: str = "test_pdfs"):
        self.server_url = server_url.rstrip('/')
        self.test_dir = Path(test_dir)
        self.results = []
        
    def check_server_health(self) -> bool:
        """Check if the server is running and healthy"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Server is healthy and running")
                return True
            else:
                print(f"❌ Server health check failed: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot connect to server: {e}")
            return False
    
    def upload_file(self, file_path: Path) -> Dict[str, Any]:
        """Upload a PDF file to the service"""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, 'application/pdf')}
                response = requests.post(f"{self.server_url}/upload", files=files, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Uploaded {file_path.name}: {result.get('file_id', 'unknown')}")
                return result
            else:
                print(f"❌ Upload failed for {file_path.name}: {response.status_code}")
                return {"error": f"Upload failed: {response.status_code}"}
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Upload error for {file_path.name}: {e}")
            return {"error": str(e)}
    
    def process_file(self, file_id: str, upload_result: Dict[str, Any]) -> Dict[str, Any]:
        """Process an uploaded file for redaction"""
        try:
            # Extract bucket and key from upload result
            bucket = upload_result.get("s3_bucket")
            key = upload_result.get("s3_key")
            
            if not bucket or not key:
                return {"error": "Missing bucket or key in upload result"}
            
            # Call the correct endpoint with query parameters
            url = f"{self.server_url}/process/{file_id}"
            params = {"bucket": bucket, "key": key}
            
            response = requests.post(
                url,
                params=params,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Processed file {file_id}")
                return result
            else:
                print(f"❌ Processing failed for {file_id}: {response.status_code}")
                print(f"Response: {response.text}")
                return {"error": f"Processing failed: {response.status_code}"}
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Processing error for {file_id}: {e}")
            return {"error": str(e)}
    
    def download_file(self, file_id: str, output_path: Path) -> bool:
        """Download the redacted file"""
        try:
            response = requests.get(f"{self.server_url}/download/{file_id}", timeout=30)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Downloaded redacted file: {output_path.name}")
                return True
            else:
                print(f"❌ Download failed for {file_id}: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Download error for {file_id}: {e}")
            return False
    
    def test_file(self, file_path: Path) -> Dict[str, Any]:
        """Test a single PDF file through the complete workflow"""
        print(f"\n🔍 Testing file: {file_path.name}")
        print("-" * 50)
        
        result = {
            "filename": file_path.name,
            "file_size": file_path.stat().st_size,
            "file_type": self._classify_file(file_path),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "upload": {},
            "processing": {},
            "download": {}
        }
        
        # Upload file
        upload_result = self.upload_file(file_path)
        result["upload"] = upload_result
        
        if "error" in upload_result:
            result["status"] = "failed_upload"
            return result
        
        file_id = upload_result.get("file_id")
        if not file_id:
            result["status"] = "no_file_id"
            return result
        
        # Process file
        process_result = self.process_file(file_id, upload_result)
        result["processing"] = process_result
        
        if "error" in process_result:
            result["status"] = "failed_processing"
            return result
        
        # Download redacted file
        output_dir = Path("redacted_outputs")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"redacted_{file_path.name}"
        
        download_success = self.download_file(file_id, output_path)
        result["download"] = {"success": download_success, "output_path": str(output_path)}
        
        if download_success:
            result["status"] = "success"
            result["redacted_size"] = output_path.stat().st_size
        else:
            result["status"] = "failed_download"
        
        return result
    
    def _classify_file(self, file_path: Path) -> str:
        """Classify the type of test file based on filename"""
        name = file_path.name.lower()
        if "sensitive" in name:
            return "sensitive"
        elif "business" in name:
            return "business"
        elif "corrupt" in name:
            return "corrupt"
        elif "empty" in name:
            return "empty"
        elif "large" in name:
            return "large"
        elif "normal" in name:
            return "normal"
        else:
            return "unknown"
    
    def run_tests(self, file_patterns: List[str] = None) -> List[Dict[str, Any]]:
        """Run tests on all or selected PDF files"""
        if not self.check_server_health():
            print("❌ Cannot proceed without a healthy server")
            return []
        
        if not self.test_dir.exists():
            print(f"❌ Test directory not found: {self.test_dir}")
            return []
        
        # Find PDF files
        if file_patterns:
            pdf_files = []
            for pattern in file_patterns:
                pdf_files.extend(self.test_dir.glob(pattern))
        else:
            pdf_files = list(self.test_dir.glob("*.pdf"))
        
        if not pdf_files:
            print(f"❌ No PDF files found in {self.test_dir}")
            return []
        
        print(f"\n🎯 Found {len(pdf_files)} PDF files to test")
        print("=" * 60)
        
        results = []
        for pdf_file in pdf_files:
            result = self.test_file(pdf_file)
            results.append(result)
            self.results.append(result)
            
            # Small delay between tests
            time.sleep(1)
        
        return results
    
    def generate_report(self) -> str:
        """Generate a test report"""
        if not self.results:
            return "No test results available"
        
        report = []
        report.append("📊 PDF Redaction Service Test Report")
        report.append("=" * 50)
        report.append(f"Test Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Server URL: {self.server_url}")
        report.append(f"Total Files Tested: {len(self.results)}")
        report.append("")
        
        # Summary statistics
        status_counts = {}
        file_type_counts = {}
        total_original_size = 0
        total_redacted_size = 0
        
        for result in self.results:
            status = result.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            
            file_type = result.get("file_type", "unknown")
            file_type_counts[file_type] = file_type_counts.get(file_type, 0) + 1
            
            total_original_size += result.get("file_size", 0)
            total_redacted_size += result.get("redacted_size", 0)
        
        report.append("📈 Summary Statistics:")
        report.append(f"  Successful: {status_counts.get('success', 0)}")
        report.append(f"  Failed Upload: {status_counts.get('failed_upload', 0)}")
        report.append(f"  Failed Processing: {status_counts.get('failed_processing', 0)}")
        report.append(f"  Failed Download: {status_counts.get('failed_download', 0)}")
        report.append(f"  Other Issues: {len(self.results) - sum(status_counts.values())}")
        report.append("")
        
        report.append("📁 File Types Tested:")
        for file_type, count in file_type_counts.items():
            report.append(f"  {file_type}: {count}")
        report.append("")
        
        if total_original_size > 0:
            report.append("📏 Size Statistics:")
            report.append(f"  Total Original Size: {total_original_size:,} bytes ({total_original_size/1024/1024:.2f} MB)")
            if total_redacted_size > 0:
                report.append(f"  Total Redacted Size: {total_redacted_size:,} bytes ({total_redacted_size/1024/1024:.2f} MB)")
                compression_ratio = (1 - total_redacted_size / total_original_size) * 100
                report.append(f"  Size Reduction: {compression_ratio:.1f}%")
        report.append("")
        
        # Detailed results
        report.append("📋 Detailed Results:")
        report.append("-" * 50)
        
        for result in self.results:
            report.append(f"\nFile: {result['filename']}")
            report.append(f"  Type: {result['file_type']}")
            report.append(f"  Size: {result['file_size']:,} bytes")
            report.append(f"  Status: {result['status']}")
            
            if result['status'] == 'success':
                processing = result.get('processing', {})
                report.append(f"  Processing Time: {processing.get('processing_time_seconds', 'N/A')}s")
                report.append(f"  Total Pages: {processing.get('total_pages', 'N/A')}")
                report.append(f"  Total Redactions: {processing.get('total_redactions', 'N/A')}")
                
                if processing.get('redactions_by_reason'):
                    report.append("  Redaction Details:")
                    for reason, count in processing['redactions_by_reason'].items():
                        report.append(f"    {reason}: {count}")
            else:
                # Show error details
                if result.get('upload', {}).get('error'):
                    report.append(f"  Upload Error: {result['upload']['error']}")
                if result.get('processing', {}).get('error'):
                    report.append(f"  Processing Error: {result['processing']['error']}")
                if result.get('download', {}).get('error'):
                    report.append(f"  Download Error: {result['download']['error']}")
        
        return "\n".join(report)


def main():
    """Main function to run the PDF redaction tests"""
    parser = argparse.ArgumentParser(description="Test PDF redaction service with generated test files")
    parser.add_argument("--server-url", "-s", default="http://localhost:8000",
                       help="Server URL (default: http://localhost:8000)")
    parser.add_argument("--test-dir", "-d", default="test_pdfs",
                       help="Directory containing test PDFs (default: test_pdfs)")
    parser.add_argument("--files", "-f", nargs="+",
                       help="Specific files to test (glob patterns)")
    parser.add_argument("--report", "-r", action="store_true",
                       help="Generate detailed test report")
    parser.add_argument("--output-report", "-o", default="test_report.txt",
                       help="Output file for test report (default: test_report.txt)")
    
    args = parser.parse_args()
    
    print("🧪 PDF Redaction Service Tester")
    print("=" * 50)
    
    tester = PDFRedactionTester(args.server_url, args.test_dir)
    
    # Run tests
    results = tester.run_tests(args.files)
    
    if not results:
        print("❌ No tests were run")
        return
    
    print(f"\n✅ Completed testing {len(results)} files")
    
    # Generate report if requested
    if args.report:
        report = tester.generate_report()
        
        with open(args.output_report, 'w') as f:
            f.write(report)
        
        print(f"📄 Test report saved to: {args.output_report}")
        print("\n" + "=" * 50)
        print(report)
    else:
        # Show quick summary
        successful = sum(1 for r in results if r.get('status') == 'success')
        total = len(results)
        print(f"📊 Results: {successful}/{total} successful")
        
        if successful < total:
            print("\n❌ Failed tests:")
            for result in results:
                if result.get('status') != 'success':
                    print(f"  - {result['filename']}: {result['status']}")


if __name__ == "__main__":
    main()
