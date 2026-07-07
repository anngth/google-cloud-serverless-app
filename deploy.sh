#!/usr/bin/env bash

# Exit immediately if any command returns a non-zero status
set -e

# =====================================================================
# Configuration Variables (Update these to match your GCP project)
# =====================================================================
PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
REGION="us-central1"
BUCKET_NAME="${PROJECT_ID}-docs-ingestion"
DATASET_NAME="doc_processing_dataset"
TABLE_NAME="doc_metadata"
SERVICE_NAME="doc-processor-service"
TRIGGER_NAME="doc-gcs-eventarc-trigger"
RUN_SA="doc-processor-runner"

echo "=== Deployment Configuration (Eventarc - Secured) ==="
echo "Project ID:      ${PROJECT_ID}"
echo "Region:          ${REGION}"
echo "Storage Bucket:  gs://${BUCKET_NAME}"
echo "BigQuery Table:  ${DATASET_NAME}.${TABLE_NAME}"
echo "Cloud Run:       ${SERVICE_NAME}"
echo "Eventarc:        ${TRIGGER_NAME}"
echo "Runner Identity: ${RUN_SA}"
echo "====================================================="

if [ -z "$PROJECT_ID" ]; then
    echo "ERROR: GCP Project ID could not be detected. Please set it manually or authenticate with 'gcloud auth login'."
    exit 1
fi

# Ensure correct project context
gcloud config set project "$PROJECT_ID"

echo "1. Enabling required Google Cloud APIs..."
gcloud services enable \
    run.googleapis.com \
    eventarc.googleapis.com \
    storage.googleapis.com \
    bigquery.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    iam.googleapis.com

echo "2. Setting up Google Cloud Storage bucket..."
if gcloud storage buckets describe "gs://${BUCKET_NAME}" &>/dev/null; then
    echo "   Bucket gs://${BUCKET_NAME} already exists."
else
    gcloud storage buckets create "gs://${BUCKET_NAME}" --location="${REGION}"
    echo "   Bucket gs://${BUCKET_NAME} created."
fi

echo "3. Granting Pub/Sub Publisher role to Cloud Storage service account at project level..."
GCS_SERVICE_ACCOUNT=$(gcloud storage service-agent | tr -d '[:space:]')
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${GCS_SERVICE_ACCOUNT}" \
    --role="roles/pubsub.publisher" \
    --quiet
echo "   Pub/Sub Publisher role granted."

echo "4. Creating Custom Service Account for Cloud Run..."
RUN_SA_EMAIL="${RUN_SA}@${PROJECT_ID}.iam.gserviceaccount.com"
if gcloud iam service-accounts describe "${RUN_SA_EMAIL}" &>/dev/null; then
    echo "   Service account ${RUN_SA_EMAIL} already exists."
else
    gcloud iam service-accounts create "${RUN_SA}" \
        --display-name="Service Account for Cloud Run Document Processor" \
        --quiet
    echo "   Service account ${RUN_SA_EMAIL} created."
fi

echo "5. Granting GCS & BigQuery permissions to custom Service Account..."
# Grant Storage Object Viewer strictly on the ingestion bucket
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
    --member="serviceAccount:${RUN_SA_EMAIL}" \
    --role="roles/storage.objectViewer" \
    --quiet

# Grant BigQuery Data Editor at project level to insert rows and list tables
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${RUN_SA_EMAIL}" \
    --role="roles/bigquery.dataEditor" \
    --quiet

# Grant BigQuery Job User at project level to run query jobs for the dashboard
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${RUN_SA_EMAIL}" \
    --role="roles/bigquery.jobUser" \
    --quiet
echo "   Permissions successfully bound to ${RUN_SA_EMAIL}."

echo "6. Creating BigQuery Dataset..."
if bq show "${PROJECT_ID}:${DATASET_NAME}" &>/dev/null; then
    echo "   BigQuery dataset ${DATASET_NAME} already exists."
else
    bq mk --location="${REGION}" --dataset "${PROJECT_ID}:${DATASET_NAME}"
    echo "   BigQuery dataset ${DATASET_NAME} created."
fi

echo "7. Creating BigQuery Table..."
if bq show "${PROJECT_ID}:${DATASET_NAME}.${TABLE_NAME}" &>/dev/null; then
    echo "   BigQuery table ${DATASET_NAME}.${TABLE_NAME} already exists."
else
    bq mk --table "${PROJECT_ID}:${DATASET_NAME}.${TABLE_NAME}" schema.json
    echo "   BigQuery table ${DATASET_NAME}.${TABLE_NAME} created using schema.json."
fi

echo "8. Building and deploying SECURED Flask service to Cloud Run..."
# We use --no-allow-unauthenticated for production-grade security,
# forcing all requests to be authorized via OIDC signatures.
gcloud run deploy "${SERVICE_NAME}" \
    --source="." \
    --region="${REGION}" \
    --no-allow-unauthenticated \
    --service-account="${RUN_SA_EMAIL}" \
    --set-env-vars="BQ_TABLE_ID=${PROJECT_ID}.${DATASET_NAME}.${TABLE_NAME},INPUT_BUCKET_NAME=${BUCKET_NAME}" \
    --quiet

echo "9. Setting up Eventarc Trigger service account permissions..."
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
TRIGGER_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Grant Cloud Run Invoker to the trigger's service account (Compute default)
# This is crucial now that Cloud Run requires authentication.
gcloud run services add-iam-policy-binding "${SERVICE_NAME}" \
    --region="${REGION}" \
    --member="serviceAccount:${TRIGGER_SA}" \
    --role="roles/run.invoker" \
    --quiet
echo "   Cloud Run Invoker role granted to ${TRIGGER_SA}."

echo "10. Creating Eventarc Trigger for GCS uploads..."
if gcloud eventarc triggers describe "${TRIGGER_NAME}" --location="${REGION}" &>/dev/null; then
    echo "   Eventarc trigger ${TRIGGER_NAME} already exists."
else
    gcloud eventarc triggers create "${TRIGGER_NAME}" \
        --location="${REGION}" \
        --destination-run-service="${SERVICE_NAME}" \
        --destination-run-region="${REGION}" \
        --event-filters="type=google.cloud.storage.object.v1.finalized" \
        --event-filters="bucket=${BUCKET_NAME}" \
        --service-account="${TRIGGER_SA}"
    echo "   Eventarc trigger ${TRIGGER_NAME} created."
fi

echo "=== Deployment completed successfully! ==="
echo "You can test the pipeline by uploading a text file to the GCS bucket:"
echo "  gcloud storage cp path/to/local/file.txt gs://${BUCKET_NAME}/"
echo "Note: The dashboard now requires authentication and cannot be accessed publicly."
