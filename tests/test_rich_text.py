import pytest

from database import create_database
from models import Document, User
from services.documents import create_document, sanitize_rich_text, update_document_content
from services.sharing import share_document


@pytest.fixture
def temp_database(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'rich-text.db').as_posix()}"
    engine, session_factory = create_database(database_url)
    yield engine, session_factory
    engine.dispose()


def demo_ids(session_factory):
    with session_factory() as session:
        return {
            user.email: user.id
            for user in session.query(User).order_by(User.id).all()
        }


def test_save_and_reopen_formatted_content(temp_database):
    _, session_factory = temp_database
    ids = demo_ids(session_factory)
    formatted = (
        '<h2>Project plan</h2><p><strong>Bold</strong> and <em>italic</em></p>'
        '<p><u>Underlined</u></p><ul><li>First</li><li>Second</li></ul>'
    )

    with session_factory() as session:
        document = create_document(session, ids["youssef@example.com"], "Formatted")
        updated = update_document_content(
            session,
            document.id,
            ids["youssef@example.com"],
            formatted,
        )
        document_id = updated.id

    with session_factory() as session:
        reopened = session.get(Document, document_id)
        assert reopened is not None
        assert "<h2>" in reopened.content
        assert "<strong>" in reopened.content
        assert "<em>" in reopened.content
        assert "<u>" in reopened.content
        assert "<ul>" in reopened.content


def test_sanitizer_preserves_formatting_and_removes_unsafe_html():
    formatted = (
        '<h1>Heading</h1><p><strong>Bold</strong><em>Italic</em></p>'
        '<ol><li>One</li></ol><script>alert("unsafe")</script>'
        '<img src="x" onerror="alert(1)"><a href="javascript:alert(1)">Link</a>'
    )

    safe = sanitize_rich_text(formatted)

    assert "<h1>" in safe
    assert "<strong>" in safe
    assert "<em>" in safe
    assert "<ol>" in safe
    assert "<li>" in safe
    assert "<script" not in safe
    assert "alert" not in safe
    assert "<img" not in safe
    assert "javascript:" not in safe


def test_viewer_cannot_save_formatted_content(temp_database):
    _, session_factory = temp_database
    ids = demo_ids(session_factory)

    with session_factory() as session:
        document = create_document(session, ids["youssef@example.com"], "Viewer test")
        share_document(
            session,
            document.id,
            ids["youssef@example.com"],
            ids["sarah@example.com"],
            "viewer",
        )

        with pytest.raises(PermissionError):
            update_document_content(
                session,
                document.id,
                ids["sarah@example.com"],
                '<p><strong>Unauthorized</strong></p>',
            )


def test_editor_can_save_formatted_content(temp_database):
    _, session_factory = temp_database
    ids = demo_ids(session_factory)

    with session_factory() as session:
        document = create_document(session, ids["youssef@example.com"], "Editor test")
        share_document(
            session,
            document.id,
            ids["youssef@example.com"],
            ids["sarah@example.com"],
            "editor",
        )
        updated = update_document_content(
            session,
            document.id,
            ids["sarah@example.com"],
            '<h2>Editor</h2><p><u>Formatted</u></p>',
        )

        assert "<h2>" in updated.content
        assert "<u>" in updated.content


def test_owner_can_save_formatted_content(temp_database):
    _, session_factory = temp_database
    ids = demo_ids(session_factory)

    with session_factory() as session:
        document = create_document(session, ids["youssef@example.com"], "Owner test")
        updated = update_document_content(
            session,
            document.id,
            ids["youssef@example.com"],
            '<h1>Owner</h1><ol><li>One</li></ol>',
        )

        assert "<h1>" in updated.content
        assert "<ol>" in updated.content
