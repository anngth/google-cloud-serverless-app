import logging
import os

logger = logging.getLogger(__name__)


class GCSHelper:
    def __init__(self):
        self.mock_mode = os.environ.get("MOCK_GCP", "false").lower() == "true"
        if self.mock_mode:
            logger.info("GCSHelper initialized in MOCK mode.")
            self.client = None
            return

        try:
            from google.cloud import storage

            self.client = storage.Client()
        except Exception as e:
            logger.warning(
                f"Could not initialize GCS Client: {e}. "
                f"Defaulting to mock/local storage operations."
            )
            self.client = None
            self.mock_mode = True

    def download_blob_as_text(self, bucket_name, object_name):
        """
        Downloads a blob from the specified bucket and decodes it as UTF-8 text.
        In mock mode, attempts to read from a local GCS folder:
        './mock_gcs/{bucket_name}/{object_name}' or falls back to mock text.
        """
        if self.mock_mode:
            logger.info(f"[MOCK GCS] Fetching gs://{bucket_name}/{object_name}")
            # Try to read from local mock directory if it exists
            base_path = os.path.abspath("mock_gcs")
            bucket_path = os.path.abspath(os.path.join(base_path, bucket_name))
            local_path = os.path.abspath(os.path.join(bucket_path, object_name))

            # Prevent directory traversal vulnerability (must be within the bucket)
            bucket_path_with_sep = bucket_path + os.sep
            if not (
                local_path.startswith(bucket_path_with_sep) or local_path == bucket_path
            ):
                logger.warning(
                    f"Directory traversal attempt blocked: {object_name} "
                    f"(Bucket: {bucket_name})"
                )
                raise ValueError("Path traversal attempt detected.")

            if os.path.exists(local_path):
                logger.info(f"[MOCK GCS] Reading file locally from {local_path}")
                with open(local_path, "r", encoding="utf-8") as f:
                    return f.read()
            return (
                "This is mock GCS content for local testing. "
                "It mentions gcp, serverless, and pipeline."
            )

        if not self.client:
            raise RuntimeError("GCS Client is not initialized.")

        logger.info(f"Downloading gs://{bucket_name}/{object_name}")
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        return blob.download_as_text(encoding="utf-8")
