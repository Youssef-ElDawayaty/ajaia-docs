# Ajaia Docs Architecture

## Overview

Ajaia Docs uses a small, modular Python architecture:

- Streamlit provides the browser UI and demo session state.
- SQLAlchemy models define SQLite persistence and relationships.
- Service modules contain document, sharing, permission, and import operations.
- Pytest uses temporary SQLite databases for isolated verification.

## Streamlit UI

`app.py` builds the dashboard, sidebar demo-user selector, document list, editor, sharing controls, and import review flow. UI code calls service functions but does not contain document persistence rules.

Streamlit reruns the application script as interactions change. Session state identifies the selected demo user and currently opened document. The sidebar also controls My Documents and Shared With Me navigation.

## Service Layer

- `services/documents.py` creates, lists, retrieves, renames, and updates documents.
- `services/sharing.py` creates and revokes shares, resolves permissions, and lists shared documents.
- `services/imports.py` validates and converts TXT, Markdown, and DOCX files.

Services manage SQLAlchemy commits and rollbacks and raise meaningful validation or permission errors for the UI.

## Database and SQLAlchemy

`database.py` creates a SQLite engine for `ajaia_docs.db`, enables `PRAGMA foreign_keys=ON`, creates tables, seeds demo users, and runs a repeatable sharing-index migration.

`models.py` defines:

- `User`: demo users and relationships.
- `Document`: title, HTML/text content, owner, and timestamps.
- `DocumentShare`: document/user pair and viewer/editor permission.

A unique index on `(document_id, user_id)` prevents duplicate share records. The migration first reports duplicate pairs and does not delete existing records when duplicates already exist.

## Ownership and Permissions

Every document has an `owner_id`. The sharing service resolves one of four effective states:

- `owner`: view, edit, rename, share, and revoke access.
- `editor`: view and edit content.
- `viewer`: view content only.
- no access: document cannot be opened or modified.

Permission enforcement exists in service functions rather than only in Streamlit controls.

## Rich-Text Storage

Rich-text content is stored as HTML in the existing `Document.content` text column. Streamlit Quill produces formatted HTML for editing. A server-side allowlist sanitizer removes unsafe elements and attributes before persistence and rendering.

Plain text remains plain text for backward compatibility; imported HTML is sanitized before storage.

## File Import Flow

1. The user selects a TXT, Markdown, or DOCX file.
2. The import service validates extension, encoding, size, and readability.
3. TXT text becomes paragraphs; Markdown is converted to HTML; DOCX paragraphs, emphasis, headings, and simple lists become HTML.
4. Imported HTML passes through the existing rich-text sanitizer.
5. The user reviews and edits the title/content in Streamlit.
6. Confirming creates a new document owned by the selected demo user.

Importing never overwrites an existing document automatically.
