import sqlite3

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database import create_database, migrate_sharing_unique_index
from models import Document, DocumentShare, User
from services.documents import create_document
from services.sharing import share_document


def test_unique_index_exists_after_initialization(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'index.db').as_posix()}"
    engine, _ = create_database(database_url)

    with engine.connect() as connection:
        indexes = connection.exec_driver_sql("PRAGMA index_list(document_shares)").fetchall()
        unique_indexes = [row for row in indexes if row[2] == 1]
        assert any(row[1] == "uq_document_user_share_idx" for row in unique_indexes)

        index_info = connection.exec_driver_sql(
            "PRAGMA index_info(uq_document_user_share_idx)"
        ).fetchall()
        assert [row[2] for row in index_info] == ["document_id", "user_id"]

    engine.dispose()


def test_duplicate_shares_rejected_by_database(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'duplicates.db').as_posix()}"
    engine, session_factory = create_database(database_url)

    with session_factory() as session:
        owner = session.query(User).filter_by(email="youssef@example.com").first()
        other = session.query(User).filter_by(email="sarah@example.com").first()
        document = create_document(session, owner.id, "Database uniqueness")

        session.add(DocumentShare(
            document_id=document.id,
            user_id=other.id,
            permission="viewer",
        ))
        session.commit()

        with pytest.raises(IntegrityError):
            session.add(DocumentShare(
                document_id=document.id,
                user_id=other.id,
                permission="editor",
            ))
            session.commit()
        session.rollback()

    engine.dispose()


def test_repeated_initialization_preserves_existing_data(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'preserve.db').as_posix()}"
    engine, session_factory = create_database(database_url)

    with session_factory() as session:
        owner = session.query(User).filter_by(email="youssef@example.com").first()
        other = session.query(User).filter_by(email="sarah@example.com").first()
        document = create_document(session, owner.id, "Preserved document")
        share_document(session, document.id, owner.id, other.id, "editor")
        document_id = document.id

    repeated_engine, repeated_sessions = create_database(database_url)
    with repeated_sessions() as session:
        preserved_document = session.get(Document, document_id)
        assert preserved_document is not None
        assert preserved_document.title == "Preserved document"
        assert session.query(DocumentShare).filter_by(document_id=document_id).count() == 1

    engine.dispose()
    repeated_engine.dispose()


def test_legacy_duplicate_pairs_are_reported_without_deletion(tmp_path):
    database_path = tmp_path / "legacy.db"

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE document_shares ("
            "id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL, "
            "user_id INTEGER NOT NULL, permission VARCHAR(10) NOT NULL)"
        )
        connection.execute(
            "INSERT INTO document_shares (document_id, user_id, permission) "
            "VALUES (?, ?, ?)",
            (42, 7, "viewer"),
        )
        connection.execute(
            "INSERT INTO document_shares (document_id, user_id, permission) "
            "VALUES (?, ?, ?)",
            (42, 7, "editor"),
        )

    database_url = f"sqlite:///{database_path.as_posix()}"
    engine, _ = create_database(database_url)

    duplicates = migrate_sharing_unique_index(engine)
    assert duplicates == [(42, 7, 2)]

    with engine.connect() as connection:
        count = connection.execute(text(
            "SELECT COUNT(*) FROM document_shares"
        )).scalar_one()
        assert count == 2
        index_rows = connection.exec_driver_sql(
            "PRAGMA index_list(document_shares)"
        ).fetchall()
        assert not any(row[1] == "uq_document_user_share_idx" for row in index_rows)

    engine.dispose()
