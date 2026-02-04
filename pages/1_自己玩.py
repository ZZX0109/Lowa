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

st.set_page_config(page_title="自己玩 · IGT", page_icon="🃏", layout="wide")

if not is_logged_in():
    st.warning("请先返回首页登录。")
    if st.button("返回首页"):
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

st.title("👤 自己玩 · 爱荷华赌博任务")
st.caption("从 A、B、C、D 四组牌堆中反复选择，观察长期收益差异。总轮数 **{}** 轮，玩完后可点击「分析」生成策略报告。".format(IGT_N_TRIALS))
st.markdown("---")

# 总轮数 100，玩完即结束
n_rounds = len(env.history)
game_over = n_rounds >= IGT_N_TRIALS

# 游戏操作区
st.metric("当前余额", f"¥ {st.session_state.balance}")
if game_over:
    st.success("🎉 **本轮游戏结束**（已完成 {} 轮）。可点击下方「分析」查看策略报告，或「重置游戏」重新开始。".format(IGT_N_TRIALS))
col1, col2, col3, col4 = st.columns(4)
for i, deck in enumerate(IGTEnv.DECK_NAMES):
    with [col1, col2, col3, col4][i]:
        if st.button(f"牌堆 {deck}", key=f"deck_{deck}", disabled=game_over):
            reward = env.step(deck)
            st.session_state.balance = env.balance
            st.rerun()

if env.history:
    last_choice, last_reward, _ = env.history[-1]
    sign = "+" if last_reward >= 0 else ""
    st.info(f"上次选择 **牌堆 {last_choice}**，本次收益: **{sign}{last_reward}**")

if st.button("🔄 重置游戏（重新开始）", type="secondary"):
    st.session_state.env = IGTEnv(decks=st.session_state.igt_decks)
    st.session_state.env.reset(initial_balance=2000)
    st.session_state.balance = 2000
    st.session_state.pop("igt_analysis_report", None)
    st.rerun()

st.markdown("---")
st.subheader("📊 可视化与记录")

# 左上选择历史，左下选择牌堆柱状图（x=A/B/C/D, y=次数）；右上牌堆比例曲线，右下收益曲线
col_left, col_right = st.columns([1, 1])
decks = list(IGTEnv.DECK_NAMES)
with col_left:
    st.caption("选择历史")
    if env.history:
        records = [
            {"轮次": i, "选择": c, "收益": r, "余额": b}
            for i, (c, r, b) in enumerate(env.history, 1)
        ]
        records.reverse()
        st.dataframe(records, use_container_width=True, height=240, hide_index=True)
        st.caption("选择牌堆柱状图（x 轴：A/B/C/D，y 轴：选择次数）")
        counts = Counter(h[0] for h in env.history)
        df_bar = pd.DataFrame({"选择次数": [counts.get(d, 0) for d in decks]}, index=decks)
        st.bar_chart(df_bar, height=260)
    else:
        st.dataframe([], use_container_width=True, height=240, hide_index=True)
        st.caption("选择牌堆柱状图（x 轴：A/B/C/D，y 轴：选择次数）")
        df_bar = pd.DataFrame({"选择次数": [0, 0, 0, 0]}, index=decks)
        st.bar_chart(df_bar, height=260)

with col_right:
    if env.history:
        counts = {d: 0 for d in decks}
        prop_a, prop_b, prop_c, prop_d = [], [], [], []
        for choice, _, _ in env.history:
            counts[choice] = counts.get(choice, 0) + 1
            t = sum(counts.values())
            prop_a.append(counts["A"] / t)
            prop_b.append(counts["B"] / t)
            prop_c.append(counts["C"] / t)
            prop_d.append(counts["D"] / t)
        st.caption("牌堆比例（曲线）")
        st.line_chart({"A": prop_a, "B": prop_b, "C": prop_c, "D": prop_d}, height=260)
        st.caption("收益曲线")
        balances = [2000] + [h[2] for h in env.history]
        st.line_chart({"余额": balances}, height=260)
    else:
        st.caption("选择牌堆后，此处将显示牌堆比例曲线与收益曲线。")

# 分析按钮与提交按钮：分析在左，提交在右
can_analyze = n_rounds >= IGT_N_TRIALS
st.markdown("---")
btn_col1, btn_col2, _ = st.columns([1, 1, 3])
with btn_col1:
    analyze_clicked = st.button(
        "📋 分析",
        type="primary",
        disabled=not can_analyze,
        help="完成至少 100 轮后可点击生成 IGT 策略诊断报告。" if not can_analyze else "生成策略诊断报告",
    )
with btn_col2:
    submit_self_clicked = st.button(
        "📤 提交",
        disabled=not game_over,
        help="游戏结束后可提交本局轨迹（首次完成会弹出说明）。",
    )
if not can_analyze:
    st.caption(f"已完成 {n_rounds} 轮，完成 {IGT_N_TRIALS} 轮后可点击「分析」。")

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
        st.success("已提交，感谢您的参与。")
        st.rerun()

# 首次完成 100 轮：以弹窗形式征询是否提交（st.dialog 需 Streamlit 1.33+）
if st.session_state.get("self_play_show_consent") and game_over:
    _consent_text = (
        "**恭喜您完成了本次爱荷华赌博任务（IGT）模拟实验。**\n\n"
        "本程序旨在探索人类在不确定性环境下的决策风格。为了优化模型并观察不同玩家的决策习惯，现征求您的建议是否愿意提交您的游戏轨迹。\n\n"
        "**我们承诺：** 不收集您的隐私，数据仅用于后台数据展示和算法拟合。\n\n"
        "**您的权益：** 如果您不希望分享数据，可以选择否，拒绝提交数据。"
    )
    if getattr(st, "dialog", None):
        @st.dialog("是否提交本局游戏轨迹？")
        def _consent_dialog():
            st.markdown(_consent_text)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("愿意提交", key="consent_yes"):
                    add_submission("自己玩", get_user_id(), get_nickname(), _self_play_payload())
                    st.session_state.self_play_consent_shown = True
                    st.session_state.self_play_show_consent = False
                    st.success("已提交，感谢您的参与。")
                    st.rerun()
            with c2:
                if st.button("拒绝提交", key="consent_no"):
                    st.session_state.self_play_consent_shown = True
                    st.session_state.self_play_show_consent = False
                    st.rerun()
        _consent_dialog()
    else:
        st.warning("是否提交本局游戏轨迹？")
        st.info(_consent_text)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("愿意提交", key="consent_yes"):
                add_submission("自己玩", get_user_id(), get_nickname(), _self_play_payload())
                st.session_state.self_play_consent_shown = True
                st.session_state.self_play_show_consent = False
                st.success("已提交，感谢您的参与。")
                st.rerun()
        with c2:
            if st.button("拒绝提交", key="consent_no"):
                st.session_state.self_play_consent_shown = True
                st.session_state.self_play_show_consent = False
                st.rerun()

summary = st.session_state.get("igt_analysis_report")
if summary and len(env.history) >= IGT_N_TRIALS:
    with st.expander("📋 IGT 策略诊断报告", expanded=True):
        st.markdown("### 综合评价")
        st.markdown(f"**净分值 (C+D)-(A+B)：{summary['net_score']}**。根据 Bechara (1994) 的标准，您属于 **{summary['decision_type']}**。")
        st.markdown(summary["decision_desc"])
        st.markdown("---")
        st.markdown("### 学习趋势")
        st.markdown(summary["learning_desc"])
        if any(s is not None for s in summary["block_scores"]):
            blocks = [f"Block{i+1}: {s}" for i, s in enumerate(summary["block_scores"]) if s is not None]
            st.caption("各阶段净分值: " + " | ".join(blocks))
        st.markdown("---")
        st.markdown("### 策略风格")
        for s in summary["strategy_styles"]:
            st.markdown(f"- {s}")
        st.markdown("---")
        st.markdown("### 潜在偏差")
        for h in summary["hints"]:
            st.markdown(f"- {h}")
        st.markdown("---")
        st.markdown("### 模型匹配")
        st.markdown(summary["model_match"])
