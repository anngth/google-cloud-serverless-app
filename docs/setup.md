# Local Setup & Testing

## Prerequisites
* Python 3.11+
* Google Cloud SDK (gcloud CLI)

## Installation
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Optional: Install development dependencies (testing and linting)
pip install -r requirements-dev.txt
```

## Running Unit Tests & Style Checks
Ensure your virtual environment is active, then run:
```bash
# Run unit tests
pytest

# Check formatting
black --check src tests

# Run linter
flake8 src tests
```

## Mock Local Test (`./test_local.sh`)
Verifies Flask payload parsing and OCR logic locally:
```bash
./test_local.sh
```
* **Simulated GCS Path**: `mock_gcs/my-bucket/sample.txt`
* **Trigger Type**: Direct HTTP POST (mocks Eventarc CloudEvent body)

## Running Local Web Server manually
```bash
MOCK_GCP=true BQ_TABLE_ID=mock-project.mock.table PORT=8080 python3 -m src.app
```
* **URL**: [http://localhost:8080](http://localhost:8080) (features search and tag filters)
