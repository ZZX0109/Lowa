"""
仪表盘对比：同时配置 Delta、Q-learning、ORL 参数，可逐步运行并实时查看图表变化。
"""

import time
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from igt_env import IGTEnv
from run_delta import run_delta_one_step
from run_qlearning import run_qlearning_one_step
from run_orl import run_orl_one_step
from auth import is_logged_in, get_user_id, get_nickname
from submission_store import add_submission
from deck_config import get_decks, get_allow_user_edit
from i18n import t, get_lang, set_lang

st.set_page_config(page_title="仪表盘对比 · IGT", page_icon="📊", layout="wide")
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

with st.sidebar:
    new_lang = st.selectbox("Language / 语言", ["zh", "en"], index=0 if get_lang() == "zh" else 1, format_func=lambda x: t("lang_zh") if x == "zh" else t("lang_en"), key="lang_dash")
    if new_lang != get_lang():
        set_lang(new_lang)
        st.rerun()

st.title(t("dash_page_title"))
st.caption(t("dash_page_caption"))
st.markdown("---")

st.subheader(t("params_config"))
c_rounds, c_seed, c_delay = st.columns(3)
with c_rounds:
    n_trials = st.number_input(t("n_trials_shared"), min_value=50, max_value=2000, value=300, step=50)
with c_seed:
    seed = st.number_input(t("seed_short"), min_value=0, value=42, step=1)
with c_delay:
    step_delay = st.slider(t("step_delay"), 0.0, 0.5, 0.05, 0.01, help=t("step_delay_dash_help"))

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**📈 Delta**")
    delta_alpha = st.slider("Delta α", 0.01, 0.5, 0.15, 0.01, key="d_alpha")
    delta_temp = st.slider("Delta " + t("temp"), 0.1, 3.0, 1.5, 0.1, key="d_temp")
with c2:
    st.markdown("**🤖 Q-learning**")
    ql_alpha = st.slider("Q-learning α", 0.01, 0.5, 0.15, 0.01, key="ql_alpha")
    ql_epsilon = st.slider("Q-learning ε", 0.0, 0.5, 0.1, 0.01, key="ql_eps")
    ql_gamma = st.slider("Q-learning γ", 0.0, 0.99, 0.0, 0.01, key="ql_gamma")
with c3:
    st.markdown("**🧠 ORL**")
    orl_alpha_v = st.slider("ORL α_reward", 0.01, 0.5, 0.15, 0.01, key="orl_av")
    orl_alpha_f = st.slider("ORL α_freq", 0.01, 0.5, 0.15, 0.01, key="orl_af")
    orl_W_v = st.slider("ORL W_v", 0.0, 1.0, 0.5, 0.05, key="orl_wv")
    orl_W_f = st.slider("ORL W_f", 0.0, 1.0, 0.5, 0.05, key="orl_wf")
    orl_temp = st.slider("ORL " + t("temp"), 0.1, 3.0, 1.5, 0.1, key="orl_temp")

run_clicked = st.button(t("run_all"), type="primary")

if run_clicked:
    decks = list("ABCD")
    np.random.seed(seed)
    env_d = IGTEnv(seed=seed, decks=st.session_state.igt_decks)
    env_q = IGTEnv(seed=seed, decks=st.session_state.igt_decks)
    env_o = IGTEnv(seed=seed, decks=st.session_state.igt_decks)
    env_d.reset(2000)
    env_q.reset(2000)
    env_o.reset(2000)
    V_d = {a: 0.0 for a in decks}
    Q_q = {a: 0.0 for a in decks}
    V_o = {a: 0.0 for a in decks}
    Ef_o = {a: 0.0 for a in decks}

    path_d, path_q, path_o = [], [], []
    bal_d, bal_q, bal_o = [2000], [2000], [2000]

    st.subheader("总收益对比（折线图）")
    line_ph = st.empty()
    st.subheader("牌组选择占比（柱状图）")
    bar_ph = st.empty()

    def proportions(path_rows):
        c = {x: 0 for x in decks}
        for (_, choice, _, _) in path_rows:
            c[choice] += 1
        n = len(path_rows) or 1
        return [c[x] / n for x in decks]

    with st.spinner("正在逐步运行三组模型…"):
        for step in range(1, n_trials + 1):
            choice_d, r_d, V_d = run_delta_one_step(env_d, V_d, delta_alpha, delta_temp)
            choice_q, r_q, Q_q = run_qlearning_one_step(env_q, Q_q, ql_alpha, ql_epsilon, ql_gamma)
            choice_o, r_o, V_o, Ef_o = run_orl_one_step(env_o, V_o, Ef_o, orl_alpha_v, orl_alpha_f, orl_W_v, orl_W_f, orl_temp)

            path_d.append((step, choice_d, r_d, env_d.balance))
            path_q.append((step, choice_q, r_q, env_q.balance))
            path_o.append((step, choice_o, r_o, env_o.balance))
            bal_d.append(env_d.balance)
            bal_q.append(env_q.balance)
            bal_o.append(env_o.balance)

            reward_d = [b - 2000 for b in bal_d]
            reward_q = [b - 2000 for b in bal_q]
            reward_o = [b - 2000 for b in bal_o]
            line_ph.line_chart({"Delta": reward_d, "Q-learning": reward_q, "ORL": reward_o}, height=320)

            prop_d = proportions(path_d)
            prop_q = proportions(path_q)
            prop_o = proportions(path_o)
            plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "SimHei", "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False
            fig, ax = plt.subplots(figsize=(8, 4))
            x = np.arange(len(decks))
            w = 0.25
            ax.bar(x - w, prop_d, w, label="Delta", color="#4A90D9")
            ax.bar(x, prop_q, w, label="Q-learning", color="#E67E22")
            ax.bar(x + w, prop_o, w, label="ORL", color="#27AE60")
            ax.set_xticks(x)
            ax.set_xticklabels(decks)
            ax.set_ylabel("选择占比")
            ax.set_xlabel("牌堆")
            ax.legend()
            ax.set_ylim(0, 1)
            bar_ph.pyplot(fig)
            plt.close()

            if step_delay > 0:
                time.sleep(step_delay)

    st.session_state.dashboard = {
        "n_trials": n_trials,
        "path_delta": path_d,
        "path_ql": path_q,
        "path_orl": path_o,
        "balances_delta": bal_d,
        "balances_ql": bal_q,
        "balances_orl": bal_o,
        "decks": dict(st.session_state.igt_decks),
    }
    st.rerun()

if "dashboard" in st.session_state:
    d = st.session_state.dashboard
    n = d["n_trials"]
    bal_d, bal_q, bal_o = d["balances_delta"], d["balances_ql"], d["balances_orl"]
    path_d, path_q, path_o = d["path_delta"], d["path_ql"], d["path_orl"]

    # 总收益 = 余额 - 2000
    reward_d = [b - 2000 for b in bal_d]
    reward_q = [b - 2000 for b in bal_q]
    reward_o = [b - 2000 for b in bal_o]

    st.subheader("总收益对比（折线图）")
    st.line_chart({
        "Delta": reward_d,
        "Q-learning": reward_q,
        "ORL": reward_o,
    }, height=320)

    st.subheader("牌组选择占比")
    decks = list("ABCD")
    def proportions(path_rows):
        c = {x: 0 for x in decks}
        for (_, choice, _, _) in path_rows:
            c[choice] += 1
        return [c[x] / len(path_rows) for x in decks]

    prop_d = proportions(path_d)
    prop_q = proportions(path_q)
    prop_o = proportions(path_o)

    plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(decks))
    w = 0.25
    ax.bar(x - w, prop_d, w, label="Delta", color="#4A90D9")
    ax.bar(x, prop_q, w, label="Q-learning", color="#E67E22")
    ax.bar(x + w, prop_o, w, label="ORL", color="#27AE60")
    ax.set_xticks(x)
    ax.set_xticklabels(decks)
    ax.set_ylabel("选择占比")
    ax.set_xlabel("牌堆")
    ax.legend()
    ax.set_ylim(0, 1)
    st.pyplot(fig)
    plt.close()

    st.subheader(t("history_label"))
    def make_log(path_rows):
        return [{t("col_round"): rnd, t("col_choice"): c, t("col_reward"): r, t("col_balance"): b} for rnd, c, r, b in path_rows]

    with st.expander("📈 Delta 规则 · 选择日志", expanded=False):
        st.dataframe(make_log(path_d), use_container_width=True, height=200, hide_index=True)

    with st.expander("🤖 Q-learning · 选择日志", expanded=False):
        st.dataframe(make_log(path_q), use_container_width=True, height=200, hide_index=True)

    with st.expander("🧠 ORL · 选择日志", expanded=False):
        st.dataframe(make_log(path_o), use_container_width=True, height=200, hide_index=True)

    if st.button(t("btn_submit_run"), key="dashboard_submit"):
        d = st.session_state.dashboard
        add_submission(
            "仪表盘",
            get_user_id(),
            get_nickname(),
            {
                "n_trials": n,
                "path_delta": path_d,
                "path_ql": path_q,
                "path_orl": path_o,
                "balances_delta": bal_d,
                "balances_ql": bal_q,
                "balances_orl": bal_o,
                "decks": d.get("decks", dict(st.session_state.igt_decks)),
            },
        )
        st.success(t("submitted_thanks"))
        st.rerun()
else:
    st.info("👆 " + t("hint_dash"))
