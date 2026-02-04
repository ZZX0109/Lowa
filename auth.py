"""
登录与权限：学号/昵称登录，后台仅学号=mc565910admin、昵称=zixinadmin 可进入。
"""

import streamlit as st

ADMIN_ID = "mc565910admin"
ADMIN_NICKNAME = "zixinadmin"


def is_logged_in():
    return bool(st.session_state.get("user_id") is not None and st.session_state.get("user_id").strip())


def is_admin():
    return (
        st.session_state.get("user_id") == ADMIN_ID
        and st.session_state.get("nickname") == ADMIN_NICKNAME
    )


def login(user_id: str, nickname: str):
    st.session_state["user_id"] = (user_id or "").strip()
    st.session_state["nickname"] = (nickname or "").strip()
    st.session_state["is_admin"] = (
        st.session_state["user_id"] == ADMIN_ID and st.session_state["nickname"] == ADMIN_NICKNAME
    )


def logout():
    for k in ("user_id", "nickname", "is_admin"):
        st.session_state.pop(k, None)


def get_user_id():
    return st.session_state.get("user_id") or ""


def get_nickname():
    return st.session_state.get("nickname") or ""
