# PDF Redaction Service

An enterprise-ready PDF redaction service that automatically detects and redacts sensitive information from PDF documents using AI-powered content detection.

## Features

- **Automated Content Detection**: Detects sensitive information including:
  - Email addresses
  - Social Security Numbers (SSN)
  - Credit card numbers
  - Phone numbers
  - Dates of birth
  - Account numbers
  - Addresses and names

- **Secure File Processing**: 
  - AWS S3 integration for file storage
  - Presigned URLs for secure uploads
  - Configurable file size limits

- **Enterprise Features**:
  - ClickHouse database for analytics
  - Prometheus metrics and Grafana dashboards
  - Comprehensive logging and monitoring
  - RESTful API with FastAPI
  - Streamlit web interface
  - Docker containerization

- **High Performance**:
  - PyMuPDF for efficient PDF processing
  - Async processing capabilities
  - Scalable architecture

## Architecture

```
┌─────────────────────────────────────────┐    ┌─────────────────┐
│         Combined Application            │    │   ClickHouse    │
│   FastAPI + Streamlit (Port 8000)      │◄──►│   Database      │
│                                         │    └─────────────────┘
│   ┌─────────────────┐ ┌─────────────────┐    ┌─────────────────┐
│   │   FastAPI API   │ │   Streamlit UI  │    │   AWS S3        │
│   │   Endpoints     │ │   /ui           │◄──►│   File Storage  │
│   └─────────────────┘ └─────────────────┘    └─────────────────┘
└─────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.9+
- ClickHouse database (optional, for analytics)
- AWS S3 bucket and credentials

### Environment Setup

1. Copy the environment template:
```bash
cp env.example .env
```

2. Configure your environment variables in `.env`:
```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name

# Security
SECRET_KEY=your-secure-secret-key

# Optional: Grafana password
GRAFANA_PASSWORD=your-grafana-password
```

### Quick Start

1. Install dependencies and start the application:
```bash
make dev-setup
make start-dev
```

2. Access the services:
- **Main Application**: http://localhost:8000
- **Streamlit UI**: http://localhost:8000/ui
- **API Documentation**: http://localhost:8000/docs

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Optional: Start ClickHouse for analytics:
```bash
# macOS
brew install clickhouse
clickhouse server

# Or use the setup script
./scripts/setup.sh
```

3. Run the combined application:
```bash
python start_combined.py
# or
make start-dev
```

4. Access the application:
- **Main App**: http://localhost:8000
- **Streamlit UI**: http://localhost:8000/ui
- **API Docs**: http://localhost:8000/docs

## API Endpoints

### File Upload
```bash
POST /upload
Content-Type: multipart/form-data

# Upload PDF file directly
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

### Get Upload URL
```bash
GET /upload-url/{filename}

# Get presigned URL for direct S3 upload
curl "http://localhost:8000/upload-url/document.pdf"
```

### Process File
```bash
POST /process/{file_id}
Content-Type: application/json

{
  "bucket": "your-bucket-name",
  "key": "uploads/document.pdf"
}
```

### Download Redacted File
```bash
POST /download
Content-Type: application/json

{
  "bucket": "your-bucket-name",
  "key": "redacted/document.pdf"
}
```

### Get Results
```bash
GET /results/{file_id}

# Get processing results and redaction details
curl "http://localhost:8000/results/your-file-id"
```

### Statistics
```bash
GET /stats?hours=24

# Get processing statistics
curl "http://localhost:8000/stats?hours=24"
```

## Configuration

### File Size Limits
- Maximum file size: 50MB (configurable via `MAX_FILE_SIZE_MB`)
- Supported formats: PDF only

### Content Detection
The service uses regular expressions and pattern matching to detect sensitive content:

- **Email**: RFC-compliant email pattern matching
- **SSN**: 9-digit patterns with optional dashes
- **Credit Card**: Luhn algorithm validation
- **Phone**: Various US phone number formats
- **Date of Birth**: MM/DD/YYYY and MM-DD-YYYY formats
- **Account Numbers**: 8+ digit sequences

### Confidence Scoring
Each detected item receives a confidence score (0.0-1.0) based on:
- Pattern strength and validation
- Context analysis
- Content characteristics

## Monitoring and Metrics

### Prometheus Metrics
- `http_requests_total`: HTTP request count by method, endpoint, status
- `http_request_duration_seconds`: Request duration histogram
- `pdf_processing_duration_seconds`: PDF processing time
- `pdf_file_size_bytes`: File size distribution
- `pdf_redactions_total`: Redaction count by reason

### Grafana Dashboards
Pre-configured dashboards for:
- API performance metrics
- Processing statistics
- Error rates and alerts
- File processing trends

### Logging
Structured JSON logging with:
- Request/response correlation IDs
- Performance metrics
- Error tracking
- Security events

## Security Features

- **File Validation**: Strict PDF format checking
- **Size Limits**: Configurable file size restrictions
- **Secure Storage**: AWS S3 with presigned URLs
- **Access Control**: Token-based authentication (extensible)
- **Audit Trail**: Complete processing history in ClickHouse

## Testing

Run the test suite:
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_api.py -v
```

## Development

### Code Quality
```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Type checking
mypy app/

# Linting
flake8 app/ tests/
```

### Database Migrations
```bash
# Initialize Alembic (if needed)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Description"

# Apply migration
alembic upgrade head
```

## Deployment

### Production Deployment

1. **Configure Environment**:
```bash
cp env.example .env
# Edit .env with production values
```

2. **Deploy with Gunicorn**:
```bash
gunicorn app.combined_app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Production Considerations

1. **Security**:
   - Use strong secret keys
   - Enable HTTPS/TLS
   - Configure proper CORS policies
   - Implement authentication/authorization
   - Use IAM roles for AWS access

2. **Performance**:
   - Configure ClickHouse for high throughput
   - Use Redis for caching (optional)
   - Implement request rate limiting
   - Configure auto-scaling

3. **Monitoring**:
   - Set up alerting rules
   - Configure log aggregation
   - Monitor S3 costs and usage
   - Set up health checks

### Deployment Options

- **Development**: `make start-dev` or `python start_combined.py`
- **Production**: Gunicorn with multiple workers
- **Cloud**: Deploy to AWS, GCP, or Azure
- **Container**: Build custom Docker image if needed

### Kubernetes Deployment (Optional)
```yaml
# Example Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pdf-redaction-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pdf-redaction-api
  template:
    metadata:
      labels:
        app: pdf-redaction-api
    spec:
      containers:
      - name: api
        image: pdf-redaction-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: AWS_ACCESS_KEY_ID
          valueFrom:
            secretKeyRef:
              name: aws-credentials
              key: access-key-id
```

## Testing

The project includes comprehensive testing tools for PDF redaction functionality:

### Test File Generation

Generate various types of test PDFs for testing:

```bash
# Generate all types of test PDFs
make generate-test-pdfs

# Or manually
python3 generate_test_pdfs.py --count 2 --type all
```

### Running Tests

Test the PDF redaction service with generated files:

```bash
# Run comprehensive tests
make test-redaction

# Quick sensitive data test
make test-sensitive

# Or manually
python3 test_redaction.py --report
```

### Test File Types

- **Normal PDFs**: Regular text documents
- **Sensitive PDFs**: Documents with emails, SSNs, credit cards
- **Business PDFs**: Structured employee documents
- **Corrupt PDFs**: Error handling test cases
- **Empty PDFs**: Edge case testing
- **Large PDFs**: Performance testing

See [TESTING.md](TESTING.md) for detailed testing documentation.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Create an issue in the GitHub repository
- Check the documentation
- Review the API documentation at `/docs`

## Roadmap

- [ ] Advanced AI/ML models for content detection
- [ ] Support for additional file formats
- [ ] Real-time processing notifications
- [ ] Batch processing capabilities
- [ ] Custom redaction patterns
- [ ] OCR integration for scanned documents
- [ ] Multi-language support
- [ ] Advanced analytics and reporting
