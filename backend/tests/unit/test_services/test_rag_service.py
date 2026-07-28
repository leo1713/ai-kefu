from app.services.rag_service import chunk_text


def test_document_chunking_basic() -> None:
    text = "A" * 1200
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) >= 3
    assert all(len(c) <= 500 for c in chunks)


def test_document_chunking_empty() -> None:
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_document_chunking_short_text() -> None:
    text = "退款政策：7天无理由退款。"
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_document_chunking_overlap() -> None:
    text = "0123456789" * 10  # 100 chars
    chunks = chunk_text(text, chunk_size=30, overlap=10)
    # With step=20, starting at 0,20,40,60,80 → 5 chunks
    assert len(chunks) == 5
    # Each chunk at most 30 chars
    assert all(len(c) <= 30 for c in chunks)
    # Overlap: end of chunk[0] overlaps start of chunk[1]
    assert chunks[0][-10:] == chunks[1][:10]


def test_document_chunking_preserves_content() -> None:
    text = "Hello world. " * 100
    chunks = chunk_text(text, chunk_size=200, overlap=20)
    # Reconstructed text (without overlap) covers original
    assert len(chunks) > 1
    assert all(c in text for c in chunks)
