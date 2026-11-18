# Ajaia Docs

Ajaia Docs is a lightweight collaborative document workspace built as a Python and Streamlit assignment. It supports document creation, rich-text editing, sharing, and TXT, Markdown, and DOCX imports.

## Features

- Demo login by switching between Youssef and Sarah
- Create, open, rename, and save documents
- Persistent rich-text content with bold, italic, underline, headings, sizes, and lists
- Owner, editor, and viewer document permissions
- Shared With Me document section
- TXT, Markdown, and DOCX file imports
- Import review before creating a document
- SQLite persistence and database-level sharing uniqueness
- HTML sanitization for rich-text and imported content

## Technology Stack

- Python 3.10.19
- Streamlit 1.56.0
- SQLAlchemy
- SQLite
- Pytest
- streamlit-quill
- python-docx

## Project Structure

```text
Ajaia docs/
├── app.py
├── auth.py
├── database.py
├── models.py
├── requirements.txt
├── services/
│   ├── documents.py
│   ├── imports.py
│   └── sharing.py
├── tests/
│   ├── test_database_migration.py
│   ├── test_documents.py
│   ├── test_imports.py
│   ├── test_rich_text.py
│   └── test_sharing.py
├── README.md
├── ARCHITECTURE.md
├── AI_WORKFLOW.md
├── SUBMISSION.md
└── WALKTHROUGH.md
```

## Installation

From the project directory:

```powershell
python -m pip install -r requirements.txt
```

Python 3.10 is recommended for the assignment environment.

## Run Locally

```powershell
python -m streamlit run app.py
```

Open the local URL printed by Streamlit, normally `http://localhost:8501`.

## Demo Login

This project intentionally uses demo authentication rather than production authentication.

Use the sidebar selectbox to switch between:

- Youssef: `youssef@example.com`
- Sarah: `sarah@example.com`

The selected user ID is stored in Streamlit session state.

## Tests

Run the complete test suite:

```powershell
python -m pytest
```

Tests use temporary SQLite databases and do not replace or delete production document data.

## GitHub and Streamlit Deployment

1. Push this project to a GitHub repository.
2. Ensure `ajaia_docs.db`, `.env`, cache directories, and virtual environments are not committed; `.gitignore` excludes them.
3. In Streamlit Community Cloud, create a new app and select:
   - Repository: your GitHub repository
   - Branch: `main`
   - Main file path: `app.py`
   - Python dependencies: `requirements.txt`
4. Deploy. `app.py` calls database initialization automatically, so tables and demo users are created on startup.

SQLite storage on a hosted ephemeral filesystem is temporary. Documents may be reset when the hosted app restarts or redeploys. This project is therefore suitable for an assignment/demo deployment, not persistent production hosting.

## Known Limitations

- Demo authentication is not suitable for production.
- Deployment and live hosting are not implemented.
- DOCX conversion handles basic paragraphs, headings, emphasis, and list styles; complex layouts and embedded objects are not reproduced.
- Rich-text content is intentionally limited to safe HTML tags and classes.
