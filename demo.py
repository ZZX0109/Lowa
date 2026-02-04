"""
行为经济学实验：爱荷华赌博任务 - 在线体验 Demo
运行: streamlit run demo.py
学生在浏览器中手动选牌堆，观察余额与奖惩变化。
"""

import streamlit as st
from igt_env import IGTEnv

st.set_page_config(page_title="爱荷华赌博任务", page_icon="🃏", layout="wide")
if "igt_decks" not in st.session_state:
    st.session_state.igt_decks = {k: list(v) for k, v in IGTEnv.DEFAULT_DECKS.items()}

# 布局：标题靠上（CSS 强制覆盖）、左右两栏中间加窄列留白
TITLE_TOP_PADDING_REM = 1.5  # 标题与顶端距离；若改后无变化，请硬刷新(Ctrl+Shift+R)或重启 streamlit run
st.markdown(
    f"""
    <style>
    /* 强制覆盖主内容区顶部留白（!important 覆盖 Streamlit 默认） */
    section[data-testid="stSidebar"] + div .block-container {{ padding-top: {TITLE_TOP_PADDING_REM}rem !important; }}
    section.main .block-container {{ padding-top: {TITLE_TOP_PADDING_REM}rem !important; }}
    div.block-container {{ padding-top: {TITLE_TOP_PADDING_REM}rem !important; }}
    [data-testid="stAppViewContainer"] .block-container {{ padding-top: {TITLE_TOP_PADDING_REM}rem !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# 持久化环境与余额（避免每次刷新重建）
if "env" not in st.session_state:
    st.session_state.env = IGTEnv(decks=st.session_state.igt_decks)
if "balance" not in st.session_state:
    st.session_state.balance = 2000
    st.session_state.env.reset(initial_balance=2000)

env = st.session_state.env
st.session_state.balance = env.balance

# 标题区：全页宽（不放在任何 column 内）
st.title("🃏 行为经济学实验：爱荷华赌博任务")
st.caption("从 A、B、C、D 四组牌堆中反复选择，观察长期收益差异。")
with st.expander("📖 游戏说明与牌堆期望"):
    st.markdown("""
    - **牌堆 A**：每次 +100，50% 概率 -250 → 期望约 **-25/次**
    - **牌堆 B**：每次 +100，10% 概率 -1250 → 期望约 **-25/次**
    - **牌堆 C**：每次 +50，50% 概率 -50 → 期望约 **+25/次**
    - **牌堆 D**：每次 +50，10% 概率 -25 → 期望约 **+47.5/次**

    理性策略应多选 C、D；人类常因高收益（A、B）的诱惑而偏向不利牌堆。
    """)

st.markdown("---")

# 同级：左侧 = 当前余额 + 选择 + 最近记录，中间留白，右侧 = 实时可视化
game_col, _spacer, charts_col = st.columns([1, 0.12, 1])

with game_col:
    st.metric("当前余额", f"¥ {st.session_state.balance}")

    # 四列按钮
    col1, col2, col3, col4 = st.columns(4)
    for i, deck in enumerate(IGTEnv.DECK_NAMES):
        with [col1, col2, col3, col4][i]:
            if st.button(f"牌堆 {deck}", key=f"deck_{deck}"):
                reward = env.step(deck)
                st.session_state.balance = env.balance
                st.rerun()

    # 最近一次反馈
    if env.history:
        last_choice, last_reward, _ = env.history[-1]
        sign = "+" if last_reward >= 0 else ""
        st.info(f"上次选择 **牌堆 {last_choice}**，本次收益: **{sign}{last_reward}**")

    # 重置
    if st.button("🔄 重置游戏（重新开始）", type="secondary"):
        st.session_state.env = IGTEnv(decks=st.session_state.igt_decks)
        st.session_state.env.reset(initial_balance=2000)
        st.session_state.balance = 2000
        st.rerun()

    # 最近记录：放在固定高度的可滚动容器内，不无限延伸
    st.markdown("---")
    st.subheader("最近记录")
    if env.history:
        records = [
            {"轮次": i, "选择": c, "收益": r, "余额": b}
            for i, (c, r, b) in enumerate(env.history, 1)
        ]
        records.reverse()  # 最新在上
        st.dataframe(records, use_container_width=True, height=280, hide_index=True)
    else:
        st.caption("暂无记录，请选择牌堆开始。")

with charts_col:
    st.subheader("📊 实时可视化")
    if env.history:
        n = len(env.history)
        trials = list(range(1, n + 1))
        balances = [2000] + [h[2] for h in env.history]  # 每步后的余额
        # 选牌比例累积：到第 t 轮时各牌堆被选中的比例
        counts = {d: 0 for d in IGTEnv.DECK_NAMES}
        prop_a, prop_b, prop_c, prop_d = [], [], [], []
        for choice, _, _ in env.history:
            counts[choice] += 1
            t = sum(counts.values())
            prop_a.append(counts["A"] / t)
            prop_b.append(counts["B"] / t)
            prop_c.append(counts["C"] / t)
            prop_d.append(counts["D"] / t)

        chart_data_prop = {
            "A 比例": prop_a,
            "B 比例": prop_b,
            "C 比例": prop_c,
            "D 比例": prop_d,
        }
        chart_data_balance = {"余额": balances}

        st.caption("选牌比例累积曲线")
        st.line_chart(chart_data_prop, height=220)

        st.caption("累积净收益（余额）曲线")
        st.line_chart(chart_data_balance, height=220)
    else:
        st.caption("选择牌堆后，此处将显示选牌比例累积曲线与累积净收益曲线。")
