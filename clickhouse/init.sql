-- ClickHouse initialization script for PDF Redaction Service

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS pdf_redaction;

-- Use the database
USE pdf_redaction;

-- Create redaction results table
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
PARTITION BY toYYYYMM(created_at)
SETTINGS index_granularity = 8192;

-- Create redaction blocks table
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
PARTITION BY toYYYYMM(created_at)
SETTINGS index_granularity = 8192;

-- Create processing metrics table
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
PARTITION BY toYYYYMM(timestamp)
SETTINGS index_granularity = 8192;

-- Create materialized view for hourly statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS hourly_stats
ENGINE = SummingMergeTree()
ORDER BY hour
AS SELECT
    toStartOfHour(timestamp) as hour,
    count() as file_count,
    sum(processing_time) as total_processing_time,
    sum(file_size) as total_file_size,
    sum(redaction_count) as total_redactions,
    sum(success) as successful_files,
    sum(1 - success) as failed_files
FROM processing_metrics
GROUP BY hour;

-- Create materialized view for redaction statistics by reason
CREATE MATERIALIZED VIEW IF NOT EXISTS redaction_reason_stats
ENGINE = SummingMergeTree()
ORDER BY (date, reason)
AS SELECT
    toDate(created_at) as date,
    reason,
    count() as redaction_count,
    avg(confidence) as avg_confidence
FROM redaction_blocks
GROUP BY date, reason;

-- Create table for storing processing errors and issues
CREATE TABLE IF NOT EXISTS processing_errors (
    timestamp DateTime DEFAULT now(),
    file_id String,
    filename String,
    error_type String,
    error_message String,
    stack_trace Nullable(String),
    processing_stage String
) ENGINE = MergeTree()
ORDER BY (timestamp, file_id)
PARTITION BY toYYYYMM(timestamp)
SETTINGS index_granularity = 8192;

-- Create table for storing user sessions and API usage
CREATE TABLE IF NOT EXISTS api_usage (
    timestamp DateTime DEFAULT now(),
    endpoint String,
    method String,
    status_code UInt16,
    response_time_ms UInt32,
    file_id Nullable(String),
    user_agent Nullable(String),
    ip_address String
) ENGINE = MergeTree()
ORDER BY (timestamp, endpoint)
PARTITION BY toYYYYMM(timestamp)
SETTINGS index_granularity = 8192;

-- Create materialized view for daily processing summary
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_processing_summary
ENGINE = SummingMergeTree()
ORDER BY date
AS SELECT
    toDate(timestamp) as date,
    count() as total_files_processed,
    sum(success) as successful_files,
    sum(1 - success) as failed_files,
    avg(processing_time) as avg_processing_time,
    sum(processing_time) as total_processing_time,
    sum(file_size) as total_file_size,
    sum(redaction_count) as total_redactions
FROM processing_metrics
GROUP BY date;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_file_id ON redaction_results (file_id) TYPE bloom_filter GRANULARITY 1;
CREATE INDEX IF NOT EXISTS idx_created_at ON redaction_results (created_at) TYPE minmax GRANULARITY 3;
CREATE INDEX IF NOT EXISTS idx_processing_time ON processing_metrics (processing_time) TYPE minmax GRANULARITY 3;
CREATE INDEX IF NOT EXISTS idx_reason ON redaction_blocks (reason) TYPE set(0) GRANULARITY 1;
CREATE INDEX IF NOT EXISTS idx_endpoint ON api_usage (endpoint) TYPE set(0) GRANULARITY 1;

-- Insert sample data for testing (optional)
-- INSERT INTO redaction_results VALUES (
--     'sample-file-1',
--     'sample.pdf',
--     1024000,
--     'test-bucket',
--     'uploads/sample.pdf',
--     'test-bucket',
--     'redacted/sample.pdf',
--     5,
--     2.5,
--     3,
--     {'email': 2, 'ssn': 1},
--     {'average': 0.85, 'minimum': 0.75, 'maximum': 0.95},
--     now()
-- );
