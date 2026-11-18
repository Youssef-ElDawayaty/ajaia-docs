from io import BytesIO
from pathlib import Path

import markdown
from docx import Document as DocxDocument

from services.documents import sanitize_rich_text

MAX_IMPORT_SIZE_BYTES = 5 * 1024 * 1024
SUPPORTED_EXTENSIONS = {"txt", "md", "docx"}


class ImportValidationError(ValueError):
    pass


def validate_import_file(filename: str, size: int) -> str:
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension not in SUPPORTED_EXTENSIONS:
        raise ImportValidationError("Unsupported file type. Upload .txt, .md, or .docx only.")
    if size <= 0:
        raise ImportValidationError("The uploaded file is empty.")
    if size > MAX_IMPORT_SIZE_BYTES:
        raise ImportValidationError("The uploaded file exceeds the 5 MB size limit.")
    return extension


def import_txt(content: bytes) -> str:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportValidationError("The text file must use UTF-8 encoding.") from exc

    if not text.strip():
        raise ImportValidationError("The uploaded text file is empty.")

    paragraphs = [
        paragraph.strip()
        for paragraph in text.replace("\r\n", "\n").split("\n\n")
        if paragraph.strip()
    ]
    html = "".join(f"<p>{escape_inline(paragraph)}</p>" for paragraph in paragraphs)
    return sanitize_rich_text(html)


def escape_inline(text: str) -> str:
    from html import escape
    return escape(text).replace("\n", "<br>")


def import_markdown(content: bytes) -> str:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportValidationError("The Markdown file must use UTF-8 encoding.") from exc

    if not text.strip():
        raise ImportValidationError("The uploaded Markdown file is empty.")

    html = markdown.markdown(text, extensions=["extra", "sane_lists"])
    return sanitize_rich_text(html)


def import_docx(content: bytes) -> str:
    if not content:
        raise ImportValidationError("The uploaded DOCX file is empty.")

    try:
        document = DocxDocument(BytesIO(content))
    except Exception as exc:
        raise ImportValidationError("The uploaded DOCX file is invalid or corrupted.") from exc

    output: list[str] = []
    list_depth = 0

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue

        style_name = paragraph.style.name.lower() if paragraph.style and paragraph.style.name else ""
        if style_name.startswith("heading"):
            try:
                level = int("".join(character for character in style_name if character.isdigit()) or "1")
            except ValueError:
                level = 1
            level = min(max(level, 1), 6)
            output.append(f"<h{level}>{format_docx_runs(paragraph.runs)}</h{level}>")
        elif style_name.startswith("list"):
            if list_depth == 0:
                output.append("<ul>")
                list_depth = 1
            output.append(f"<li>{format_docx_runs(paragraph.runs)}</li>")
        else:
            if list_depth:
                output.append("</ul>")
                list_depth = 0
            output.append(f"<p>{format_docx_runs(paragraph.runs)}</p>")

    if list_depth:
        output.append("</ul>")

    html = "".join(output)
    if not html:
        raise ImportValidationError("The uploaded DOCX file contains no readable text.")
    return sanitize_rich_text(html)


def format_docx_runs(runs) -> str:
    from html import escape

    output: list[str] = []
    for run in runs:
        text = escape(run.text)
        if not text:
            continue
        if run.bold:
            text = f"<strong>{text}</strong>"
        if run.italic:
            text = f"<em>{text}</em>"
        if run.underline:
            text = f"<u>{text}</u>"
        output.append(text)
    return "".join(output)


def import_document_file(filename: str, content: bytes) -> str:
    extension = validate_import_file(filename, len(content))
    if extension == "txt":
        return import_txt(content)
    if extension == "md":
        return import_markdown(content)
    return import_docx(content)
