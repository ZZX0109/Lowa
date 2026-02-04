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

st.set_page_config(page_title="Delta 规则 · IGT", page_icon="📈", layout="wide")

if not is_logged_in():
    st.warning("请先返回首页登录。")
    if st.button("返回首页"):
        st.switch_page("app.py")
    st.stop()
if not get_allow_user_edit():
    st.session_state.igt_decks = get_decks()
elif "igt_decks" not in st.session_state:
    st.session_state.igt_decks = get_decks()

st.title("📈 Delta 规则智能体 · 爱荷华赌博任务")
st.caption("在前端逐步观看算法选择路径与运行日志，与人玩时看到的路径一致。")
st.markdown("---")

with st.sidebar:
    st.subheader("参数")
    n_trials = st.number_input("试验轮数", min_value=10, max_value=2000, value=200, step=10)
    alpha = st.slider("学习率 α", 0.01, 0.5, 0.15, 0.01)
    temp = st.slider("Softmax 温度", 0.1, 3.0, 1.5, 0.1)
    seed = st.number_input("随机种子（可选）", min_value=0, value=42, step=1)
    step_delay = st.slider("每步延迟（秒）", 0.0, 0.5, 0.05, 0.01, help="0 = 最快，稍大一点可看清每一步")
    st.markdown("---")
    run_clicked = st.button("▶ 开始运行 Delta 规则", type="primary")
    if st.session_state.get("delta_result"):
        if st.button("🔄 再次运行", key="delta_rerun"):
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

    with st.spinner("Delta 规则运行中..."):
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

    st.metric("当前余额", f"¥ {res['final_balance']}")
    row_msg, row_btn = st.columns([2, 1])
    with row_msg:
        st.success(f"运行结束 · 共 {res['n_trials']} 轮")
    with row_btn:
        if st.button("📤 提交", key="delta_submit"):
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
            st.success("已提交。")
            st.rerun()
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.caption("选择历史")
        with st.expander("📋 每轮计算解释（点击展开）", expanded=False):
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
            [{"轮次": r[0], "选择": r[1], "收益": r[2], "余额": r[3]} for r in path_rows[-30:]],
            use_container_width=True,
            height=220,
            hide_index=True,
        )
        st.caption("选择牌堆柱状图（x 轴：A/B/C/D，y 轴：选择次数）")
        df_bar = pd.DataFrame({"选择次数": [counts.get(d, 0) for d in decks]}, index=decks)
        st.bar_chart(df_bar, height=220)
    with col_right:
        # 牌堆比例随轮次变化的曲线
        prop_a, prop_b, prop_c, prop_d = [], [], [], []
        c = {d: 0 for d in decks}
        for r in path_rows:
            c[r[1]] = c.get(r[1], 0) + 1
            t = sum(c.values())
            prop_a.append(c["A"] / t)
            prop_b.append(c["B"] / t)
            prop_c.append(c["C"] / t)
            prop_d.append(c["D"] / t)
        st.caption("牌堆比例（曲线）")
        st.line_chart({"A": prop_a, "B": prop_b, "C": prop_c, "D": prop_d}, height=220)
        st.caption("收益曲线")
        st.line_chart({"余额": balances}, height=220)
else:
    st.info("👈 在左侧设置参数后点击「开始运行 Delta 规则」，即可在前端逐步看到选择路径与日志。")
