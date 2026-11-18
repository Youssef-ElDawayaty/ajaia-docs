from pathlib import Path

import streamlit as st
from streamlit_quill import st_quill

from auth import select_demo_user
from database import initialize_database
from models import Document, User
from services.documents import (
    create_document,
    get_owned_document,
    list_owned_documents,
    rename_document,
    sanitize_rich_text,
    update_document_content,
)
from services.sharing import (
    get_accessible_document,
    get_document_permission,
    list_document_shares,
    list_shared_documents,
    revoke_document_access,
    share_document,
)
from services.imports import ImportValidationError, import_document_file

initialize_database()
from database import SessionLocal


st.set_page_config(page_title="Ajaia Docs", page_icon="D", layout="wide")

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { background: #f8fafc; border-right: 1px solid #e2e8f0; }
    .block-container { max-width: 1180px; padding-top: 2rem; }
    .app-title { font-size: 2rem; font-weight: 700; color: #0f172a; }
    .section-title { font-size: 1.15rem; font-weight: 700; color: #1e293b; }
    .empty-card { border: 1px dashed #cbd5e1; border-radius: 12px; padding: 2rem;
                   text-align: center; color: #64748b; background: #ffffff; }
    .document-card { border: 1px solid #e2e8f0; border-radius: 10px; padding: 1rem;
                     background: #ffffff; margin-bottom: 0.75rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


with st.sidebar:
    st.markdown("### Ajaia Docs")
    st.caption("Collaborative workspace")
    st.divider()

    try:
        with SessionLocal() as session:
            users = session.query(User).order_by(User.id).all()
    except Exception:
        st.error("The application could not open the demo workspace.")
        st.stop()

    if not users:
        st.error("No demo users are available.")
        st.stop()

    selected_user = select_demo_user(users)
    if st.session_state.get("document_owner_id") != selected_user.id:
        st.session_state.pop("selected_document_id", None)
        st.session_state.document_owner_id = selected_user.id

    st.divider()
    st.caption("Navigation")
    page = st.radio("Workspace", ["My Documents", "Shared With Me"], label_visibility="collapsed")


st.markdown('<div class="app-title">Ajaia Docs</div>', unsafe_allow_html=True)
st.caption("Demo collaborative document workspace")

selected_document_id = st.session_state.get("selected_document_id")

if selected_document_id is not None:
    try:
        with SessionLocal() as session:
            selected_document = get_accessible_document(
                session, int(selected_document_id), selected_user.id
            )
    except Exception:
        selected_document = None

    if selected_document is None:
        st.warning("This document is missing or is not owned by the current user.")
        if st.button("Back to My Documents"):
            st.session_state.pop("selected_document_id", None)
            st.rerun()
    else:
        top_left, top_right = st.columns([5, 1])
        with top_left:
            st.markdown(f'<div class="section-title">{selected_document.title}</div>', unsafe_allow_html=True)
        with top_right:
            if st.button("Back", use_container_width=True):
                st.session_state.pop("selected_document_id", None)
                st.rerun()

        try:
            with SessionLocal() as session:
                permission = get_document_permission(
                    session, selected_document.id, selected_user.id
                )
        except Exception:
            permission = None

        st.caption(f"Access level: **{permission or 'none'}**")

        if permission == "owner":
            with st.expander("Rename document"):
                new_title = st.text_input(
                    "Title",
                    value=selected_document.title,
                    key=f"rename_title_{selected_document.id}",
                )
                if st.button("Save title", key=f"rename_{selected_document.id}"):
                    try:
                        with SessionLocal() as session:
                            rename_document(
                                session,
                                selected_document.id,
                                selected_user.id,
                                new_title,
                            )
                        st.success("Document title updated.")
                        st.rerun()
                    except ValueError as exc:
                        st.warning(str(exc))
                    except PermissionError as exc:
                        st.error(str(exc))
                    except Exception:
                        st.error("The document title could not be updated.")

        can_edit = permission in {"owner", "editor"}
        safe_content = sanitize_rich_text(selected_document.content)

        if can_edit:
            rich_toolbar = [
                ["bold", "italic", "underline"],
                [{"header": [1, 2, 3, False]}],
                [{"size": ["small", False, "large", "huge"]}],
                [{"list": "ordered"}, {"list": "bullet"}],
                ["clean"],
            ]
            content = st_quill(
                value=safe_content,
                html=True,
                toolbar=rich_toolbar,
                readonly=False,
                key=f"quill_{selected_document.id}",
            )
            if st.button("Save", type="primary"):
                try:
                    with SessionLocal() as session:
                        update_document_content(
                            session,
                            selected_document.id,
                            selected_user.id,
                            content or "",
                        )
                    st.success("Document saved.")
                except PermissionError as exc:
                    st.error(str(exc))
                except Exception:
                    st.error("The document could not be saved.")
        else:
            st.markdown("### Document preview")
            st.markdown(safe_content, unsafe_allow_html=True)
            st.info("This document is read-only because you have viewer access.")

        if permission == "owner":
            with st.expander("Share document", expanded=False):
                try:
                    with SessionLocal() as session:
                        available_users = session.query(User).filter(User.id != selected_user.id).order_by(User.name).all()
                        shares = list_document_shares(
                            session, selected_document.id, selected_user.id
                        )
                except Exception:
                    available_users = []
                    shares = []

                if available_users:
                    share_labels = [f"{user.name} ({user.email})" for user in available_users]
                    selected_share_label = st.selectbox(
                        "User",
                        share_labels,
                        key=f"share_user_{selected_document.id}",
                    )
                    selected_share_user = available_users[share_labels.index(selected_share_label)]
                    share_permission = st.selectbox(
                        "Permission",
                        ["viewer", "editor"],
                        key=f"share_permission_{selected_document.id}",
                    )
                    if st.button("Apply access", key=f"apply_share_{selected_document.id}"):
                        try:
                            with SessionLocal() as session:
                                share_document(
                                    session,
                                    selected_document.id,
                                    selected_user.id,
                                    selected_share_user.id,
                                    share_permission,
                                )
                            st.success("Access updated.")
                            st.rerun()
                        except (LookupError, PermissionError, ValueError) as exc:
                            st.error(str(exc))
                        except Exception:
                            st.error("Access could not be updated.")

                if shares:
                    st.markdown("**Current access**")
                    for share in shares:
                        with SessionLocal() as session:
                            shared_user = session.get(User, share.user_id)
                        if shared_user is None:
                            continue
                        share_col, revoke_col = st.columns([4, 1])
                        with share_col:
                            st.write(f"{shared_user.name} — {share.permission}")
                        with revoke_col:
                            if st.button("Revoke", key=f"revoke_{share.id}"):
                                try:
                                    with SessionLocal() as session:
                                        revoke_document_access(
                                            session,
                                            selected_document.id,
                                            selected_user.id,
                                            shared_user.id,
                                        )
                                    st.success("Access revoked.")
                                    st.rerun()
                                except (LookupError, PermissionError) as exc:
                                    st.error(str(exc))
                                except Exception:
                                    st.error("Access could not be revoked.")
                else:
                    st.caption("This document has not been shared with anyone.")

        st.caption(f"Last updated: {selected_document.updated_at.strftime('%b %d, %Y at %H:%M')}")
else:
    left, right = st.columns([5, 1], vertical_alignment="bottom")
    with left:
        st.markdown(f'<div class="section-title">{page}</div>', unsafe_allow_html=True)
    with right:
        if page == "My Documents" and st.button("+ New Document", type="primary", use_container_width=True):
            st.session_state.show_new_document = True

    if st.session_state.get("show_new_document", False):
        with st.form("new_document_form", clear_on_submit=True):
            title = st.text_input("Document title", placeholder="Untitled document")
            submitted = st.form_submit_button("Create")
            cancelled = st.form_submit_button("Cancel")

            if submitted:
                try:
                    with SessionLocal() as session:
                        document = create_document(session, selected_user.id, title)
                    st.session_state.show_new_document = False
                    st.session_state.selected_document_id = document.id
                    st.session_state.document_owner_id = selected_user.id
                    st.success("Document created.")
                    st.rerun()
                except ValueError as exc:
                    st.warning(str(exc))
                except Exception:
                    st.error("The document could not be created.")
            elif cancelled:
                st.session_state.show_new_document = False
                st.rerun()

    st.divider()

    if page == "My Documents":
        uploaded_file = st.file_uploader(
            "Import a document",
            type=["txt", "md", "docx"],
            help="Supported formats: TXT, Markdown, and DOCX. Maximum size: 5 MB.",
            key="document_import_uploader",
        )

        if uploaded_file is not None:
            upload_signature = f"{uploaded_file.name}:{uploaded_file.size}"
            if st.session_state.get("import_signature") != upload_signature:
                try:
                    imported_html = import_document_file(
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                    )
                    default_title = Path(uploaded_file.name).stem.strip() or "Imported document"
                    st.session_state.import_signature = upload_signature
                    st.session_state.import_title = default_title
                    st.session_state.import_html = imported_html
                    st.session_state.import_ready = True
                    st.success("File converted successfully. Review it before importing.")
                except ImportValidationError as exc:
                    st.warning(str(exc))
                    st.session_state.import_ready = False
                except Exception:
                    st.error("The file could not be read or converted.")
                    st.session_state.import_ready = False

        if st.session_state.get("import_ready", False):
            with st.expander("Review imported document", expanded=True):
                import_title = st.text_input(
                    "Imported document title",
                    value=st.session_state.get("import_title", "Imported document"),
                    key="import_title_review",
                )
                import_html = st_quill(
                    value=st.session_state.get("import_html", ""),
                    html=True,
                    key="import_content_review",
                )

                confirm_col, cancel_col = st.columns([1, 1])
                with confirm_col:
                    if st.button("Import document", type="primary"):
                        try:
                            with SessionLocal() as session:
                                document = create_document(
                                    session,
                                    selected_user.id,
                                    import_title,
                                )
                                update_document_content(
                                    session,
                                    document.id,
                                    selected_user.id,
                                    import_html or "",
                                )
                            st.session_state.import_ready = False
                            st.session_state.pop("import_signature", None)
                            st.session_state.selected_document_id = document.id
                            st.session_state.document_owner_id = selected_user.id
                            st.success("Imported document created.")
                            st.rerun()
                        except ValueError as exc:
                            st.warning(str(exc))
                        except PermissionError as exc:
                            st.error(str(exc))
                        except Exception:
                            st.error("The imported document could not be created.")
                with cancel_col:
                    if st.button("Cancel import"):
                        st.session_state.import_ready = False
                        st.session_state.pop("import_signature", None)
                        st.rerun()

    if page == "My Documents":
        try:
            with SessionLocal() as session:
                documents = list_owned_documents(session, selected_user.id)
        except Exception:
            st.error("Your documents could not be loaded.")
            documents = []

        if not documents:
            st.markdown(
                '<div class="empty-card"><strong>No documents yet</strong><br>Create a document to start writing.</div>',
                unsafe_allow_html=True,
            )
        else:
            for document in documents:
                card_left, card_right = st.columns([5, 1])
                with card_left:
                    st.markdown("<div class='document-card'>", unsafe_allow_html=True)
                    st.markdown(f"**{document.title}**")
                    st.caption(f"Updated {document.updated_at.strftime('%b %d, %Y at %H:%M')}")
                    st.markdown("</div>", unsafe_allow_html=True)
                with card_right:
                    if st.button("Open", key=f"open_{document.id}", use_container_width=True):
                        st.session_state.selected_document_id = document.id
                        st.session_state.document_owner_id = selected_user.id
                        st.rerun()
    else:
        try:
            with SessionLocal() as session:
                shared_documents = list_shared_documents(session, selected_user.id)
        except Exception:
            st.error("Shared documents could not be loaded.")
            shared_documents = []

        if not shared_documents:
            st.markdown(
                '<div class="empty-card"><strong>No shared documents</strong><br>Documents shared with you will appear here.</div>',
                unsafe_allow_html=True,
            )
        else:
            for document in shared_documents:
                card_left, card_right = st.columns([5, 1])
                with card_left:
                    try:
                        with SessionLocal() as session:
                            permission = get_document_permission(
                                session, document.id, selected_user.id
                            )
                            owner_name = document.owner.name
                    except Exception:
                        permission = None
                        owner_name = "Unknown owner"

                    st.markdown("<div class='document-card'>", unsafe_allow_html=True)
                    st.markdown(f"**{document.title}**")
                    st.caption(
                        f"Owner: {owner_name} · Access: {permission or 'none'} · "
                        f"Updated {document.updated_at.strftime('%b %d, %Y at %H:%M')}"
                    )
                    st.markdown("</div>", unsafe_allow_html=True)
                with card_right:
                    if st.button("Open", key=f"open_shared_{document.id}", use_container_width=True):
                        st.session_state.selected_document_id = document.id
                        st.session_state.document_owner_id = selected_user.id
                        st.rerun()
