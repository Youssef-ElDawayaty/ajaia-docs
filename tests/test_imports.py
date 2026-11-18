import pytest
from docx import Document as DocxDocument

from database import create_database
from models import User
from services.documents import create_document
from services.imports import (
    ImportValidationError,
    import_document_file,
)


@pytest.fixture
def temp_database(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'imports.db').as_posix()}"
    engine, session_factory = create_database(database_url)
    yield engine, session_factory
    engine.dispose()


def demo_ids(session_factory):
    with session_factory() as session:
        return {
            user.email: user.id
            for user in session.query(User).order_by(User.id).all()
        }


def test_txt_import():
    html = import_document_file("notes.txt", b"First paragraph.\n\nSecond paragraph.")
    assert "<p>First paragraph.</p>" in html
    assert "<p>Second paragraph.</p>" in html


def test_markdown_import():
    html = import_document_file(
        "notes.md",
        b"# Heading\n\n**Bold** and *italic*\n\n- One\n- Two",
    )
    assert "<h1>" in html
    assert "<strong>" in html
    assert "<em>" in html
    assert "<ul>" in html
    assert "<li>" in html


def test_docx_import(tmp_path):
    source = tmp_path / "sample.docx"
    document = DocxDocument()
    heading = document.add_heading("Document Heading", level=1)
    heading.runs[0].bold = True

    paragraph = document.add_paragraph()
    bold = paragraph.add_run("Bold ")
    bold.bold = True
    italic = paragraph.add_run("Italic")
    italic.italic = True
    underlined = paragraph.add_run(" Underline")
    underlined.underline = True

    document.add_paragraph("List item", style="List Bullet")
    document.save(source)

    html = import_document_file("sample.docx", source.read_bytes())
    assert "<h1>" in html
    assert "<strong>" in html
    assert "<em>" in html
    assert "<u>" in html
    assert "<ul>" in html


def test_invalid_extension():
    with pytest.raises(ImportValidationError):
        import_document_file("notes.pdf", b"not a document")


def test_empty_files():
    with pytest.raises(ImportValidationError):
        import_document_file("empty.txt", b"")

    with pytest.raises(ImportValidationError):
        import_document_file("empty.md", b"   ")


def test_corrupted_docx():
    with pytest.raises(ImportValidationError):
        import_document_file("broken.docx", b"not a valid zip document")


def test_import_sanitizes_html():
    html = import_document_file(
        "unsafe.md",
        b"# Safe\n\n<script>alert('unsafe')</script><img src=x onerror=alert(1)>\n\n**Visible**",
    )
    assert "<h1>" in html
    assert "<strong>" in html
    assert "<script" not in html
    assert "<img" not in html
    assert "alert" not in html


def test_imported_document_ownership(temp_database):
    _, session_factory = temp_database
    ids = demo_ids(session_factory)

    with session_factory() as session:
        document = create_document(session, ids["youssef@example.com"], "Imported by Youssef")
        assert document.owner_id == ids["youssef@example.com"]
        assert document.owner_id != ids["sarah@example.com"]
