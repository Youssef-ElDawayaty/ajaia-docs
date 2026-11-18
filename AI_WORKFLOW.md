# AI Workflow and Review Notes

## AI Tools Used

ChatGPT was used for planning, architecture discussions, implementation prompts, code review, and debugging guidance. Claude Code was used to generate and modify project files. Human review and automated tests were used before considering implementation changes complete.

## How AI Output Was Reviewed

AI-generated code was reviewed against the project requirements and the existing workspace rather than blindly accepted. The main review steps were:

- Inspecting existing files before changes.
- Checking SQLAlchemy relationships and foreign-key behavior.
- Running Python tests after each major implementation stage.
- Starting Streamlit and checking HTTP reachability.
- Reviewing editor diagnostics and terminal startup output.
- Keeping temporary-database tests separate from `ajaia_docs.db`.

## Examples of Corrections

The following are verified corrections made during the project:

1. Rich-text plain-text compatibility: an initial sanitizer implementation wrapped plain text in paragraph tags. Existing tests expected plain text to remain unchanged, so the implementation was corrected to preserve plain text while sanitizing actual HTML.
2. Database migration: the migration logic was extended to inspect duplicate `(document_id, user_id)` pairs before creating a unique index. Duplicate pairs are reported and existing rows are preserved instead of silently deleted.
3. SQLite index verification: migration tests were added to confirm the index name and indexed columns rather than assuming that a model constraint was sufficient for an existing database.
4. Dependency decisions: package inspection was performed before adding rich-text or DOCX support. `streamlit-quill` and `python-docx` were installed only after package size and requirements were checked and approval was obtained.

These examples are based on observed implementation issues and test failures. This document does not claim exhaustive automated or visual browser testing.

## Testing and Manual Verification

The final test suite uses temporary SQLite databases. The complete suite was executed with `python -m pytest` and passed 34 tests. Streamlit was started with `python -m streamlit run app.py`, and the local endpoint returned HTTP 200.

Manual verification still needs to confirm the complete browser interaction flow, including Quill formatting behavior, import preview editing, permission changes, and the appearance of Shared With Me for both demo users.
