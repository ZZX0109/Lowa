"""
Q-learning 智能体 · 与 demo 共用 igt_env，可前端运行或自动化运行。
- 前端: streamlit run run_qlearning.py
- 自动化: python run_qlearning.py --auto   （在终端自动跑完，打印日志与结果）
"""

import sys
import time
import numpy as np
from igt_env import IGTEnv


def run_qlearning_one_step(env, Q, alpha, epsilon, gamma):
    """执行一步 Q-learning，返回 (choice, reward, new_Q)。"""
    decks = list(IGTEnv.DECK_NAMES)
    if np.random.random() < epsilon:
        choice = np.random.choice(decks)
    else:
        choice = max(decks, key=lambda a: Q[a])
    r = env.step(choice)
    Q = dict(Q)
    max_next_q = max(Q.values())
    Q[choice] += alpha * (r + gamma * max_next_q - Q[choice])
    return choice, r, Q


def run_qlearning_auto(env, n_trials, alpha=0.15, epsilon=0.1, gamma=0.0, seed=42):
    """无 UI：用与 demo 相同的 igt_env 自动跑完，返回 (path_rows, balances)。"""
    if seed is not None:
        np.random.seed(seed)
    env.reset(initial_balance=2000)
    decks = list(IGTEnv.DECK_NAMES)
    Q = {a: 0.0 for a in decks}
    path_rows = []
    balances = [2000]
    for t in range(1, n_trials + 1):
        if np.random.random() < epsilon:
            choice = np.random.choice(decks)
        else:
            choice = max(decks, key=lambda a: Q[a])
        r = env.step(choice)
        max_next_q = max(Q.values())
        Q[choice] += alpha * (r + gamma * max_next_q - Q[choice])
        path_rows.append((t, choice, r, env.balance))
        balances.append(env.balance)
    return path_rows, balances


def run_qlearning_step_by_step(env, n_trials, alpha, epsilon, gamma, seed, step_delay, log_ph, balance_ph, path_ph, prop_ph, chart_ph):
    """逐步执行 Q-learning，并更新前端占位符。布局：左上是日志、左下是历史表；右上是牌堆比例、右下是收益曲线。"""
    if seed is not None:
        np.random.seed(seed)
    env.reset(initial_balance=2000)
    decks = list(IGTEnv.DECK_NAMES)
    Q = {a: 0.0 for a in decks}

    log_lines = []
    path_rows = []
    balances = [2000]

    for t in range(1, n_trials + 1):
        if np.random.random() < epsilon:
            choice = np.random.choice(decks)
            mode = "探索"
        else:
            choice = max(decks, key=lambda a: Q[a])
            mode = "利用"
        r = env.step(choice)
        max_next_q = max(Q.values())
        Q[choice] += alpha * (r + gamma * max_next_q - Q[choice])

        path_rows.append((t, choice, r, env.balance))
        balances.append(env.balance)
        line = f"第 {t:4d} 轮  [{mode}] 选择 牌堆 {choice}  →  收益 {r:+5d}  →  余额 {env.balance:6d}  |  Q = {dict((k, round(v, 1)) for k, v in Q.items())}"
        log_lines.append(line)

        if log_ph is not None:
            log_ph.text_area(
                "运行日志",
                value="\n".join(log_lines),
                height=400,
                disabled=True,
                key=f"ql_log_{t}",
                label_visibility="collapsed",
            )
        if balance_ph is not None:
            balance_ph.metric("当前余额", f"¥ {env.balance}", delta=f"{r:+d}")
        if path_ph is not None:
            path_ph.dataframe(
                data=[{"轮次": r[0], "选择": r[1], "收益": r[2], "余额": r[3]} for r in path_rows[-30:]],
                use_container_width=True,
                height=220,
                hide_index=True,
            )
        if prop_ph is not None and path_rows:
            from collections import Counter
            counts = Counter(r[1] for r in path_rows)
            prop_ph.bar_chart({d: [counts.get(d, 0)] for d in decks}, height=220)
        if chart_ph is not None and len(balances) > 1:
            chart_ph.line_chart({"余额": balances}, height=220)

        if step_delay > 0:
            time.sleep(step_delay)

    return path_rows, balances, log_lines


def _main_auto():
    """自动化运行：用与 demo 相同的 igt_env 在终端跑完并打印。"""
    import argparse
    p = argparse.ArgumentParser(description="Q-learning · 自动化跑 IGT（与 demo 同一环境）")
    p.add_argument("--auto", "-a", action="store_true", help="自动跑完，不启动 Streamlit")
    p.add_argument("--trials", "-n", type=int, default=200, help="试验轮数")
    p.add_argument("--alpha", type=float, default=0.15, help="学习率 α")
    p.add_argument("--epsilon", type=float, default=0.1, help="探索率 ε")
    p.add_argument("--gamma", type=float, default=0.0, help="折扣因子 γ")
    p.add_argument("--seed", type=int, default=42, help="随机种子")
    p.add_argument("--log-every", type=int, default=50, help="每 N 轮打印一行")
    args = p.parse_args()
    env = IGTEnv(seed=args.seed)
    path_rows, balances = run_qlearning_auto(env, args.trials, args.alpha, args.epsilon, args.gamma, args.seed)
    for i in range(0, len(path_rows), args.log_every):
        t, choice, r, bal = path_rows[i]
        print(f"第 {t:4d} 轮  选择 牌堆 {choice}  →  收益 {r:+5d}  →  余额 {bal:6d}")
    print("---")
    print(f"运行结束 · 共 {args.trials} 轮 · 最终余额 ¥ {env.balance}")


if __name__ == "__main__":
    if "--auto" in sys.argv or "-a" in sys.argv:
        _main_auto()
        sys.exit(0)

    import streamlit as st
    st.set_page_config(page_title="Q-learning · IGT", page_icon="🤖", layout="wide")
    if "igt_decks" not in st.session_state:
        st.session_state.igt_decks = {k: list(v) for k, v in IGTEnv.DEFAULT_DECKS.items()}

    st.title("🤖 Q-learning 智能体 · 爱荷华赌博任务")
    st.caption("在前端逐步观看算法选择路径与运行日志，与人玩时看到的路径一致。")
    st.markdown("---")

    with st.sidebar:
        st.subheader("参数")
        n_trials = st.number_input("试验轮数", min_value=10, max_value=2000, value=200, step=10)
        alpha = st.slider("学习率 α", 0.01, 0.5, 0.15, 0.01)
        gamma = st.slider("折扣因子 γ (远见力)", 0.0, 0.99, 0.0, 0.01, help="衡量未来奖励对当前决策的影响")
        epsilon = st.slider("探索率 ε", 0.0, 0.5, 0.1, 0.01)
        seed = st.number_input("随机种子（可选）", min_value=0, value=42, step=1)
        step_delay = st.slider("每步延迟（秒）", 0.0, 0.5, 0.05, 0.01, help="0 = 最快，稍大一点可看清每一步")
        st.markdown("---")
        run_clicked = st.button("▶ 开始运行 Q-learning", type="primary")

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

        with st.spinner("Q-learning 运行中..."):
            path_rows, balances, _ = run_qlearning_step_by_step(
                env, n_trials, alpha, epsilon, gamma, seed, step_delay,
                log_ph, balance_ph, path_ph, prop_ph, chart_ph,
            )

        st.success(f"运行结束 · 最终余额 ¥ {env.balance} · 共 {n_trials} 轮")
        st.balloons()
    else:
        st.info("👈 在左侧设置参数后点击「开始运行 Q-learning」，即可在前端逐步看到选择路径与日志。")
