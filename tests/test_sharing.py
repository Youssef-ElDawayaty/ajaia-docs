import pytest

from database import create_database
from models import DocumentShare, User
from services.documents import create_document, rename_document, update_document_content
from services.sharing import (
    get_document_permission,
    list_shared_documents,
    revoke_document_access,
    share_document,
)


@pytest.fixture
def temp_database(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'sharing.db').as_posix()}"
    engine, session_factory = create_database(database_url)
    yield engine, session_factory
    engine.dispose()


def demo_ids(session_factory):
    with session_factory() as session:
        return {
            user.email: user.id
            for user in session.query(User).order_by(User.id).all()
        }


def test_sharing_document(temp_database):
    _, session_factory = temp_database
    ids = demo_ids(session_factory)

    with session_factory() as session:
        document = create_document(session, ids["youssef@example.com"], "Shared Draft")
        share = share_document(
            session,
            document.id,
            ids["youssef@example.com"],
            ids["sarah@example.com"],
            "editor",
        )

        assert share.document_id == document.id
        assert share.user_id == ids["sarah@example.com"]
        assert share.permission == "editor"


def test_viewer_access(temp_database):
    _, session_factory = temp_database
    ids = demo_ids(session_factory)

    with session_factory() as session:
        document = create_document(session, ids["youssef@example.com"], "Read Only")
        share_document(
            session,
            document.id,
            ids["youssef@example.com"],
            ids["sarah@example.com"],
            "viewer",
        )

        assert get_document_permission(session, document.id, ids["sarah@example.com"]) == "viewer"
        with pytest.raises(PermissionError):
            update_document_content(
                session,
                document.id,
                ids["sarah@example.com"],
                "Not allowed",
            )
        with pytest.raises(PermissionError):
            rename_document(
                session,
                document.id,
                ids["sarah@example.com"],
                "Not allowed",
            )


def test_editor_access(temp_database):
    _, session_factory = temp_database
    ids = demo_ids(session_factory)

    with session_factory() as session:
        document = create_document(session, ids["youssef@example.com"], "Editable")
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
            "Edited by Sarah",
        )
        assert updated.content == "Edited by Sarah"
        with pytest.raises(PermissionError):
            rename_document(
                session,
                document.id,
                ids["sarah@example.com"],
                "Editor rename",
            )


def test_owner_permissions(temp_database):
    _, session_factory = temp_database
    ids = demo_ids(session_factory)

    with session_factory() as session:
        document = create_document(session, ids["youssef@example.com"], "Owner Document")

        assert get_document_permission(session, document.id, ids["youssef@example.com"]) == "owner"
        update_document_content(session, document.id, ids["youssef@example.com"], "Owner edit")
        renamed = rename_document(session, document.id, ids["youssef@example.com"], "Owner Rename")
        assert renamed.title == "Owner Rename"


def test_unauthorized_access_rejection(temp_database):
    _, session_factory = temp_database
    ids = demo_ids(session_factory)

    with session_factory() as session:
        document = create_document(session, ids["youssef@example.com"], "Private")

        assert get_document_permission(session, document.id, ids["sarah@example.com"]) is None
        with pytest.raises(PermissionError):
            update_document_content(session, document.id, ids["sarah@example.com"], "Hack")


def test_revoking_access(temp_database):
    _, session_factory = temp_database
    ids = demo_ids(session_factory)

    with session_factory() as session:
        document = create_document(session, ids["youssef@example.com"], "Revoke Me")
        share_document(
            session,
            document.id,
            ids["youssef@example.com"],
            ids["sarah@example.com"],
            "editor",
        )
        revoke_document_access(
            session,
            document.id,
            ids["youssef@example.com"],
            ids["sarah@example.com"],
        )

        assert get_document_permission(session, document.id, ids["sarah@example.com"]) is None


def test_updating_permission(temp_database):
    _, session_factory = temp_database
    ids = demo_ids(session_factory)

    with session_factory() as session:
        document = create_document(session, ids["youssef@example.com"], "Permission Change")
        share_document(
            session,
            document.id,
            ids["youssef@example.com"],
            ids["sarah@example.com"],
            "viewer",
        )
        share_document(
            session,
            document.id,
            ids["youssef@example.com"],
            ids["sarah@example.com"],
            "editor",
        )

        assert get_document_permission(session, document.id, ids["sarah@example.com"]) == "editor"


def test_duplicate_shares_are_prevented(temp_database):
    _, session_factory = temp_database
    ids = demo_ids(session_factory)

    with session_factory() as session:
        document = create_document(session, ids["youssef@example.com"], "No Duplicates")
        share_document(
            session,
            document.id,
            ids["youssef@example.com"],
            ids["sarah@example.com"],
            "viewer",
        )
        share_document(
            session,
            document.id,
            ids["youssef@example.com"],
            ids["sarah@example.com"],
            "viewer",
        )

        assert session.query(DocumentShare).filter(
            DocumentShare.document_id == document.id,
            DocumentShare.user_id == ids["sarah@example.com"],
        ).count() == 1


def test_shared_with_me_listing(temp_database):
    _, session_factory = temp_database
    ids = demo_ids(session_factory)

    with session_factory() as session:
        document = create_document(session, ids["youssef@example.com"], "Shared Listing")
        share_document(
            session,
            document.id,
            ids["youssef@example.com"],
            ids["sarah@example.com"],
            "viewer",
        )

        shared = list_shared_documents(session, ids["sarah@example.com"])
        assert [item.title for item in shared] == ["Shared Listing"]
