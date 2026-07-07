#!/usr/bin/env bash

# Exit immediately if any command returns a non-zero status
set -e

echo "=== Local Pipeline Eventarc Integration Test ==="

# 1. Setup local mock GCS storage
MOCK_DIR="mock_gcs/my-bucket"
mkdir -p "$MOCK_DIR"
cat <<EOF > "$MOCK_DIR/sample.txt"
This is a local text file containing gcp, serverless, and pipeline keywords.
We are using it to simulate OCR text extraction and indexing.
EOF
echo "   Mock file created at: $MOCK_DIR/sample.txt"

# 2. Start the Flask application in mock mode (background)
echo "   Starting local Flask server in mock mode..."
export MOCK_GCP="true"
export BQ_TABLE_ID="mock-project.mock_dataset.mock_table"
export INPUT_BUCKET_NAME="my-bucket"
export PORT=8080
export PYTHONPATH="."

# Run Flask app in background
./.venv/bin/python src/app.py &
SERVER_PID=$!

# Ensure the background server is terminated on exit
cleanup() {
    echo "   Stopping local Flask server (PID: $SERVER_PID)..."
    kill "$SERVER_PID" 2>/dev/null || true
    echo "   Cleaning up mock GCS files..."
    rm -rf mock_gcs
    echo "=== Local Test Finished ==="
}
trap cleanup EXIT

# Wait a moment for Flask to initialize
sleep 2

# 3. Send mock GCS Eventarc payload via curl
echo "   Sending mock Eventarc GCS finalize payload to http://localhost:8080/..."
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST \
  -H "Content-Type: application/json" \
  -d "{
    \"bucket\": \"my-bucket\",
    \"name\": \"sample.txt\",
    \"timeCreated\": \"2026-07-06T15:00:00Z\"
  }" http://localhost:8080/)

# Parse response and status
HTML_BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')
HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d':' -f2)

echo "   HTTP Status Code: $HTTP_STATUS"
echo "   Response Body: $HTML_BODY"

if [ "$HTTP_STATUS" -eq 200 ]; then
    echo "SUCCESS: Local Eventarc integration test passed successfully!"
else
    echo "ERROR: Local Eventarc integration test failed with status $HTTP_STATUS."
    exit 1
fi
