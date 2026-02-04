"""
ORL 模型 · 同时模拟“金额感知”与“频率感知”，与 demo 共用 igt_env。
- 前端: streamlit run run_orl.py
- 自动化: python run_orl.py --auto
"""

import sys
import time
import numpy as np
from igt_env import IGTEnv


def softmax(x, temperature=1.0):
    x = np.array(x, dtype=float)
    x = (x - x.max()) / max(temperature, 1e-8)
    exp_x = np.exp(x)
    return exp_x / exp_x.sum()


def update_orl(choice, reward, V, Ef, alpha_v, alpha_f, W_v, W_f):
    """ORL 单步更新：更新 V（期望金额）、Ef（赢钱频率），返回该选项的综合分值 valence。"""
    # 1. 更新期望价值 (类似 Delta)
    V[choice] += alpha_v * (reward - V[choice])
    # 2. 更新赢钱频率 (ORL 特有)：reward > 0 为 1，否则 -1
    sign = 1 if reward > 0 else -1
    Ef[choice] += alpha_f * (sign - Ef[choice])
    # 3. 综合决策分值
    valence = W_v * V[choice] + W_f * Ef[choice]
    return valence


def run_orl_one_step(env, V, Ef, alpha_v, alpha_f, W_v, W_f, temp):
    """执行一步 ORL，返回 (choice, reward, new_V, new_Ef)。"""
    decks = list(IGTEnv.DECK_NAMES)
    valence_list = [W_v * V[a] + W_f * Ef[a] for a in decks]
    probs = softmax(valence_list, temperature=temp)
    choice = np.random.choice(decks, p=probs)
    r = env.step(choice)
    V = dict(V)
    Ef = dict(Ef)
    update_orl(choice, r, V, Ef, alpha_v, alpha_f, W_v, W_f)
    return choice, r, V, Ef


def run_orl_auto(env, n_trials, alpha_v=0.15, alpha_f=0.15, W_v=0.5, W_f=0.5, temp=1.5, seed=42):
    """无 UI：用与 demo 相同的 igt_env 自动跑完，返回 (path_rows, balances, ef_history)。"""
    if seed is not None:
        np.random.seed(seed)
    env.reset(initial_balance=2000)
    decks = list(IGTEnv.DECK_NAMES)
    V = {a: 0.0 for a in decks}
    Ef = {a: 0.0 for a in decks}
    path_rows = []
    balances = [2000]
    ef_history = {a: [0.0] for a in decks}

    for t in range(1, n_trials + 1):
        valence_list = [W_v * V[a] + W_f * Ef[a] for a in decks]
        probs = softmax(valence_list, temperature=temp)
        choice = np.random.choice(decks, p=probs)
        r = env.step(choice)
        update_orl(choice, r, V, Ef, alpha_v, alpha_f, W_v, W_f)

        path_rows.append((t, choice, r, env.balance))
        balances.append(env.balance)
        for a in decks:
            ef_history[a].append(Ef[a])

    return path_rows, balances, ef_history


def run_orl_step_by_step(
    env, n_trials, alpha_v, alpha_f, W_v, W_f, temp, seed, step_delay,
    log_ph, balance_ph, path_ph, prop_ph, chart_ph, freq_chart_ph,
):
    """逐步执行 ORL，并更新前端占位符。布局：左上是日志、左下是历史表；右上是牌堆比例、右下是收益曲线与 Ef。"""
    if seed is not None:
        np.random.seed(seed)
    env.reset(initial_balance=2000)
    decks = list(IGTEnv.DECK_NAMES)
    V = {a: 0.0 for a in decks}
    Ef = {a: 0.0 for a in decks}

    log_lines = []
    path_rows = []
    balances = [2000]
    ef_history = {a: [0.0] for a in decks}

    for t in range(1, n_trials + 1):
        valence_list = [W_v * V[a] + W_f * Ef[a] for a in decks]
        probs = softmax(valence_list, temperature=temp)
        choice = np.random.choice(decks, p=probs)
        r = env.step(choice)
        update_orl(choice, r, V, Ef, alpha_v, alpha_f, W_v, W_f)

        path_rows.append((t, choice, r, env.balance))
        balances.append(env.balance)
        for a in decks:
            ef_history[a].append(Ef[a])

        freq_comment = "智能体觉得这个牌堆赢钱很频繁，所以即使刚才大亏，它还是想选。" if r < 0 and Ef[choice] > 0.3 else ""
        line = (
            f"第 {t:4d} 轮  选择 牌堆 {choice}  →  收益 {r:+5d}  →  余额 {env.balance:6d}  |  "
            f"V = {dict((k, round(v, 1)) for k, v in V.items())}  |  Ef = {dict((k, round(v, 2)) for k, v in Ef.items())}"
        )
        if freq_comment:
            line += f"\n  → {freq_comment}"
        log_lines.append(line)

        if log_ph is not None:
            log_ph.text_area(
                "运行日志",
                value="\n".join(log_lines),
                height=400,
                disabled=True,
                key=f"orl_log_{t}",
                label_visibility="collapsed",
            )
        if balance_ph is not None:
            balance_ph.metric("当前余额", f"¥ {env.balance}", delta=f"{r:+d}")
        if path_ph is not None:
            path_ph.dataframe(
                data=[{"轮次": r[0], "选择": r[1], "收益": r[2], "余额": r[3]} for r in path_rows[-30:]],
                use_container_width=True,
                height=200,
                hide_index=True,
            )
        if prop_ph is not None and path_rows:
            from collections import Counter
            counts = Counter(r[1] for r in path_rows)
            prop_ph.bar_chart({d: [counts.get(d, 0)] for d in decks}, height=200)
        if chart_ph is not None and len(balances) > 1:
            chart_ph.line_chart({"余额": balances}, height=200)
        if freq_chart_ph is not None and t > 1:
            freq_chart_ph.line_chart(
                {f"Ef({a})": ef_history[a] for a in decks},
                height=200,
            )

        if step_delay > 0:
            time.sleep(step_delay)

    return path_rows, balances, ef_history, log_lines


def _main_auto():
    """自动化运行：终端跑完并打印。"""
    import argparse
    p = argparse.ArgumentParser(description="ORL · 自动化跑 IGT（与 demo 同一环境）")
    p.add_argument("--auto", "-a", action="store_true", help="自动跑完，不启动 Streamlit")
    p.add_argument("--trials", "-n", type=int, default=200, help="试验轮数")
    p.add_argument("--alpha-v", type=float, default=0.15, help="金额学习率 α_reward")
    p.add_argument("--alpha-f", type=float, default=0.15, help="频率学习率 α_freq")
    p.add_argument("--W-v", type=float, default=0.5, help="金额权重 W_v")
    p.add_argument("--W-f", type=float, default=0.5, help="频率权重 W_f")
    p.add_argument("--seed", type=int, default=42, help="随机种子")
    p.add_argument("--log-every", type=int, default=50, help="每 N 轮打印一行")
    args = p.parse_args()
    env = IGTEnv(seed=args.seed)
    path_rows, balances, ef_history = run_orl_auto(
        env, args.trials, args.alpha_v, args.alpha_f, args.W_v, args.W_f, temp=1.5, seed=args.seed
    )
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
    st.set_page_config(page_title="ORL · IGT", page_icon="🧠", layout="wide")
    if "igt_decks" not in st.session_state:
        st.session_state.igt_decks = {k: list(v) for k, v in IGTEnv.DEFAULT_DECKS.items()}

    st.title("🧠 ORL 模型 · 爱荷华赌博任务")
    st.caption("同时模拟「金额感知」与「频率感知」，解释为什么人会反复掉入 B 堆陷阱。")
    st.markdown("---")

    with st.sidebar:
        st.subheader("参数")
        n_trials = st.number_input("试验轮数", min_value=10, max_value=2000, value=200, step=10)
        alpha_v = st.slider("学习率 α_reward（金额）", 0.01, 0.5, 0.15, 0.01)
        alpha_f = st.slider("学习率 α_freq（频率）", 0.01, 0.5, 0.15, 0.01)
        W_v = st.slider("金额权重 W_v", 0.0, 1.0, 0.5, 0.05)
        W_f = st.slider("频率权重 W_f", 0.0, 1.0, 0.5, 0.05, help="调高则更看重赢钱频率，易偏向 B 堆")
        temp = st.slider("Softmax 温度", 0.1, 3.0, 1.5, 0.1)
        seed = st.number_input("随机种子（可选）", min_value=0, value=42, step=1)
        step_delay = st.slider("每步延迟（秒）", 0.0, 0.5, 0.05, 0.01)
        st.markdown("---")
        run_clicked = st.button("▶ 开始运行 ORL", type="primary")

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

        with st.spinner("ORL 运行中..."):
            path_rows, balances, ef_history, _ = run_orl_step_by_step(
                env, n_trials, alpha_v, alpha_f, W_v, W_f, temp, seed, step_delay,
                log_ph, balance_ph, path_ph, prop_ph, chart_ph, freq_chart_ph,
            )

        st.success(f"运行结束 · 最终余额 ¥ {env.balance} · 共 {n_trials} 轮")
        st.balloons()
    else:
        st.info("👈 在左侧设置参数后点击「开始运行 ORL」，查看 V 值、Ef 值与频率感知图。")
