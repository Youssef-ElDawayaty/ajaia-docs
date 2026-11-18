from pathlib import Path
from typing import Optional

from sqlalchemy import Engine, event, create_engine
from sqlalchemy.orm import Session, sessionmaker

from models import Base, User

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "ajaia_docs.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"


def _enable_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def migrate_sharing_unique_index(engine: Engine) -> list[tuple[int, int, int]]:
    """Create the document-share unique index, unless duplicates require review."""
    with engine.begin() as connection:
        table_names = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_list").fetchall()
        }
        if "document_shares" not in table_names:
            return []

        duplicate_rows = connection.exec_driver_sql(
            """
            SELECT document_id, user_id, COUNT(*) AS duplicate_count
            FROM document_shares
            GROUP BY document_id, user_id
            HAVING COUNT(*) > 1
            ORDER BY document_id, user_id
            """
        ).fetchall()

        duplicates = [
            (int(document_id), int(user_id), int(count))
            for document_id, user_id, count in duplicate_rows
        ]
        if duplicates:
            import logging

            logging.warning(
                "Document-share duplicates detected; unique index not created. "
                "Duplicate pairs: %s",
                duplicates,
            )
            return duplicates

        connection.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "uq_document_user_share_idx "
            "ON document_shares(document_id, user_id)"
        )
        return []


def create_database(database_url: Optional[str] = None) -> tuple[Engine, sessionmaker[Session]]:
    url = database_url or DATABASE_URL
    engine = create_engine(url, connect_args={"check_same_thread": False})

    if url.startswith("sqlite:"):
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)

    Base.metadata.create_all(engine)
    migrate_sharing_unique_index(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

    seed_demo_users(session_factory)
    return engine, session_factory


def seed_demo_users(session_factory: sessionmaker[Session]) -> None:
    demo_users = (
        ("Youssef", "youssef@example.com"),
        ("Sarah", "sarah@example.com"),
    )

    with session_factory() as session:
        try:
            for name, email in demo_users:
                existing = session.query(User).filter(User.email == email).first()
                if existing is None:
                    session.add(User(name=name, email=email))
            session.commit()
        except Exception:
            session.rollback()
            raise


engine: Optional[Engine] = None
SessionLocal = sessionmaker(class_=Session, expire_on_commit=False)


def initialize_database(database_url: Optional[str] = None) -> sessionmaker[Session]:
    global engine, SessionLocal
    engine, SessionLocal = create_database(database_url)
    return SessionLocal
