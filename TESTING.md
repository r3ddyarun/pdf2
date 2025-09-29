# PDF Redaction Service Testing

This document describes how to test the PDF redaction service using the provided test tools and generated test files.

## Test File Generator

The `generate_test_pdfs.py` script creates various types of test PDF files for comprehensive testing:

### PDF Types Generated

1. **Normal PDFs** - Regular text documents for basic functionality testing
2. **Sensitive PDFs** - Documents containing sensitive data (emails, SSNs, credit cards, phone numbers)
3. **Business PDFs** - Structured business documents with employee information
4. **Corrupt PDFs** - Intentionally corrupted files for error handling testing
5. **Empty PDFs** - Minimal content files for edge case testing
6. **Large PDFs** - Multi-page documents for performance testing

### Usage

```bash
# Generate all types of test PDFs (1 of each)
python3 generate_test_pdfs.py

# Generate multiple files of each type
python3 generate_test_pdfs.py --count 3

# Generate only sensitive PDFs
python3 generate_test_pdfs.py --type sensitive --count 5

# Generate to custom directory
python3 generate_test_pdfs.py --output-dir my_test_files

# Using Makefile
make generate-test-pdfs
```

### Command Line Options

- `--output-dir, -o`: Output directory (default: test_pdfs)
- `--count, -c`: Number of each type to generate (default: 1)
- `--type, -t`: Type to generate (normal, sensitive, business, corrupt, empty, large, all)

## Test Runner

The `test_redaction.py` script automatically tests the PDF redaction service with generated test files:

### Features

- **Complete Workflow Testing**: Upload → Process → Download
- **Multiple File Types**: Tests all generated PDF types
- **Error Handling**: Tests corrupt files and edge cases
- **Performance Metrics**: Measures processing time and file sizes
- **Detailed Reporting**: Generates comprehensive test reports

### Usage

```bash
# Test all PDFs in test_pdfs directory
python3 test_redaction.py

# Test specific files
python3 test_redaction.py --files "sensitive_*.pdf" "business_*.pdf"

# Generate detailed report
python3 test_redaction.py --report

# Test against different server
python3 test_redaction.py --server-url http://localhost:8080

# Using Makefile
make test-redaction
```

### Command Line Options

- `--server-url, -s`: Server URL (default: http://localhost:8000)
- `--test-dir, -d`: Test PDF directory (default: test_pdfs)
- `--files, -f`: Specific files to test (glob patterns)
- `--report, -r`: Generate detailed test report
- `--output-report, -o`: Report output file (default: test_report.txt)

## Quick Test Commands

### Using Makefile

```bash
# Generate test files and run tests
make generate-test-pdfs
make test-redaction

# Quick sensitive data test
make test-sensitive

# Clean up test files
make clean-tests
```

### Manual Testing

```bash
# 1. Generate test files
python3 generate_test_pdfs.py --count 2 --type all

# 2. Start the server (in another terminal)
python3 start_combined.py

# 3. Run tests
python3 test_redaction.py --report

# 4. Check results
cat test_report.txt
```

## Test Scenarios

### 1. Basic Functionality
- **Files**: Normal PDFs
- **Purpose**: Verify basic upload, processing, and download
- **Expected**: Successful processing with minimal redactions

### 2. Sensitive Data Detection
- **Files**: Sensitive PDFs
- **Purpose**: Test redaction accuracy for emails, SSNs, credit cards
- **Expected**: High redaction count with proper categorization

### 3. Business Documents
- **Files**: Business PDFs
- **Purpose**: Test structured document processing
- **Expected**: Accurate extraction and redaction of employee data

### 4. Error Handling
- **Files**: Corrupt PDFs
- **Purpose**: Test graceful error handling
- **Expected**: Proper error messages and no crashes

### 5. Edge Cases
- **Files**: Empty PDFs
- **Purpose**: Test minimal content handling
- **Expected**: Successful processing with no redactions

### 6. Performance
- **Files**: Large PDFs
- **Purpose**: Test processing time and memory usage
- **Expected**: Reasonable processing times for large files

## Sample Test Output

```
🧪 PDF Redaction Service Tester
==================================================
✅ Server is healthy and running

🎯 Found 6 PDF files to test
============================================================

🔍 Testing file: sensitive_1_20250929_125424.pdf
--------------------------------------------------
✅ Uploaded sensitive_1_20250929_125424.pdf: abc123def456
✅ Processed file abc123def456
✅ Downloaded redacted file: redacted_outputs/redacted_sensitive_1_20250929_125424.pdf

🔍 Testing file: corrupt_1_20250929_125424.pdf
--------------------------------------------------
✅ Uploaded corrupt_1_20250929_125424.pdf: def456ghi789
❌ Processing failed for def456ghi789: 500
```

## Test Report Example

```
📊 PDF Redaction Service Test Report
==================================================
Test Date: 2025-09-29 12:54:24
Server URL: http://localhost:8000
Total Files Tested: 6

📈 Summary Statistics:
  Successful: 5
  Failed Upload: 0
  Failed Processing: 1
  Failed Download: 0
  Other Issues: 0

📁 File Types Tested:
  sensitive: 2
  business: 2
  normal: 2
  corrupt: 1
  empty: 1
  large: 1

📏 Size Statistics:
  Total Original Size: 61,014 bytes (0.06 MB)
  Total Redacted Size: 58,234 bytes (0.06 MB)
  Size Reduction: 4.6%

📋 Detailed Results:
--------------------------------------------------

File: sensitive_1_20250929_125424.pdf
  Type: sensitive
  Size: 3,606 bytes
  Status: success
  Processing Time: 2.34s
  Total Pages: 1
  Total Redactions: 8
  Redaction Details:
    email: 3
    ssn: 2
    credit_card: 2
    phone: 1
```

## Integration with CI/CD

The test scripts can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Test PDF Redaction Service
  run: |
    python3 generate_test_pdfs.py --count 1 --type all
    python3 test_redaction.py --report
    # Check if all tests passed
    if grep -q "Failed Processing: 0" test_report.txt; then
      echo "All tests passed!"
    else
      echo "Some tests failed!"
      exit 1
    fi
```

## Troubleshooting

### Common Issues

1. **Server not running**: Make sure the PDF redaction service is started
2. **Permission errors**: Check file permissions in test directories
3. **Memory issues**: Reduce file count for large PDFs
4. **Network errors**: Verify server URL and connectivity

### Debug Mode

Add verbose output to test scripts:

```bash
python3 test_redaction.py --report --files "sensitive_*.pdf"
```

## Contributing

To add new test scenarios:

1. Add new PDF generation methods to `generate_test_pdfs.py`
2. Update the `_classify_file` method in `test_redaction.py`
3. Add new test cases to the documentation
4. Update the Makefile targets if needed
