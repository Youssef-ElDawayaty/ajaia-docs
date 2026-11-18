from typing import Sequence

import streamlit as st

from models import User


def select_demo_user(users: Sequence[User]) -> User:
    labels = [f"{user.name} ({user.email})" for user in users]

    current_id = st.session_state.get("selected_user_id")
    current_index = next(
        (index for index, user in enumerate(users) if user.id == current_id),
        0,
    )

    selected_label = st.sidebar.selectbox(
        "Demo user",
        labels,
        index=current_index,
        help="Demo-only user switching; this is not production authentication.",
    )
    selected_user = users[labels.index(selected_label)]
    st.session_state.selected_user_id = selected_user.id

    st.sidebar.caption("Current demo user")
    st.sidebar.markdown(f"**{selected_user.name}**")
    st.sidebar.caption(selected_user.email)
    return selected_user
