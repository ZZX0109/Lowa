"""
实验室 1：自己玩 - 手动选牌堆，观察余额与奖惩。
布局：左上日志、左下历史表；右上牌堆比例、右下收益曲线。日志区可点击切换为牌堆选择柱状图。
可视化下方有分析按钮，完成 100 轮后可点击生成 IGT 策略诊断报告。
"""

import streamlit as st
import pandas as pd
from collections import Counter
from igt_env import IGTEnv
from igt_analysis import analyze_igt_history, IGT_N_TRIALS
from auth import is_logged_in, get_user_id, get_nickname
from submission_store import add_submission
from deck_config import get_decks, get_allow_user_edit
from i18n import t, get_lang, set_lang

st.set_page_config(page_title="自己玩 · IGT", page_icon="🃏", layout="wide")
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
if "env" not in st.session_state:
    st.session_state.env = IGTEnv(decks=st.session_state.igt_decks)
if "balance" not in st.session_state:
    st.session_state.balance = 2000
    st.session_state.env.reset(initial_balance=2000)

env = st.session_state.env
st.session_state.balance = env.balance

# 语言切换（侧栏）
with st.sidebar:
    new_lang = st.selectbox("Language / 语言", ["zh", "en"], index=0 if get_lang() == "zh" else 1, format_func=lambda x: t("lang_zh") if x == "zh" else t("lang_en"), key="lang_self")
    if new_lang != get_lang():
        set_lang(new_lang)
        st.rerun()

st.title(t("self_play_title"))
st.caption(t("self_play_caption", n=IGT_N_TRIALS))
st.markdown("---")

# 总轮数 100，玩完即结束
n_rounds = len(env.history)
game_over = n_rounds >= IGT_N_TRIALS

# 游戏操作区
st.metric(t("current_balance"), f"¥ {st.session_state.balance}")
if game_over:
    st.success(t("game_over_msg", n=IGT_N_TRIALS))
col1, col2, col3, col4 = st.columns(4)
for i, deck in enumerate(IGTEnv.DECK_NAMES):
    with [col1, col2, col3, col4][i]:
        if st.button(t("deck_btn", deck=deck), key=f"deck_{deck}", disabled=game_over):
            reward = env.step(deck)
            st.session_state.balance = env.balance
            st.rerun()

if env.history:
    last_choice, last_reward, _ = env.history[-1]
    sign = "+" if last_reward >= 0 else ""
    st.info(t("last_choice", deck=last_choice, sign=sign, reward=last_reward))

if st.button(t("btn_reset"), type="secondary"):
    st.session_state.env = IGTEnv(decks=st.session_state.igt_decks)
    st.session_state.env.reset(initial_balance=2000)
    st.session_state.balance = 2000
    st.session_state.pop("igt_analysis_report", None)
    st.rerun()

st.markdown("---")
st.subheader(t("viz_title"))

col_left, col_right = st.columns([1, 1])
decks = list(IGTEnv.DECK_NAMES)
with col_left:
    st.caption(t("history_label"))
    if env.history:
        records = [
            {t("col_round"): i, t("col_choice"): c, t("col_reward"): r, t("col_balance"): b}
            for i, (c, r, b) in enumerate(env.history, 1)
        ]
        records.reverse()
        st.dataframe(records, use_container_width=True, height=240, hide_index=True)
        st.caption(t("bar_chart_caption"))
        counts = Counter(h[0] for h in env.history)
        df_bar = pd.DataFrame({t("col_count"): [counts.get(d, 0) for d in decks]}, index=decks)
        st.bar_chart(df_bar, height=260)
    else:
        st.dataframe([], use_container_width=True, height=240, hide_index=True)
        st.caption(t("bar_chart_caption"))
        df_bar = pd.DataFrame({t("col_count"): [0, 0, 0, 0]}, index=decks)
        st.bar_chart(df_bar, height=260)

with col_right:
    if env.history:
        counts = {d: 0 for d in decks}
        prop_a, prop_b, prop_c, prop_d = [], [], [], []
        for choice, _, _ in env.history:
            counts[choice] = counts.get(choice, 0) + 1
            tot = sum(counts.values())
            prop_a.append(counts["A"] / tot)
            prop_b.append(counts["B"] / tot)
            prop_c.append(counts["C"] / tot)
            prop_d.append(counts["D"] / tot)
        st.caption(t("prop_caption"))
        st.line_chart({"A": prop_a, "B": prop_b, "C": prop_c, "D": prop_d}, height=260)
        st.caption(t("balance_curve"))
        balances = [2000] + [h[2] for h in env.history]
        st.line_chart({t("col_balance"): balances}, height=260)
    else:
        st.caption(t("empty_chart"))

can_analyze = n_rounds >= IGT_N_TRIALS
st.markdown("---")
btn_col1, btn_col2, _ = st.columns([1, 1, 3])
with btn_col1:
    analyze_clicked = st.button(
        t("btn_analyze"),
        type="primary",
        disabled=not can_analyze,
        help=t("analyze_help_off") if not can_analyze else t("analyze_help_on"),
    )
with btn_col2:
    submit_self_clicked = st.button(
        t("btn_submit"),
        disabled=not game_over,
        help=t("submit_help"),
    )
if not can_analyze:
    st.caption(t("progress_analyze", current=n_rounds, total=IGT_N_TRIALS))

# 点击分析后保存报告到 session_state
if analyze_clicked and can_analyze:
    st.session_state.igt_analysis_report = analyze_igt_history(env.history)
    st.rerun()

def _self_play_payload():
    return {
        "history": env.history,
        "balance": env.balance,
        "n_rounds": len(env.history),
        "decks": dict(st.session_state.igt_decks),
    }

# 自己玩提交：首次完成游戏时以弹窗征询是否提交
if game_over and submit_self_clicked:
    first_time = not st.session_state.get("self_play_consent_shown", False)
    if first_time:
        st.session_state.self_play_show_consent = True
        st.rerun()
    else:
        add_submission("自己玩", get_user_id(), get_nickname(), _self_play_payload())
        st.success(t("submitted_thanks"))
        st.rerun()

if st.session_state.get("self_play_show_consent") and game_over:
    _consent_text = t("consent_text")
    if getattr(st, "dialog", None):
        @st.dialog(t("consent_title"))
        def _consent_dialog():
            st.markdown(_consent_text)
            c1, c2 = st.columns(2)
            with c1:
                if st.button(t("consent_yes"), key="consent_yes"):
                    add_submission("自己玩", get_user_id(), get_nickname(), _self_play_payload())
                    st.session_state.self_play_consent_shown = True
                    st.session_state.self_play_show_consent = False
                    st.success(t("submitted_thanks"))
                    st.rerun()
            with c2:
                if st.button(t("consent_no"), key="consent_no"):
                    st.session_state.self_play_consent_shown = True
                    st.session_state.self_play_show_consent = False
                    st.rerun()
        _consent_dialog()
    else:
        st.warning(t("consent_title"))
        st.info(_consent_text)
        c1, c2 = st.columns(2)
        with c1:
            if st.button(t("consent_yes"), key="consent_yes"):
                add_submission("自己玩", get_user_id(), get_nickname(), _self_play_payload())
                st.session_state.self_play_consent_shown = True
                st.session_state.self_play_show_consent = False
                st.success(t("submitted_thanks"))
                st.rerun()
        with c2:
            if st.button(t("consent_no"), key="consent_no"):
                st.session_state.self_play_consent_shown = True
                st.session_state.self_play_show_consent = False
                st.rerun()

summary = st.session_state.get("igt_analysis_report")
if summary and len(env.history) >= IGT_N_TRIALS:
    with st.expander(t("report_title"), expanded=True):
        st.markdown("### " + t("report_summary"))
        st.markdown(t("report_net", score=summary["net_score"], dtype=summary["decision_type"]))
        st.markdown(summary["decision_desc"])
        st.markdown("---")
        st.markdown("### " + t("report_learning"))
        st.markdown(summary["learning_desc"])
        if any(s is not None for s in summary["block_scores"]):
            blocks = [f"Block{i+1}: {s}" for i, s in enumerate(summary["block_scores"]) if s is not None]
            st.caption(t("report_blocks", blocks=" | ".join(blocks)))
        st.markdown("---")
        st.markdown("### " + t("report_style"))
        for s in summary["strategy_styles"]:
            st.markdown(f"- {s}")
        st.markdown("---")
        st.markdown("### " + t("report_bias"))
        for h in summary["hints"]:
            st.markdown(f"- {h}")
        st.markdown("---")
        st.markdown("### " + t("report_model"))
        st.markdown(summary["model_match"])
