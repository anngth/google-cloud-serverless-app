import re
import logging

logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self):
        # List of keywords to detect for simulated OCR indexing
        self.keywords = [
            "gcp",
            "serverless",
            "pipeline",
            "event-driven",
            "data",
            "cloud",
            "storage",
            "pubsub",
            "bigquery",
            "run",
            "python",
            "flask",
            "ocr",
            "google",
            "architecture",
            "metadata",
        ]

    def process_text(self, text_content):
        """
        Parses text content to extract word count and match keywords as tags.
        """
        if not text_content:
            return 0, ["document"]

        # Calculate word count
        words = text_content.split()
        word_count = len(words)

        # Extract matching tags
        found_tags = []
        text_lower = text_content.lower()
        for kw in self.keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                found_tags.append(kw)

        if not found_tags:
            found_tags = ["document"]

        logger.info(f"Processed content: word_count={word_count}, tags={found_tags}")
        return word_count, found_tags
