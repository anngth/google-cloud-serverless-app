# GCP Deployment & Cloud Verification

## Authenticate
```bash
gcloud auth login
gcloud config set project <PROJECT_ID>
```

## Deploy (`./deploy.sh`)
Provision resources and deploy container:
```bash
./deploy.sh
```

### Deployed Resources:
* **APIs**: `run`, `eventarc`, `storage`, `bigquery`, `artifactregistry`, `cloudbuild`, `iam`
* **Bucket**: `gs://<PROJECT_ID>-docs-ingestion`
* **BigQuery**: Dataset `doc_processing_dataset`, Table `doc_metadata`
* **Custom SA**: `doc-processor-runner` (IAM Roles: `storage.objectViewer` on bucket, `bigquery.dataEditor`, `bigquery.jobUser` on project)
* **Cloud Run**: Authenticated endpoint (`--no-allow-unauthenticated`)
* **Eventarc GCS Trigger**: `doc-gcs-eventarc-trigger` (Compute default SA: `run.invoker`)

## Cloud Verification (`./test_cloud.sh`)
Uploads a randomized text file to GCS and queries BigQuery:
```bash
./test_cloud.sh
```
* **Wait duration**: 10 seconds (event propagation)
* **Query check**: `SELECT * FROM \`PROJECT_ID.doc_processing_dataset.doc_metadata\` WHERE filename LIKE 'test_cloud%'`
