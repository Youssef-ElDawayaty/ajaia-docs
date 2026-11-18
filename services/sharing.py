"""Document-sharing operations and permission checks."""

from typing import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Document, DocumentShare, User


def get_document_permission(
    session: Session, document_id: int, user_id: int
) -> str | None:
    document = session.query(Document).filter(Document.id == document_id).first()
    if document is None:
        return None
    if document.owner_id == user_id:
        return "owner"

    share = (
        session.query(DocumentShare)
        .filter(
            DocumentShare.document_id == document_id,
            DocumentShare.user_id == user_id,
        )
        .first()
    )
    return share.permission if share is not None else None


def get_accessible_document(
    session: Session, document_id: int, user_id: int
) -> Document | None:
    if get_document_permission(session, document_id, user_id) is None:
        return None
    return session.query(Document).filter(Document.id == document_id).first()


def require_document_access(
    session: Session, document_id: int, user_id: int
) -> str:
    permission = get_document_permission(session, document_id, user_id)
    if permission is None:
        raise PermissionError("You do not have access to this document.")
    return permission


def require_editor_permission(
    session: Session, document_id: int, user_id: int
) -> None:
    permission = require_document_access(session, document_id, user_id)
    if permission not in {"owner", "editor"}:
        raise PermissionError("You do not have permission to edit this document.")


def share_document(
    session: Session,
    document_id: int,
    owner_id: int,
    user_id: int,
    permission: str,
) -> DocumentShare:
    document = session.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise LookupError("Document not found.")
    if document.owner_id != owner_id:
        raise PermissionError("Only the document owner can change sharing.")
    if user_id == owner_id:
        raise ValueError("A document cannot be shared with its owner.")
    if permission not in {"viewer", "editor"}:
        raise ValueError("Permission must be either viewer or editor.")

    existing = (
        session.query(DocumentShare)
        .filter(
            DocumentShare.document_id == document_id,
            DocumentShare.user_id == user_id,
        )
        .first()
    )
    if existing is not None:
        existing.permission = permission
        try:
            session.commit()
            session.refresh(existing)
            return existing
        except Exception:
            session.rollback()
            raise

    target_user = session.query(User).filter(User.id == user_id).first()
    if target_user is None:
        raise LookupError("Selected user not found.")

    share = DocumentShare(
        document_id=document_id,
        user_id=user_id,
        permission=permission,
    )
    try:
        session.add(share)
        session.commit()
        session.refresh(share)
        return share
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("This document is already shared with the selected user.") from exc
    except Exception:
        session.rollback()
        raise


def revoke_document_access(
    session: Session, document_id: int, owner_id: int, user_id: int
) -> None:
    document = session.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise LookupError("Document not found.")
    if document.owner_id != owner_id:
        raise PermissionError("Only the document owner can revoke sharing.")

    share = (
        session.query(DocumentShare)
        .filter(
            DocumentShare.document_id == document_id,
            DocumentShare.user_id == user_id,
        )
        .first()
    )
    if share is None:
        raise LookupError("This user does not have access to the document.")

    try:
        session.delete(share)
        session.commit()
    except Exception:
        session.rollback()
        raise


def list_document_shares(
    session: Session, document_id: int, owner_id: int
) -> Sequence[DocumentShare]:
    document = session.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise LookupError("Document not found.")
    if document.owner_id != owner_id:
        raise PermissionError("Only the document owner can view sharing settings.")

    return (
        session.query(DocumentShare)
        .filter(DocumentShare.document_id == document_id)
        .order_by(DocumentShare.user_id)
        .all()
    )


def list_shared_documents(session: Session, user_id: int) -> Sequence[Document]:
    return (
        session.query(Document)
        .join(DocumentShare, DocumentShare.document_id == Document.id)
        .filter(DocumentShare.user_id == user_id)
        .order_by(Document.updated_at.desc())
        .all()
    )
