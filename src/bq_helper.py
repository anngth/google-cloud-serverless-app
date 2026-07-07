import logging
import os
import re

logger = logging.getLogger(__name__)


class BQHelper:
    def __init__(self):
        self.mock_mode = os.environ.get("MOCK_GCP", "false").lower() == "true"
        if self.mock_mode:
            logger.info("BQHelper initialized in MOCK mode.")
            self.client = None
            return

        try:
            from google.cloud import bigquery

            self.client = bigquery.Client()
        except Exception as e:
            logger.warning(
                f"Could not initialize BigQuery Client: {e}. "
                f"Defaulting to mock/local DB operations."
            )
            self.client = None
            self.mock_mode = True

    def _validate_table_id(self, table_id):
        """
        Validates that the BigQuery table ID only contains safe characters:
        alphanumeric, underscores, dashes, and periods.
        """
        if not table_id:
            raise ValueError("BigQuery table_id cannot be empty.")
        # Strip backticks if present
        clean_id = table_id.replace("`", "")
        # BigQuery project, dataset and table names only allow alphanumeric,
        # underscores, and dashes, separated by dots.
        if not re.match(r"^[a-zA-Z0-9\-_\.]+$", clean_id):
            raise ValueError(f"Invalid BigQuery table ID format: {table_id}")

    def insert_metadata_row(self, table_id, row_data):
        """
        Streams a single metadata row into the specified BigQuery table.
        In mock mode, simply prints the row data to the log and returns success.
        """
        self._validate_table_id(table_id)
        if self.mock_mode:
            logger.info(
                f"[MOCK BQ] Row successfully streamed to {table_id}: {row_data}"
            )
            return True

        if not self.client:
            raise RuntimeError("BigQuery Client is not initialized.")

        logger.info(f"Streaming insert to BigQuery table {table_id}: {row_data}")
        errors = self.client.insert_rows_json(table_id, [row_data])
        if errors:
            logger.error(f"BigQuery insertion errors: {errors}")
            raise RuntimeError(f"BigQuery Insert Error: {errors}")

        return True

    def list_metadata_rows(self, table_id, limit=100):
        """
        Queries BigQuery for the latest processed documents.
        In mock mode, returns a static list of simulated documents.
        """
        self._validate_table_id(table_id)
        if self.mock_mode:
            logger.info(f"[MOCK BQ] Querying latest records from {table_id}")
            return [
                {
                    "filename": "serverless_gcp_guide.txt",
                    "upload_time": "2026-07-06 15:30:00 UTC",
                    "word_count": 142,
                    "tags": "gcp,serverless,pipeline",
                },
                {
                    "filename": "app_config_production.json",
                    "upload_time": "2026-07-06 15:15:00 UTC",
                    "word_count": 56,
                    "tags": "data,metadata",
                },
                {
                    "filename": "python_ocr_engine.py",
                    "upload_time": "2026-07-06 14:50:00 UTC",
                    "word_count": 312,
                    "tags": "python,ocr,run",
                },
                {
                    "filename": "raw_scanned_image.png",
                    "upload_time": "2026-07-06 14:10:00 UTC",
                    "word_count": 0,
                    "tags": "binary,unsupported",
                },
            ]

        if not self.client:
            raise RuntimeError("BigQuery Client is not initialized.")

        query = f"""
            SELECT filename, upload_time, word_count, tags
            FROM `{table_id}`
            ORDER BY upload_time DESC
            LIMIT {limit}
        """
        logger.info(f"Executing BigQuery Query: {query}")
        query_job = self.client.query(query)
        results = query_job.result()

        rows = []
        for row in results:
            # Format datetime safely
            if row.upload_time:
                # If it's a datetime object, format it. Otherwise keep as string.
                if hasattr(row.upload_time, "strftime"):
                    upload_time_str = row.upload_time.strftime("%Y-%m-%d %H:%M:%S UTC")
                else:
                    upload_time_str = str(row.upload_time)
            else:
                upload_time_str = "Unknown"

            rows.append(
                {
                    "filename": row.filename,
                    "upload_time": upload_time_str,
                    "word_count": row.word_count,
                    "tags": row.tags or "",
                }
            )

        return rows
