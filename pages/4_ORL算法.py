"""
实验室 4：ORL 模型 - 同时模拟金额感知与频率感知，V 与 Ef、频率感知图。
布局：左上日志、左下历史表；右上牌堆比例、右下收益曲线与 Ef。日志区可点击切换为牌堆选择柱状图。
"""

import streamlit as st
import pandas as pd
from collections import Counter
from igt_env import IGTEnv
from run_orl import run_orl_step_by_step
from auth import is_logged_in, get_user_id, get_nickname
from submission_store import add_submission
from i18n import t, get_lang, set_lang

st.set_page_config(page_title="ORL · IGT", page_icon="🧠", layout="wide")
if "lang" not in st.session_state:
    st.session_state.lang = "zh"

if not is_logged_in():
    st.warning(t("warn_login"))
    if st.button(t("btn_back_home_short")):
        st.switch_page("app.py")
    st.stop()
if "igt_decks" not in st.session_state:
    st.session_state.igt_decks = {k: list(v) for k, v in IGTEnv.DEFAULT_DECKS.items()}

st.title(t("orl_title"))
st.caption(t("orl_caption"))
st.markdown("---")

with st.sidebar:
    new_lang = st.selectbox("Language / 语言", ["zh", "en"], index=0 if get_lang() == "zh" else 1, format_func=lambda x: t("lang_zh") if x == "zh" else t("lang_en"), key="lang_orl")
    if new_lang != get_lang():
        set_lang(new_lang)
        st.rerun()
    st.subheader(t("params_title"))
    n_trials = st.number_input(t("n_trials"), min_value=10, max_value=2000, value=200, step=10)
    alpha_v = st.slider(t("alpha_v"), 0.01, 0.5, 0.15, 0.01)
    alpha_f = st.slider(t("alpha_f"), 0.01, 0.5, 0.15, 0.01)
    W_v = st.slider(t("W_v"), 0.0, 1.0, 0.5, 0.05)
    W_f = st.slider(t("W_f"), 0.0, 1.0, 0.5, 0.05, help=t("W_f_help"))
    temp = st.slider(t("temp"), 0.1, 3.0, 1.5, 0.1)
    seed = st.number_input(t("seed"), min_value=0, value=42, step=1)
    step_delay = st.slider(t("step_delay"), 0.0, 0.5, 0.05, 0.01, help=t("step_delay_help_short"))
    st.markdown("---")
    run_clicked = st.button(t("btn_run_orl"), type="primary")
    if st.session_state.get("orl_result"):
        if st.button(t("btn_rerun"), key="orl_rerun"):
            for k in ("orl_result", "log_show_bar_orl"):
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
        freq_chart_ph = st.empty()

    with st.spinner(t("spinner_orl")):
        path_rows, balances, ef_history, log_lines = run_orl_step_by_step(
            env, n_trials, alpha_v, alpha_f, W_v, W_f, temp, seed, step_delay,
            log_ph, balance_ph, path_ph, prop_ph, chart_ph, freq_chart_ph,
        )
    decks = list(IGTEnv.DECK_NAMES)
    st.session_state.orl_result = {
        "path_rows": path_rows,
        "balances": balances,
        "ef_history": ef_history,
        "log_lines": log_lines,
        "final_balance": env.balance,
        "n_trials": n_trials,
        "decks": decks,
    }
    st.rerun()

if st.session_state.get("orl_result"):
    res = st.session_state.orl_result
    path_rows = res["path_rows"]
    balances = res["balances"]
    log_lines = res["log_lines"]
    ef_history = res["ef_history"]
    decks = res["decks"]
    counts = Counter(r[1] for r in path_rows)

    st.metric(t("current_balance"), f"¥ {res['final_balance']}")
    row_msg, row_btn = st.columns([2, 1])
    with row_msg:
        st.success(t("run_done", n=res["n_trials"], balance=res["final_balance"]))
    with row_btn:
        if st.button(t("btn_submit_run"), key="orl_submit"):
            add_submission(
                "ORL",
                get_user_id(),
                get_nickname(),
                {
                    "path_rows": path_rows,
                    "balances": balances,
                    "n_trials": res["n_trials"],
                    "final_balance": res["final_balance"],
                },
            )
            st.success(t("submitted_thanks"))
            st.rerun()
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.caption(t("history_label"))
        with st.expander(t("explain_title"), expanded=False):
            st.caption("模型每轮根据 V（金额）与 Ef（赢钱频率）加权得分、Softmax 得出选择。")
            st.text_area(
                "运行日志",
                value="\n".join(log_lines),
                height=280,
                disabled=True,
                label_visibility="collapsed",
                key="orl_log_view",
            )
        st.dataframe(
            [{t("col_round"): r[0], t("col_choice"): r[1], t("col_reward"): r[2], t("col_balance"): r[3]} for r in path_rows[-30:]],
            use_container_width=True,
            height=200,
            hide_index=True,
        )
        st.caption(t("bar_chart_caption"))
        df_bar = pd.DataFrame({t("col_count"): [counts.get(d, 0) for d in decks]}, index=decks)
        st.bar_chart(df_bar, height=200)
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
        st.line_chart({"A": prop_a, "B": prop_b, "C": prop_c, "D": prop_d}, height=200)
        st.caption(t("balance_curve"))
        st.line_chart({t("col_balance"): balances}, height=200)
        st.caption(t("ef_chart_label"))
        st.line_chart({f"Ef({a})": ef_history[a] for a in decks}, height=200)
        st.caption(t("ef_chart_explain"))
else:
    st.info(t("hint_orl"))
