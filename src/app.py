import logging
import os
from datetime import datetime, timezone

from flask import Flask, request, jsonify, render_template

# Import modular helper components
from src.gcs_helper import GCSHelper
from src.bq_helper import BQHelper
from src.processor import DocumentProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize components
gcs_helper = GCSHelper()
bq_helper = BQHelper()
processor = DocumentProcessor()

# Validate configuration on startup
if not os.environ.get("INPUT_BUCKET_NAME"):
    logger.warning(
        "INPUT_BUCKET_NAME is not configured. "
        "Access verification will log warnings but permit requests."
    )

if not os.environ.get("BQ_TABLE_ID"):
    logger.warning(
        "BQ_TABLE_ID is not configured. "
        "Database operations will fail unless MOCK_GCP is enabled."
    )


@app.route("/", methods=["GET"])
def render_dashboard():
    """
    Renders the HTML dashboard of processed documents.
    """
    table_id = os.environ.get("BQ_TABLE_ID")
    if not table_id:
        logger.error("BQ_TABLE_ID environment variable is not set.")
        return "Internal Server Error: BQ_TABLE_ID unset", 500

    try:
        # Fetch the latest processed documents
        documents = bq_helper.list_metadata_rows(table_id)

        # Calculate the unique list of tags for filtering chips
        unique_tags_set = set()
        for doc in documents:
            tags_str = doc.get("tags")
            if tags_str:
                for tag in tags_str.split(","):
                    clean_tag = tag.strip().lower()
                    if clean_tag:
                        unique_tags_set.add(clean_tag)

        unique_tags = sorted(list(unique_tags_set))

        return render_template(
            "dashboard.html", documents=documents, unique_tags=unique_tags
        )
    except Exception as e:
        logger.error(f"Failed to render dashboard: {e}")
        return f"Internal Server Error: {e}", 500


def _extract_coordinates(data):
    """
    Extracts bucket, object name, and creation time coordinates from payload.
    """
    if not data:
        logger.error("No JSON payload received.")
        return None, "Bad Request: Missing payload", 400

    bucket_name = data.get("bucket")
    object_name = data.get("name")
    time_created = data.get("timeCreated")

    if not bucket_name or not object_name:
        logger.error(f"Missing bucket or name in Eventarc metadata: {data}")
        return None, "Bad Request: Missing bucket or name", 400

    return (bucket_name, object_name, time_created), None, 200


def _validate_bucket(bucket_name, object_name):
    """
    Validates if bucket source is expected to prevent unauthorized access.
    """
    expected_bucket = os.environ.get("INPUT_BUCKET_NAME")
    if not expected_bucket:
        logger.warning(
            f"INPUT_BUCKET_NAME is unset. Processing file "
            f"gs://{bucket_name}/{object_name} without bucket validation."
        )
        return True

    if bucket_name != expected_bucket:
        logger.warning(
            f"Forbidden bucket access attempt: gs://{bucket_name}/{object_name} "
            f"(Expected: gs://{expected_bucket})"
        )
        return False

    return True


def _verify_file_size(bucket_name, object_name):
    """
    Checks file size on GCS to prevent OOM errors before downloading.
    """
    if gcs_helper.mock_mode or not gcs_helper.client:
        return None, 200

    try:
        bucket = gcs_helper.client.bucket(bucket_name)
        blob = bucket.get_blob(object_name)
        if not blob:
            logger.error(f"Blob not found: gs://{bucket_name}/{object_name}")
            return "Not Found: File not found on GCS", 404

        # Enforce 20 MB size limit
        MAX_SIZE_BYTES = 20 * 1024 * 1024
        if blob.size > MAX_SIZE_BYTES:
            logger.warning(f"File size {blob.size} bytes exceeds maximum 20MB limit.")
            return "Bad Request: File size exceeds 20MB limit", 400
    except Exception as e:
        logger.error(f"GCS metadata size check failed: {e}")
        return f"Internal GCS check error: {e}", 500

    return None, 200


@app.route("/", methods=["POST"])
def process_message():
    """
    Receives an Eventarc CloudEvent representing a GCS finalized file, downloads
    the file, extracts metadata using DocumentProcessor, and streams it to BigQuery.
    """
    data = request.get_json(silent=True)
    coords, err_msg, status_code = _extract_coordinates(data)
    if err_msg:
        return jsonify({"error": err_msg}), status_code

    bucket_name, object_name, time_created = coords

    # 1. Security Hardening: Validate bucket source to prevent SSRF / Path Traversal
    if not _validate_bucket(bucket_name, object_name):
        return jsonify({"error": "Forbidden: Bucket source not authorized"}), 403

    logger.info(f"Event received for file: gs://{bucket_name}/{object_name}")

    # 2. Security Hardening: Check file size before downloading to avoid OOM
    err_msg, status_code = _verify_file_size(bucket_name, object_name)
    if err_msg:
        return jsonify({"error": err_msg}), status_code

    # 3. Download file content from GCS
    try:
        content = gcs_helper.download_blob_as_text(bucket_name, object_name)
        # 4. Process text content to extract word count and tags
        word_count, tags = processor.process_text(content)
        tags_str = ",".join(tags)
    except Exception as e:
        logger.warning(f"Failed to process text file (treating as binary): {e}")
        word_count = 0
        tags_str = "binary,unsupported"

    # Default to current UTC time if metadata time is not provided
    if not time_created:
        time_created = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 5. Stream data to BigQuery
    table_id = os.environ.get("BQ_TABLE_ID")
    if not table_id:
        logger.error("BQ_TABLE_ID environment variable is not set.")
        return jsonify({"error": "Internal Server Error: BQ_TABLE_ID unset"}), 500

    row_data = {
        "filename": object_name,
        "upload_time": time_created,
        "word_count": word_count,
        "tags": tags_str,
    }

    try:
        bq_helper.insert_metadata_row(table_id, row_data)
        logger.info(f"Successfully processed and recorded: {object_name}")
        return (
            jsonify(
                {"status": "success", "message": "File processed and metadata saved"}
            ),
            200,
        )
    except Exception as e:
        logger.error(f"Failed to insert row into BigQuery: {e}")
        return jsonify({"error": f"Internal BigQuery Error: {e}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
