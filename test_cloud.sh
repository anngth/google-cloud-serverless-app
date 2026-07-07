#!/usr/bin/env bash

# Exit immediately if any command returns a non-zero status
set -e

# =====================================================================
# Configuration Variables (Must match deploy.sh variables)
# =====================================================================
PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
BUCKET_NAME="${PROJECT_ID}-docs-ingestion"
DATASET_NAME="doc_processing_dataset"
TABLE_NAME="doc_metadata"

echo "=== Live Cloud Pipeline Integration Test ==="
echo "Project ID:      ${PROJECT_ID}"
echo "Storage Bucket:  gs://${BUCKET_NAME}"
echo "BigQuery Table:  ${DATASET_NAME}.${TABLE_NAME}"
echo "============================================="

if [ -z "$PROJECT_ID" ]; then
    echo "ERROR: GCP Project ID could not be detected. Please set it manually or authenticate with 'gcloud auth login'."
    exit 1
fi

# Ensure correct project context
gcloud config set project "$PROJECT_ID" &>/dev/null

# 1. Create a temporary local file to upload
RANDOM_ID=$(python3 -c "import random; print(random.randint(1000, 9999))")
TEST_FILE="test_cloud_upload_${RANDOM_ID}.txt"
echo "1. Creating temporary local text file: ${TEST_FILE}..."
python3 -c "
import random
sentences = [
    'Google Cloud Platform provides powerful serverless capabilities.',
    'This pipeline uses Cloud Storage, Eventarc, Cloud Run, and BigQuery.',
    'Python and Flask run the metadata extraction service.',
    'Data engineering pipelines enable real-time analytical indexing.',
    'Developing automated OCR simulation helps index documents quickly.',
    'Serverless compute scales down to zero when idle.'
]
selected = random.sample(sentences, k=random.randint(2, 4))
print('\n'.join(selected))
" > "${TEST_FILE}"

# Ensure cleanup of local file on exit
cleanup() {
    echo "4. Cleaning up temporary local file: ${TEST_FILE}..."
    rm -f "${TEST_FILE}"
    echo "=== Live Cloud Test Completed ==="
}
trap cleanup EXIT

# 2. Upload file to GCS bucket to trigger the pipeline
echo "2. Uploading ${TEST_FILE} to GCS bucket gs://${BUCKET_NAME}..."
gcloud storage cp "${TEST_FILE}" "gs://${BUCKET_NAME}/${TEST_FILE}"

# 3. Wait for the event to flow through Pub/Sub and trigger Cloud Run
WAIT_SECONDS=10
echo "3. Waiting ${WAIT_SECONDS} seconds for pipeline execution..."
sleep ${WAIT_SECONDS}

# 4. Query BigQuery table to check if the metadata record exists
echo "   Querying BigQuery table..."
bq query --use_legacy_sql=false \
    "SELECT filename, upload_time, word_count, tags FROM \`${PROJECT_ID}.${DATASET_NAME}.${TABLE_NAME}\` WHERE filename = '${TEST_FILE}' ORDER BY upload_time DESC LIMIT 1"
