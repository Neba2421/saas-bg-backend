# Background Remover API

A production-ready FastAPI SaaS backend for removing image backgrounds using the Silueta ONNX model via rembg.

## Features

- **Fast & Efficient**: Background removal in under a second
- **Multiple Formats**: Supports JPEG, PNG, and WEBP input
- **In-Memory Processing**: No disk I/O for optimal performance
- **Production Ready**: Docker containerized with health checks
- **Scalable**: Gunicorn with Uvicorn workers for high concurrency
- **Secure**: Four-layer upload validation with decompression bomb protection

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (for containerized deployment)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd saas-bg-backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Copy environment file**
   ```bash
   cp .env.example .env
   ```

5. **Run the development server**
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Access the API**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

### Docker Build & Run

1. **Build the Docker image**
   ```bash
   docker build -t background-remover-api .
   ```

2. **Run the container**
   ```bash
   docker run -d -p 8000:8000 --name bg-remover background-remover-api
   ```

3. **Verify the container is running**
   ```bash
   docker ps
   curl http://localhost:8000/health
   ```

4. **Stop and remove container**
   ```bash
   docker stop bg-remover
   docker rm bg-remover
   ```

## Render Deployment

### Step-by-Step Deployment

1. **Create a new Web Service on Render**
   - Connect your GitHub repository
   - Select "Docker" as the environment
   - Choose your region

2. **Configure Environment Variables**

   Set the following environment variables in Render:

   ```
   MAX_FILE_SIZE=5242880
   MAX_WIDTH=6000
   MAX_HEIGHT=6000
   ORT_NUM_THREADS=1
   OMP_NUM_THREADS=1
   WEB_CONCURRENCY=2
   ALLOWED_ORIGINS=https://your-frontend-domain.com
   ```

3. **Deploy**
   - Render will automatically build and deploy your service
   - The health check endpoint (`/health`) will be monitored

### Render Environment Variables Explained

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_FILE_SIZE` | 5242880 | Maximum upload file size in bytes (5 MB) |
| `MAX_WIDTH` | 6000 | Maximum image width in pixels |
| `MAX_HEIGHT` | 6000 | Maximum image height in pixels |
| `ORT_NUM_THREADS` | 1 | ONNX Runtime thread count |
| `OMP_NUM_THREADS` | 1 | OpenMP thread count |
| `WEB_CONCURRENCY` | 4 | Number of Gunicorn workers |
| `ALLOWED_ORIGINS` | localhost | Comma-separated list of allowed CORS origins |

## API Endpoints

### Meta Endpoints

#### GET `/`
Service information endpoint.

**Response:**
```json
{
  "name": "Background Remover API",
  "version": "1.0.0",
  "status": "running"
}
```

#### GET `/health`
Health check endpoint for Docker and Render monitoring.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "engine": "rembg-silueta",
  "model_loaded": true,
  "timestamp": "2025-01-01T00:00:00+00:00"
}
```

**Response (503 Service Unavailable):**
```json
{
  "detail": "The inference engine is currently unavailable. Please try again shortly."
}
```

### Processing Endpoints

#### POST `/api/v1/remove-background`
Remove background from an uploaded image.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` (JPEG, PNG, or WEBP, max 5 MB)

**Response:**
- Content-Type: `image/png`
- Returns a transparent PNG file

**Example using curl:**
```bash
curl -X POST \
  http://localhost:8000/api/v1/remove-background \
  -F "file=@input.jpg" \
  -o output.png
```

**Example using Python:**
```python
import requests

with open('input.jpg', 'rb') as f:
    files = {'file': ('input.jpg', f, 'image/jpeg')}
    response = requests.post(
        'http://localhost:8000/api/v1/remove-background',
        files=files
    )

if response.status_code == 200:
    with open('output.png', 'wb') as out:
        out.write(response.content)
```

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success - PNG image returned |
| 400 | Corrupted image or invalid dimensions |
| 413 | File too large (exceeds 5 MB) |
| 415 | Unsupported file type |
| 422 | Invalid request payload |
| 500 | Internal server error |
| 503 | Inference engine unavailable |

## Testing

### Run All Tests
```bash
pytest
```

### Run with Verbose Output
```bash
pytest -v
```

### Run Specific Test File
```bash
pytest tests/test_validators.py -v
```

### Run with Coverage
```bash
pytest --cov=. --cov-report=html
```

## Troubleshooting

### Model Loading Issues

**Problem:** Health check returns 503

**Solutions:**
1. Check container logs: `docker logs bg-remover`
2. Verify the model was pre-downloaded during build
3. Ensure sufficient memory allocation (minimum 512 MB recommended)

### Performance Issues

**Problem:** Slow processing times

**Solutions:**
1. Increase `WEB_CONCURRENCY` for higher throughput
2. Adjust `ORT_NUM_THREADS` and `OMP_NUM_THREADS` based on CPU cores
3. Consider using a larger instance type on Render

### CORS Errors

**Problem:** Frontend cannot access API

**Solutions:**
1. Set `ALLOWED_ORIGINS` to include your frontend domain
2. Ensure the format is comma-separated without spaces
3. Example: `ALLOWED_ORIGINS=https://example.com,https://www.example.com`

### Upload Failures

**Problem:** Valid images rejected

**Solutions:**
1. Check file size doesn't exceed `MAX_FILE_SIZE`
2. Verify image dimensions don't exceed `MAX_WIDTH`/`MAX_HEIGHT`
3. Ensure file is a valid JPEG, PNG, or WEBP format

### Docker Build Failures

**Problem:** Build fails during model download

**Solutions:**
1. Check internet connectivity during build
2. Increase Docker build timeout
3. Verify Python version is 3.11

## Architecture

### Technology Stack
- **Framework**: FastAPI 0.111.0
- **Server**: Gunicorn 22.0.0 with Uvicorn workers
- **AI Model**: Silueta ONNX via rembg 2.0.56
- **Image Processing**: Pillow 10.3.0
- **Container**: Multi-stage Docker build

### Security Features
- Four-layer upload validation
- Decompression bomb protection (50 MP limit)
- Non-root container user
- CORS configuration
- Input sanitization

### Performance Optimizations
- Model preloading and warming
- In-memory processing (no disk I/O)
- Singleton session pattern
- Thread pool optimization
- ONNX runtime caching

## License

MIT License

## Support

For issues and questions:
- GitHub Issues: [Create an issue]
- Documentation: `/docs` endpoint
- Health Check: `/health` endpoint