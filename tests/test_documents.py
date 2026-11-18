import pytest
from sqlalchemy import inspect

from database import create_database
from models import Document, User
from services.documents import (
    create_document,
    list_owned_documents,
    rename_document,
    update_document_content,
)


@pytest.fixture
def temp_database(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    engine, session_factory = create_database(database_url)
    yield database_url, engine, session_factory
    engine.dispose()


def get_demo_users(session_factory):
    with session_factory() as session:
        return {
            user.email: user.id
            for user in session.query(User).order_by(User.id).all()
        }


def test_database_initializes_and_seeds_users_without_duplicates(temp_database):
    database_url, engine, session_factory = temp_database

    inspector = inspect(engine)
    assert set(inspector.get_table_names()) >= {
        "users",
        "documents",
        "document_shares",
    }

    with session_factory() as session:
        users = session.query(User).order_by(User.email).all()
        assert [(user.name, user.email) for user in users] == [
            ("Sarah", "sarah@example.com"),
            ("Youssef", "youssef@example.com"),
        ]

    repeated_engine, _ = create_database(database_url)

    with session_factory() as session:
        assert session.query(User).count() == 2
        assert session.query(User).filter(User.email == "youssef@example.com").count() == 1
        assert session.query(User).filter(User.email == "sarah@example.com").count() == 1

    repeated_engine.dispose()


def test_create_document(temp_database):
    _, _, session_factory = temp_database
    owner_id = get_demo_users(session_factory)["youssef@example.com"]

    with session_factory() as session:
        document = create_document(session, owner_id, "Project Notes")

        assert document.id is not None
        assert document.title == "Project Notes"
        assert document.owner_id == owner_id
        assert document.created_at is not None
        assert document.updated_at is not None


def test_retrieve_documents_by_owner(temp_database):
    _, _, session_factory = temp_database
    user_ids = get_demo_users(session_factory)
    youssef_id = user_ids["youssef@example.com"]
    sarah_id = user_ids["sarah@example.com"]

    with session_factory() as session:
        create_document(session, youssef_id, "Youssef Document")
        create_document(session, sarah_id, "Sarah Document")

    with session_factory() as session:
        owned = list_owned_documents(session, youssef_id)
        assert [document.title for document in owned] == ["Youssef Document"]


def test_update_document_content(temp_database):
    _, _, session_factory = temp_database
    owner_id = get_demo_users(session_factory)["youssef@example.com"]

    with session_factory() as session:
        document = create_document(session, owner_id, "Draft")
        document_id = document.id
        updated = update_document_content(session, document_id, owner_id, "Saved content")
        assert updated.content == "Saved content"


def test_rename_document(temp_database):
    _, _, session_factory = temp_database
    owner_id = get_demo_users(session_factory)["youssef@example.com"]

    with session_factory() as session:
        document = create_document(session, owner_id, "Old title")
        renamed = rename_document(session, document.id, owner_id, "New title")
        assert renamed.title == "New title"


def test_user_cannot_edit_another_users_document(temp_database):
    _, _, session_factory = temp_database
    user_ids = get_demo_users(session_factory)
    owner_id = user_ids["youssef@example.com"]
    other_id = user_ids["sarah@example.com"]

    with session_factory() as session:
        document = create_document(session, owner_id, "Private Draft")

        with pytest.raises(PermissionError):
            update_document_content(session, document.id, other_id, "Unauthorized")

        with pytest.raises(PermissionError):
            rename_document(session, document.id, other_id, "Unauthorized title")


def test_document_persists_after_database_reinitialization(temp_database):
    database_url, engine, session_factory = temp_database
    owner_id = get_demo_users(session_factory)["youssef@example.com"]

    with session_factory() as session:
        document = create_document(session, owner_id, "Persistent Document")
        document_id = document.id
        update_document_content(session, document_id, owner_id, "Persistent content")

    engine.dispose()
    reinitialized_engine, reinitialized_sessions = create_database(database_url)

    with reinitialized_sessions() as session:
        document = session.get(Document, document_id)
        assert document is not None
        assert document.title == "Persistent Document"
        assert document.content == "Persistent content"

    reinitialized_engine.dispose()


def test_empty_title_is_rejected(temp_database):
    _, _, session_factory = temp_database
    owner_id = get_demo_users(session_factory)["youssef@example.com"]

    with session_factory() as session:
        with pytest.raises(ValueError):
            create_document(session, owner_id, "   ")
