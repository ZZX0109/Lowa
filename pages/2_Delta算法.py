"""
实验室 2：Delta 规则智能体 - 逐步观看选牌与 V 值、路径、收益曲线。
布局：左上日志、左下历史表；右上牌堆比例、右下收益曲线。日志区可点击切换为牌堆选择柱状图。
"""

import streamlit as st
import pandas as pd
from collections import Counter
from igt_env import IGTEnv
from run_delta import run_delta_step_by_step
from auth import is_logged_in, get_user_id, get_nickname
from submission_store import add_submission
from deck_config import get_decks, get_allow_user_edit
from i18n import t, get_lang, set_lang

st.set_page_config(page_title="Delta 规则 · IGT", page_icon="📈", layout="wide")
if "lang" not in st.session_state:
    st.session_state.lang = "zh"

if not is_logged_in():
    st.warning(t("warn_login"))
    if st.button(t("btn_back_home_short")):
        st.switch_page("app.py")
    st.stop()
if not get_allow_user_edit():
    st.session_state.igt_decks = get_decks()
elif "igt_decks" not in st.session_state:
    st.session_state.igt_decks = get_decks()

st.title(t("delta_title"))
st.caption(t("algo_caption"))
st.markdown("---")

with st.sidebar:
    new_lang = st.selectbox("Language / 语言", ["zh", "en"], index=0 if get_lang() == "zh" else 1, format_func=lambda x: t("lang_zh") if x == "zh" else t("lang_en"), key="lang_delta")
    if new_lang != get_lang():
        set_lang(new_lang)
        st.rerun()
    st.subheader(t("params_title"))
    n_trials = st.number_input(t("n_trials"), min_value=10, max_value=2000, value=200, step=10)
    alpha = st.slider(t("alpha"), 0.01, 0.5, 0.15, 0.01)
    temp = st.slider(t("temp"), 0.1, 3.0, 1.5, 0.1)
    seed = st.number_input(t("seed"), min_value=0, value=42, step=1)
    step_delay = st.slider(t("step_delay"), 0.0, 0.5, 0.05, 0.01, help=t("step_delay_help"))
    st.markdown("---")
    run_clicked = st.button(t("btn_run_delta"), type="primary")
    if st.session_state.get("delta_result"):
        if st.button(t("btn_rerun"), key="delta_rerun"):
            for k in ("delta_result", "log_show_bar_delta"):
                st.session_state.pop(k, None)
            st.rerun()

if run_clicked:
    env = IGTEnv(seed=seed, decks=st.session_state.igt_decks)
    balance_ph = st.empty()
    col_left, col_right = st.columns([1, 1])
    with col_left:
        log_ph = st.empty()
        path_ph = st.empty()
    with col_right:
        prop_ph = st.empty()
        chart_ph = st.empty()

    with st.spinner(t("spinner_delta")):
        path_rows, balances, log_lines = run_delta_step_by_step(
            env, n_trials, alpha, temp, seed, step_delay,
            log_ph, balance_ph, path_ph, prop_ph, chart_ph,
        )
    st.session_state.delta_result = {
        "path_rows": path_rows,
        "balances": balances,
        "log_lines": log_lines,
        "final_balance": env.balance,
        "n_trials": n_trials,
        "decks": dict(st.session_state.igt_decks),
    }
    st.rerun()

if st.session_state.get("delta_result"):
    res = st.session_state.delta_result
    path_rows, balances, log_lines = res["path_rows"], res["balances"], res["log_lines"]
    decks = list(IGTEnv.DECK_NAMES)
    counts = Counter(r[1] for r in path_rows)

    st.metric(t("current_balance"), f"¥ {res['final_balance']}")
    row_msg, row_btn = st.columns([2, 1])
    with row_msg:
        st.success(t("run_done", n=res["n_trials"], balance=res["final_balance"]))
    with row_btn:
        if st.button(t("btn_submit_run"), key="delta_submit"):
            add_submission(
                "Delta",
                get_user_id(),
                get_nickname(),
                {
                    "path_rows": path_rows,
                    "balances": balances,
                    "n_trials": res["n_trials"],
                    "final_balance": res["final_balance"],
                    "decks": res.get("decks", dict(st.session_state.igt_decks)),
                },
            )
            st.success(t("submitted_thanks"))
            st.rerun()
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.caption(t("history_label"))
        with st.expander(t("explain_title"), expanded=False):
            st.caption("模型每轮根据 V 值、Softmax 得出选择，并用 Delta 规则更新 V。")
            st.text_area(
                "运行日志",
                value="\n".join(log_lines),
                height=280,
                disabled=True,
                label_visibility="collapsed",
                key="delta_log_view",
            )
        st.dataframe(
            [{t("col_round"): r[0], t("col_choice"): r[1], t("col_reward"): r[2], t("col_balance"): r[3]} for r in path_rows[-30:]],
            use_container_width=True,
            height=220,
            hide_index=True,
        )
        st.caption(t("bar_chart_caption"))
        df_bar = pd.DataFrame({t("col_count"): [counts.get(d, 0) for d in decks]}, index=decks)
        st.bar_chart(df_bar, height=220)
    with col_right:
        prop_a, prop_b, prop_c, prop_d = [], [], [], []
        c = {d: 0 for d in decks}
        for r in path_rows:
            c[r[1]] = c.get(r[1], 0) + 1
            tot = sum(c.values())
            prop_a.append(c["A"] / tot)
            prop_b.append(c["B"] / tot)
            prop_c.append(c["C"] / tot)
            prop_d.append(c["D"] / tot)
        st.caption(t("prop_caption"))
        st.line_chart({"A": prop_a, "B": prop_b, "C": prop_c, "D": prop_d}, height=220)
        st.caption(t("balance_curve"))
        st.line_chart({t("col_balance"): balances}, height=220)
else:
    st.info(t("hint_delta"))
