import os
import shutil
import pytest
from src.gcs_helper import GCSHelper
from src.bq_helper import BQHelper


@pytest.fixture(autouse=True)
def setup_mock_env():
    """Ensure mock env is set for helper tests."""
    os.environ["MOCK_GCP"] = "true"
    yield
    # Clean up mock directories if created
    if os.path.exists("mock_gcs"):
        shutil.rmtree("mock_gcs")


def test_gcs_helper_mock_default():
    helper = GCSHelper()
    content = helper.download_blob_as_text("test-bucket", "missing-file.txt")
    assert "This is mock GCS content" in content


def test_gcs_helper_mock_local_file():
    helper = GCSHelper()
    # Prepare local mock file
    os.makedirs("mock_gcs/test-bucket", exist_ok=True)
    with open("mock_gcs/test-bucket/hello.txt", "w", encoding="utf-8") as f:
        f.write("Hello from local mock storage!")

    content = helper.download_blob_as_text("test-bucket", "hello.txt")
    assert content == "Hello from local mock storage!"


def test_gcs_helper_path_traversal_protection():
    helper = GCSHelper()
    with pytest.raises(ValueError, match="Path traversal attempt detected"):
        helper.download_blob_as_text("test-bucket", "../../../outside.txt")


def test_gcs_helper_path_traversal_sibling_bucket():
    helper = GCSHelper()
    with pytest.raises(ValueError, match="Path traversal attempt detected"):
        helper.download_blob_as_text("test-bucket", "../sibling-bucket/file.txt")


def test_bq_helper_mock_insert():
    helper = BQHelper()
    success = helper.insert_metadata_row("mock.dataset.table", {"col": "val"})
    assert success is True


def test_bq_helper_mock_list():
    helper = BQHelper()
    rows = helper.list_metadata_rows("mock.dataset.table")
    assert len(rows) > 0
    assert "filename" in rows[0]
    assert "upload_time" in rows[0]


def test_bq_helper_validation():
    helper = BQHelper()
    # Should not raise any exception for valid format
    helper._validate_table_id("project-id.dataset_id.table_id")
    helper._validate_table_id("`project-id.dataset_id.table_id`")

    # Should raise ValueError for invalid characters or empty string
    with pytest.raises(ValueError, match="Invalid BigQuery table ID format"):
        helper._validate_table_id("project; drop table;")
    with pytest.raises(ValueError, match="BigQuery table_id cannot be empty"):
        helper._validate_table_id("")
