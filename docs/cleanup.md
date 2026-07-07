# Cleaning Up GCP Resources

Delete resources to prevent charges:

```bash
PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
BUCKET_NAME="${PROJECT_ID}-docs-ingestion"
TRIGGER_NAME="doc-gcs-eventarc-trigger"
DATASET_NAME="doc_processing_dataset"
SERVICE_NAME="doc-processor-service"
RUN_SA="doc-processor-runner"
RUN_SA_EMAIL="${RUN_SA}@${PROJECT_ID}.iam.gserviceaccount.com"

# 1. Eventarc GCS Trigger
gcloud eventarc triggers delete "${TRIGGER_NAME}" --location="${REGION}" --quiet

# 2. Cloud Run Service
gcloud run services delete "${SERVICE_NAME}" --region="${REGION}" --quiet

# 3. GCS Ingestion Bucket
gcloud storage rm --recursive "gs://${BUCKET_NAME}" --quiet

# 4. BigQuery Dataset
bq rm -r -f -d "${PROJECT_ID}:${DATASET_NAME}"

# 5. Service Account
gcloud iam service-accounts delete "${RUN_SA_EMAIL}" --quiet

# 6. Artifact Registry
gcloud artifacts repositories delete cloud-run-source-deploy --location="${REGION}" --quiet

# 7. Cloud Build Source Cache
gcloud storage rm --recursive "gs://run-sources-${PROJECT_ID}-${REGION}" --quiet
```
