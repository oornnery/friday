from app.agent.agents import get_file_metadata, process_message_with_files


def test_get_file_metadata_exists(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("content")

    meta = get_file_metadata(str(f))
    assert meta["name"] == "test.txt"
    assert meta["size_bytes"] == 7
    assert meta["content_snippet"] == "content"
    assert "error" not in meta


def test_get_file_metadata_missing():
    meta = get_file_metadata("non_existent_file.xyz")
    assert "error" in meta
    assert meta["error"] == "File not found"


def test_process_message_with_files_injection(tmp_path):
    # Setup a dummy file
    f = tmp_path / "readme.md"
    f.write_text("# Readme")

    # Run process
    # We need to change cwd or pass absolute path for the test to work transparently
    # OR we can mock get_file_metadata.
    # Let's use the file path relative to CWD?
    # process_message_with_files calls get_file_metadata which uses Path(path_str).
    # If we pass absolute path in message, it should work.

    msg = f"Summarize @{f}"

    processed = process_message_with_files(msg)

    assert f"@{f}" in processed  # Token remains
    assert "<file_context path=" in processed
    assert "# Readme" in processed
    assert "--- AUTO-INJECTED CONTEXT ---" in processed


def test_process_message_no_files():
    msg = "Hello world"
    processed = process_message_with_files(msg)
    assert processed == "Hello world"
