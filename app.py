"""
行为经济学实验 · 爱荷华赌博任务 - 统一入口
运行: streamlit run app.py
登录：学号 + 昵称；后台仅管理员可进入，非管理员侧栏与页面均无后台入口。
数据按学号隔离，普通用户仅能提交/查看与己相关的内容。
"""

import streamlit as st
from igt_env import IGTEnv
from auth import is_logged_in, is_admin, login, logout, get_user_id, get_nickname
from deck_config import load_config, save_config, get_decks, get_allow_user_edit
from i18n import t, get_lang, set_lang
from submission_store import (
    get_all,
    get_all_grouped_by_user,
    self_play_to_csv_rows,
    model_run_to_csv_rows,
    to_csv_string,
    list_users,
    delete_user_data,
)

st.set_page_config(page_title="爱荷华赌博任务 · 实验室", page_icon="🃏", layout="wide")
if "lang" not in st.session_state:
    st.session_state.lang = "zh"

# 未登录时：先选语言，再显示登录表单
if not is_logged_in():
    # 登录口就设置语言（放在最上方）
    lang_col, _ = st.columns([1, 3])
    with lang_col:
        new_lang = st.selectbox(
            "Language / 语言",
            options=["zh", "en"],
            index=0 if get_lang() == "zh" else 1,
            format_func=lambda x: t("lang_zh") if x == "zh" else t("lang_en"),
            key="lang_login",
        )
        if new_lang != get_lang():
            set_lang(new_lang)
            st.rerun()
    st.title("🃏 " + t("app_title"))
    st.caption(t("login_caption"))
    with st.form("login_form"):
        user_id = st.text_input(t("label_student_id"), placeholder=t("placeholder_student_id"), max_chars=20)
        nickname = st.text_input(t("label_nickname"), placeholder=t("placeholder_nickname"))
        submitted = st.form_submit_button(t("btn_enter"))
        if submitted:
            uid = (user_id or "").strip()
            nick = (nickname or "").strip()
            if not uid or not nick:
                st.warning(t("warning_fill"))
            elif uid == "mc565910admin" and nick == "zixinadmin":
                login(uid, nick)
                st.rerun()
            elif len(uid) != 8:
                st.warning(t("warning_8digits"))
            else:
                login(uid, nick)
                st.rerun()
    st.stop()

# 全局牌堆配置：开关关时所有人用管理员配置，开关开时用户可自行修改（session_state）
cfg = load_config()
if not cfg.get("allow_user_edit", False):
    st.session_state.igt_decks = {k: list(v) for k, v in cfg["decks"].items()}
elif "igt_decks" not in st.session_state:
    st.session_state.igt_decks = {k: list(v) for k, v in cfg["decks"].items()}

# 顶部：语言切换 + 当前用户 + 退出登录 + 后台入口（仅管理员）
top_left, top_right = st.columns([3, 1])
with top_left:
    st.caption(t("current_user_fmt", nick=get_nickname(), uid=get_user_id()))
with top_right:
    lang_col, btn_col = st.columns([1, 1])
    with lang_col:
        new_lang = st.selectbox(
            "Language / 语言",
            options=["zh", "en"],
            index=0 if get_lang() == "zh" else 1,
            format_func=lambda x: t("lang_zh") if x == "zh" else t("lang_en"),
            key="lang_switch",
        )
        if new_lang != get_lang():
            set_lang(new_lang)
            st.rerun()
    with btn_col:
        if st.button(t("btn_logout"), key="logout_main"):
            logout()
            st.session_state.pop("viewing_backend", None)
            st.rerun()
        if is_admin() and st.button(t("btn_admin"), key="go_admin", type="primary"):
            st.session_state.viewing_backend = True
            st.rerun()

# 管理员查看后台时：仅在此处展示后台内容，不显示首页
if is_logged_in() and is_admin() and st.session_state.get("viewing_backend"):
    st.title(t("admin_title"))
    st.caption(t("admin_caption"))
    st.markdown("---")
    if st.button(t("btn_back_home"), key="back_from_admin"):
        st.session_state.viewing_backend = False
        st.rerun()
    st.markdown("---")
    tab_deck, tab_users, tab_self, tab_others = st.tabs([
        t("tab_deck"), t("tab_users"), t("tab_self"), t("tab_others"),
    ])
    with tab_deck:
        st.subheader(t("deck_title"))
        st.caption(t("deck_caption"))
        cfg = load_config()
        with st.form("admin_deck_config"):
            allow = st.checkbox(t("allow_user_edit"), value=cfg.get("allow_user_edit", False))
            st.markdown("---")
            for k in IGTEnv.DECK_NAMES:
                w, p, L = cfg.get("decks", {}).get(k, list(IGTEnv.DEFAULT_DECKS[k]))
                if isinstance(w, (list, tuple)):
                    w, p, L = w[0], w[1], w[2]
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.number_input(t("deck_reward", k=k), min_value=1, value=int(w), step=10, key=f"admin_deck_{k}_w")
                with c2:
                    st.slider(t("deck_penalty_p", k=k), 0.0, 1.0, float(p), 0.05, key=f"admin_deck_{k}_p")
                with c3:
                    st.number_input(t("deck_penalty_L", k=k), value=int(L), step=50, key=f"admin_deck_{k}_L")
            if st.form_submit_button(t("btn_save_deck")):
                new_decks = {}
                for k in IGTEnv.DECK_NAMES:
                    w = int(st.session_state.get(f"admin_deck_{k}_w", 100))
                    p = float(st.session_state.get(f"admin_deck_{k}_p", 0.5))
                    L = int(st.session_state.get(f"admin_deck_{k}_L", -250))
                    if L > 0:
                        L = -L
                    new_decks[k] = [w, p, L]
                save_config(allow_user_edit=allow, decks=new_decks)
                st.session_state.igt_decks = {k: list(v) for k, v in get_decks().items()}
                st.success(t("saved_deck"))
                st.rerun()
    with tab_users:
        st.subheader(t("users_title"))
        st.caption(t("users_caption"))
        users = list_users()
        if not users:
            st.info(t("no_users"))
        else:
            for uid, nick in users:
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**{t('user_id_label')}** {uid} · **{t('label_nickname')}** {nick}")
                with c2:
                    if st.button(t("btn_del_user"), key=f"del_user_{uid}"):
                        delete_user_data(uid)
                        st.success(t("deleted_user", uid=uid))
                        st.rerun()
    with tab_self:
        st.subheader(t("self_tab_title"))
        grouped = get_all_grouped_by_user("自己玩")
        if not grouped:
            st.info(t("no_self_data"))
        else:
            for user_id in sorted(grouped.keys()):
                entries = grouped[user_id]
                nickname = entries[0].get("昵称", "") if entries else ""
                with st.expander(t("expander_user", uid=user_id, nick=nickname, n=len(entries)), expanded=(len(entries) > 0)):
                    for i, e in enumerate(entries):
                        ts = e.get("时间", "")
                        history = e.get("history", [])
                        n_rounds = len(history)
                        final_balance = history[-1][2] if history else 0
                        st.caption(t("submit_n", n=i+1) + f" · {ts} · " + t("rounds_balance", rounds=n_rounds, balance=final_balance))
                    csv_rows = self_play_to_csv_rows(entries)
                    csv_str = to_csv_string(csv_rows)
                    st.download_button(
                        t("dl_user_csv", uid=user_id),
                        data=csv_str.encode("utf-8-sig"),
                        file_name=f"igt_自己玩_{user_id}.csv",
                        mime="text/csv",
                        key=f"dl_self_{user_id}",
                    )
            all_self = get_all("自己玩")
            if all_self:
                all_csv = self_play_to_csv_rows(all_self)
                st.download_button(
                    t("dl_all_self"),
                    data=to_csv_string(all_csv).encode("utf-8-sig"),
                    file_name="igt_自己玩_全部.csv",
                    mime="text/csv",
                    key="dl_self_all",
                )
    with tab_others:
        sub_tabs = st.tabs(["Delta", "Q-learning", "ORL", "仪表盘"])
        mod_map = ["Delta", "Qlearning", "ORL", "仪表盘"]
        for idx, (mod_name, mod_key) in enumerate(zip(["Delta", "Q-learning", "ORL", "仪表盘"], mod_map)):
            with sub_tabs[idx]:
                entries = get_all(mod_key)
                if not entries:
                    st.info(t("no_mod_data", mod=mod_name))
                else:
                    grouped = get_all_grouped_by_user(mod_key)
                    for user_id in sorted(grouped.keys()):
                        user_entries = grouped[user_id]
                        nickname = user_entries[0].get("昵称", "") if user_entries else ""
                        with st.expander(t("expander_user_short", uid=user_id, nick=nickname, n=len(user_entries)), expanded=False):
                            for i, e in enumerate(user_entries):
                                ts = e.get("时间", "")
                                n_trials = e.get("n_trials", 0)
                                final_balance = e.get("final_balance", 0)
                                st.caption(t("submit_n", n=i+1) + f" · {ts} · " + t("rounds_balance", rounds=n_trials, balance=final_balance))
                            if user_entries and user_entries[0].get("path_rows") is not None:
                                csv_rows = model_run_to_csv_rows(user_entries)
                                st.download_button(
                                    t("dl_mod_csv", uid=user_id),
                                    data=to_csv_string(csv_rows).encode("utf-8-sig"),
                                    file_name=f"igt_{mod_key}_{user_id}.csv",
                                    mime="text/csv",
                                    key=f"dl_{mod_key}_{user_id}",
                                )
                    if entries and entries[0].get("path_rows") is not None:
                        all_csv = model_run_to_csv_rows(entries)
                        st.download_button(
                            t("dl_all_mod", mod=mod_name),
                            data=to_csv_string(all_csv).encode("utf-8-sig"),
                            file_name=f"igt_{mod_key}_全部.csv",
                            mime="text/csv",
                            key=f"dl_{mod_key}_all",
                        )
                    elif mod_key == "仪表盘":
                        st.caption(t("dashboard_no_path"))
    st.stop()

st.title("🃏 " + t("app_title_full"))
st.caption(t("app_caption"))

with st.expander(t("game_rules_title"), expanded=False):
    decks = st.session_state.igt_decks
    for k in IGTEnv.DECK_NAMES:
        w, p, L = decks[k][0], decks[k][1], decks[k][2]
        exp = w + p * L
        st.markdown("- " + t("deck_line", k=k, w=int(w), p=int(float(p)*100), L=int(L), exp=f"{exp:.1f}"))
    st.markdown(t("rational_note"))
    if get_allow_user_edit():
        if st.button(t("btn_edit_decks"), key="edit_decks_btn"):
            st.session_state.edit_decks = True
        if st.session_state.get("edit_decks", False):
            st.markdown("---")
            st.caption(t("edit_decks_caption"))
            with st.form("牌堆配置"):
                new_decks = {}
                for k in IGTEnv.DECK_NAMES:
                    w, p, L = decks[k][0], decks[k][1], decks[k][2]
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        new_w = st.number_input(t("deck_reward", k=k), min_value=1, value=int(w), step=10, key=f"deck_{k}_w")
                    with c2:
                        new_p = st.slider(t("deck_penalty_p", k=k), 0.0, 1.0, float(p), 0.05, key=f"deck_{k}_p")
                    with c3:
                        new_L = st.number_input(t("deck_penalty_L", k=k), value=int(L), step=50, key=f"deck_{k}_L")
                        if new_L > 0:
                            new_L = -new_L
                    new_decks[k] = (new_w, new_p, new_L)
                col_save, col_cancel, _ = st.columns([1, 1, 2])
                with col_save:
                    save = st.form_submit_button(t("btn_save"))
                with col_cancel:
                    cancel = st.form_submit_button(t("btn_cancel"))
                if save:
                    st.session_state.igt_decks = {k: [a, b, c] for k, (a, b, c) in new_decks.items()}
                    st.session_state.edit_decks = False
                    st.rerun()
                if cancel:
                    st.session_state.edit_decks = False
                    st.rerun()

st.markdown("---")

row1_col1, row1_col2 = st.columns(2)
row2_col1, row2_col2 = st.columns(2)

with row1_col1:
    st.subheader(t("nav_self_play"))
    st.markdown(t("nav_self_desc"))
    if st.button(t("btn_enter_lab"), key="go_play", type="primary", use_container_width=True):
        st.switch_page("pages/1_自己玩.py")

with row1_col2:
    st.subheader(t("nav_delta"))
    st.markdown(t("nav_delta_desc"))
    if st.button(t("btn_enter_lab"), key="go_delta", type="primary", use_container_width=True):
        st.switch_page("pages/2_Delta算法.py")

with row2_col1:
    st.subheader(t("nav_ql"))
    st.markdown(t("nav_ql_desc"))
    if st.button(t("btn_enter_lab"), key="go_qlearning", type="primary", use_container_width=True):
        st.switch_page("pages/3_Qlearning.py")

with row2_col2:
    st.subheader(t("nav_orl"))
    st.markdown(t("nav_orl_desc"))
    if st.button(t("btn_enter_lab"), key="go_orl", type="primary", use_container_width=True):
        st.switch_page("pages/4_ORL算法.py")

st.markdown("---")
st.subheader(t("dash_title"))
st.markdown(t("dash_desc"))
if st.button(t("btn_enter_dash"), key="go_dashboard", type="primary", use_container_width=True):
    st.switch_page("pages/5_仪表盘对比.py")

st.markdown("---")
st.caption(t("footer"))
