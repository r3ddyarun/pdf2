"""
ClickHouse database client and utilities
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import clickhouse_connect
from clickhouse_connect import get_client
from app.config import settings

logger = logging.getLogger(__name__)


class ClickHouseClient:
    """ClickHouse database client"""
    
    def __init__(self):
        self.client = None
        self._connect()
    
    def _connect(self):
        """Establish connection to ClickHouse"""
        try:
            self.client = get_client(
                host=settings.clickhouse_host,
                port=settings.clickhouse_port,
                database=settings.clickhouse_database,
                username=settings.clickhouse_user,
                password=settings.clickhouse_password
            )
            logger.info("Connected to ClickHouse successfully")
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise
    
    def create_tables(self):
        """Create necessary tables"""
        create_redaction_results_table = """
        CREATE TABLE IF NOT EXISTS redaction_results (
            file_id String,
            filename String,
            file_size UInt64,
            s3_bucket String,
            s3_key String,
            redacted_s3_bucket String,
            redacted_s3_key String,
            total_pages UInt16,
            processing_time_seconds Float64,
            total_redactions UInt16,
            redactions_by_reason Map(String, UInt16),
            confidence_scores Map(String, Float64),
            created_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (created_at, file_id)
        """
        
        create_redaction_blocks_table = """
        CREATE TABLE IF NOT EXISTS redaction_blocks (
            file_id String,
            page_number UInt16,
            x Float64,
            y Float64,
            width Float64,
            height Float64,
            reason String,
            confidence Float64,
            original_text Nullable(String),
            created_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (file_id, page_number)
        """
        
        create_metrics_table = """
        CREATE TABLE IF NOT EXISTS processing_metrics (
            timestamp DateTime,
            file_id String,
            processing_time Float64,
            file_size UInt64,
            redaction_count UInt16,
            success UInt8,
            error_message Nullable(String)
        ) ENGINE = MergeTree()
        ORDER BY (timestamp, file_id)
        """
        
        try:
            self.client.command(create_redaction_results_table)
            self.client.command(create_redaction_blocks_table)
            self.client.command(create_metrics_table)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def insert_redaction_result(self, data: Dict[str, Any]) -> None:
        """Insert redaction result into database"""
        try:
            # Convert dict to list of values in the correct order
            values = [
                data['file_id'],
                data['filename'],
                data['file_size'],
                data['s3_bucket'],
                data['s3_key'],
                data['redacted_s3_bucket'],
                data['redacted_s3_key'],
                data['total_pages'],
                data['processing_time_seconds'],
                data['total_redactions'],
                data['redactions_by_reason'],
                data['confidence_scores'],
                data.get('created_at', datetime.utcnow())
            ]
            self.client.insert('redaction_results', [values])
            logger.info(f"Inserted redaction result for file_id: {data.get('file_id')}")
        except Exception as e:
            logger.error(f"Failed to insert redaction result: {e}")
            raise
    
    def insert_redaction_blocks(self, file_id: str, blocks: List[Dict[str, Any]]) -> None:
        """Insert redaction blocks into database"""
        if not blocks:
            return
            
        try:
            # Convert blocks to list of lists
            values = []
            for block in blocks:
                values.append([
                    file_id,
                    block['page_number'],
                    block['x'],
                    block['y'],
                    block['width'],
                    block['height'],
                    block['reason'],
                    block['confidence'],
                    block.get('original_text'),
                    datetime.utcnow()
                ])
            
            self.client.insert('redaction_blocks', values)
            logger.info(f"Inserted {len(blocks)} redaction blocks for file_id: {file_id}")
        except Exception as e:
            logger.error(f"Failed to insert redaction blocks: {e}")
            raise
    
    def insert_metrics(self, data: Dict[str, Any]) -> None:
        """Insert processing metrics into database"""
        try:
            # Convert dict to list of values in the correct order
            values = [
                data['timestamp'],
                data['file_id'],
                data['processing_time'],
                data['file_size'],
                data['redaction_count'],
                data['success'],
                data['error_message']
            ]
            self.client.insert('processing_metrics', [values])
            logger.info(f"Inserted metrics for file_id: {data.get('file_id')}")
        except Exception as e:
            logger.error(f"Failed to insert metrics: {e}")
            raise
    
    def get_file_history(self, file_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get processing history for a file"""
        try:
            result = self.client.query(
                "SELECT * FROM redaction_results WHERE file_id = %(file_id)s ORDER BY created_at DESC",
                parameters={'file_id': file_id}
            )
            if not result.result_rows:
                return None
            
            # Convert tuples to dictionaries using proper column names
            columns = [
                'file_id', 'filename', 'file_size', 's3_bucket', 's3_key',
                'redacted_s3_bucket', 'redacted_s3_key', 'total_pages',
                'processing_time_seconds', 'total_redactions', 'redactions_by_reason',
                'confidence_scores', 'created_at'
            ]
            return [dict(zip(columns, row)) for row in result.result_rows]
        except Exception as e:
            logger.error(f"Failed to get file history: {e}")
            return None
    
    def get_redaction_blocks(self, file_id: str) -> List[Dict[str, Any]]:
        """Get redaction blocks for a file"""
        try:
            result = self.client.query(
                "SELECT * FROM redaction_blocks WHERE file_id = %(file_id)s ORDER BY page_number",
                parameters={'file_id': file_id}
            )
            return result.result_rows
        except Exception as e:
            logger.error(f"Failed to get redaction blocks: {e}")
            return []
    
    def get_processing_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get processing statistics for the last N hours"""
        try:
            # Use columns from processing_metrics table
            result = self.client.query(
                """
                SELECT 
                    count() AS total_files,
                    avg(processing_time) AS avg_processing_time,
                    sum(redaction_count) AS total_redactions,
                    countIf(success = 1) AS successful_files,
                    countIf(success = 0) AS failed_files
                FROM processing_metrics 
                WHERE timestamp >= now() - INTERVAL %(hours)s HOUR
                """,
                parameters={'hours': hours}
            )

            if not result.result_rows:
                return {
                    "total_files": 0,
                    "avg_processing_time": 0.0,
                    "total_redactions": 0,
                    "successful_files": 0,
                    "failed_files": 0,
                }

            # Map the single-row tuple result to a dictionary with explicit keys
            row = result.result_rows[0]
            return {
                "total_files": row[0] or 0,
                "avg_processing_time": float(row[1]) if row[1] is not None else 0.0,
                "total_redactions": row[2] or 0,
                "successful_files": row[3] or 0,
                "failed_files": row[4] or 0,
            }
        except Exception as e:
            logger.error(f"Failed to get processing stats: {e}")
            return {}
    
    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()


# Global ClickHouse client instance
clickhouse_client = ClickHouseClient()
