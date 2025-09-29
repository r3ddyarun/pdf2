#!/usr/bin/env python3
"""
Debug ClickHouse database operations
"""

from app.database.clickhouse_client import clickhouse_client
from datetime import datetime
import traceback

def debug_clickhouse():
    """Debug ClickHouse operations step by step"""
    
    print("🔍 Debugging ClickHouse Operations")
    print("=" * 40)
    
    try:
        # Test 1: Check connection
        print("1. Testing ClickHouse connection...")
        clickhouse_client.create_tables()
        print("✅ Connection successful")
        
        # Test 2: Test metrics insertion with minimal data
        print("\n2. Testing metrics insertion...")
        metrics_data = {
            'timestamp': datetime.now(),
            'file_id': 'test-file-123',
            'processing_time': 1.0,
            'file_size': 1000,
            'redaction_count': 0,
            'success': 1,
            'error_message': None
        }
        
        print(f"Metrics data: {metrics_data}")
        clickhouse_client.insert_metrics(metrics_data)
        print("✅ Metrics insertion successful")
        
        # Test 3: Test redaction result insertion
        print("\n3. Testing redaction result insertion...")
        redaction_data = {
            'file_id': 'test-file-123',
            'filename': 'test.pdf',
            'file_size': 1000,
            's3_bucket': 'test-bucket',
            's3_key': 'test-key',
            'redacted_s3_bucket': 'test-bucket',
            'redacted_s3_key': 'test-redacted-key',
            'total_pages': 1,
            'processing_time_seconds': 1.0,
            'total_redactions': 0,
            'redactions_by_reason': {},
            'confidence_scores': {}
        }
        
        print(f"Redaction data: {redaction_data}")
        clickhouse_client.insert_redaction_result(redaction_data)
        print("✅ Redaction result insertion successful")
        
        # Test 4: Test redaction blocks insertion
        print("\n4. Testing redaction blocks insertion...")
        blocks_data = [
            {
                'page_number': 1,
                'x': 10.0,
                'y': 20.0,
                'width': 100.0,
                'height': 30.0,
                'reason': 'EMAIL',
                'confidence': 0.95,
                'original_text': 'test@example.com'
            }
        ]
        
        print(f"Blocks data: {blocks_data}")
        clickhouse_client.insert_redaction_blocks('test-file-123', blocks_data)
        print("✅ Redaction blocks insertion successful")
        
        print("\n🎉 All ClickHouse operations successful!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    debug_clickhouse()
