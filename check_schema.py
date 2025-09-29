#!/usr/bin/env python3
"""
Check ClickHouse table schemas
"""

from app.database.clickhouse_client import clickhouse_client

def check_schemas():
    """Check table schemas"""
    
    print("🔍 Checking ClickHouse Table Schemas")
    print("=" * 40)
    
    try:
        # Check redaction_results table
        print("1. redaction_results table:")
        result = clickhouse_client.client.query("DESCRIBE redaction_results")
        for row in result.result_rows:
            print(f"   {row[0]} - {row[1]}")
        
        print(f"\n   Total columns: {len(result.result_rows)}")
        
        # Check redaction_blocks table
        print("\n2. redaction_blocks table:")
        result = clickhouse_client.client.query("DESCRIBE redaction_blocks")
        for row in result.result_rows:
            print(f"   {row[0]} - {row[1]}")
        
        print(f"\n   Total columns: {len(result.result_rows)}")
        
        # Check processing_metrics table
        print("\n3. processing_metrics table:")
        result = clickhouse_client.client.query("DESCRIBE processing_metrics")
        for row in result.result_rows:
            print(f"   {row[0]} - {row[1]}")
        
        print(f"\n   Total columns: {len(result.result_rows)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_schemas()
