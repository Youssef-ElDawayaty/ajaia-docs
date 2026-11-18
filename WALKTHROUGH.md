# Ajaia Docs Walkthrough Script

**Target length:** 3–5 minutes

## 0:00–0:30 — Introduction and Demo Login

“Hello, this is Ajaia Docs, a lightweight collaborative document workspace built with Python, Streamlit, SQLAlchemy, and SQLite.”

Open the application and show the sidebar. Select Youssef. Point out the demo user name and email and explain that this is demo-only switching, not production authentication.

## 0:30–1:15 — Create and Edit a Document

From My Documents, select “+ New Document.” Enter a title such as “Project Proposal” and create it. Show the document title and rich-text editor.

Demonstrate bold, italic, underline, a heading, and an ordered or bulleted list. Save the document. Briefly refresh or reopen it to show that formatting persisted.

## 1:15–2:00 — Import a File

Return to My Documents and use the file uploader. Choose a TXT, Markdown, or DOCX sample file. Explain that supported formats are limited to `.txt`, `.md`, and `.docx`, with a 5 MB upload limit.

Show the review pane and edit the imported title if desired. Clarify that the imported content is reviewed before creating a new document, and confirm the import.

## 2:00–3:00 — Share and Permissions

Open an owned document and expand “Share document.” Share it with Sarah as an editor. Explain that the owner can edit, rename, share, and revoke access.

Switch the sidebar to Sarah. Open Shared With Me and show the document and editor access. Edit the document and save it. Switch Sarah’s access to viewer by switching back to Youssef or use the existing permission control, then have Sarah reopen it and show the read-only preview.

Also briefly show the revoke control and explain that revoked users lose access.

## 3:00–3:30 — Closing

Summarize: documents are stored in SQLite, rich-text content is sanitized and persisted, sharing is owner-controlled, and imports convert files into the same rich-text representation.

Close by noting that this submission does not include a live deployment or production authentication.
