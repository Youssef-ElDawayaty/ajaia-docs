from datetime import datetime, timezone
from html import escape
from html.parser import HTMLParser
from typing import Sequence

from sqlalchemy.orm import Session

from models import Document
from services.sharing import require_editor_permission


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_document(session: Session, owner_id: int, title: str) -> Document:
    clean_title = title.strip()
    if not clean_title:
        raise ValueError("A document title is required.")

    document = Document(title=clean_title, content="", owner_id=owner_id)
    try:
        session.add(document)
        session.commit()
        session.refresh(document)
        return document
    except Exception:
        session.rollback()
        raise


def list_owned_documents(session: Session, owner_id: int) -> Sequence[Document]:
    return (
        session.query(Document)
        .filter(Document.owner_id == owner_id)
        .order_by(Document.updated_at.desc())
        .all()
    )


def get_owned_document(session: Session, document_id: int, owner_id: int) -> Document | None:
    return (
        session.query(Document)
        .filter(Document.id == document_id, Document.owner_id == owner_id)
        .first()
    )


def update_document_content(
    session: Session, document_id: int, owner_id: int, content: str
) -> Document:
    require_editor_permission(session, document_id, owner_id)
    document = session.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise LookupError("Document not found.")

    document.content = sanitize_rich_text(content)
    document.updated_at = utc_now()
    try:
        session.commit()
        session.refresh(document)
        return document
    except Exception:
        session.rollback()
        raise


def rename_document(
    session: Session, document_id: int, owner_id: int, title: str
) -> Document:
    clean_title = title.strip()
    if not clean_title:
        raise ValueError("A document title is required.")

    document = session.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise LookupError("Document not found.")
    if document.owner_id != owner_id:
        raise PermissionError("Only the document owner can rename this document.")

    document.title = clean_title
    document.updated_at = utc_now()
    try:
        session.commit()
        session.refresh(document)
        return document
    except Exception:
        session.rollback()
        raise


ALLOWED_RICH_TEXT_TAGS = {
    "p", "br", "strong", "b", "em", "i", "u",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "span", "blockquote",
}

SKIP_RICH_TEXT_CONTENT_TAGS = {"script", "style", "iframe", "object", "embed", "svg"}
BLOCKED_RICH_TEXT_VOID_TAGS = {"img", "video", "audio"}
BLOCKED_RICH_TEXT_TAGS = SKIP_RICH_TEXT_CONTENT_TAGS | BLOCKED_RICH_TEXT_VOID_TAGS


class RichTextSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.output: list[str] = []
        self.blocked_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in BLOCKED_RICH_TEXT_TAGS:
            if tag in SKIP_RICH_TEXT_CONTENT_TAGS:
                self.blocked_depth += 1
            return
        if self.blocked_depth:
            return
        if tag not in ALLOWED_RICH_TEXT_TAGS:
            return

        if tag == "span":
            class_name = next((value for name, value in attrs if name == "class"), None) or ""
            allowed_classes = [name for name in class_name.split() if name.startswith("ql-size-")]
            if allowed_classes:
                self.output.append(f'<span class="{escape(" ".join(allowed_classes), quote=True)}">')
            else:
                self.output.append("<span>")
        elif tag == "br":
            self.output.append("<br>")
        else:
            self.output.append(f"<{tag}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self.blocked_depth == 0 and tag in ALLOWED_RICH_TEXT_TAGS:
            self.output.append("<br>" if tag == "br" else f"<{tag}></{tag}>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in BLOCKED_RICH_TEXT_TAGS:
            if tag in SKIP_RICH_TEXT_CONTENT_TAGS and self.blocked_depth:
                self.blocked_depth -= 1
            return
        if self.blocked_depth:
            return
        if tag in ALLOWED_RICH_TEXT_TAGS:
            self.output.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self.blocked_depth:
            self.output.append(escape(data))


def sanitize_rich_text(content: str) -> str:
    value = content.strip()
    if not value:
        return ""

    if "<" not in value:
        return escape(value)

    parser = RichTextSanitizer()
    parser.feed(value)
    parser.close()
    return "".join(parser.output).strip()
