from src.processor import DocumentProcessor


def test_process_empty_text():
    processor = DocumentProcessor()
    word_count, tags = processor.process_text("")
    assert word_count == 0
    assert tags == ["document"]


def test_process_none_text():
    processor = DocumentProcessor()
    word_count, tags = processor.process_text(None)
    assert word_count == 0
    assert tags == ["document"]


def test_process_matching_keywords():
    processor = DocumentProcessor()
    text = "This is a simple serverless application running on gcp using python."
    word_count, tags = processor.process_text(text)

    assert word_count == 11
    assert "serverless" in tags
    assert "gcp" in tags
    assert "python" in tags
    assert "run" not in tags  # 'running' has no word boundary for 'run'


def test_process_no_matching_keywords():
    processor = DocumentProcessor()
    text = "Hello world! This has absolutely no special keywords."
    word_count, tags = processor.process_text(text)

    assert word_count == 8
    assert tags == ["document"]


def test_word_boundary_matching():
    processor = DocumentProcessor()
    # 'flaskapp' contains 'flask', but it should not match due to \b boundary.
    text = "Using flaskapp here."
    word_count, tags = processor.process_text(text)

    assert "flask" not in tags
    assert tags == ["document"]
