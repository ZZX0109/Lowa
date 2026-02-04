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

# 未登录时仅显示登录表单（弹窗式：页面中央）
if not is_logged_in():
    st.title("🃏 爱荷华赌博任务 · 实验室")
    st.caption("请填写学号（八位）与昵称后进入。")
    with st.form("login_form"):
        user_id = st.text_input("学号", placeholder="请输入八位学号", max_chars=20)
        nickname = st.text_input("昵称", placeholder="请输入昵称")
        submitted = st.form_submit_button("进入")
        if submitted:
            uid = (user_id or "").strip()
            nick = (nickname or "").strip()
            if not uid or not nick:
                st.warning("请填写学号和昵称。")
            elif uid == "mc565910admin" and nick == "zixinadmin":
                login(uid, nick)
                st.rerun()
            elif len(uid) != 8:
                st.warning("学号必须为八位。")
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

# 顶部：当前用户 + 退出登录 + 后台入口（仅管理员，非管理员不显示）
top_left, top_right = st.columns([3, 1])
with top_left:
    st.caption(f"当前：**{get_nickname()}**（{get_user_id()}）")
with top_right:
    if st.button("退出登录", key="logout_main"):
        logout()
        st.session_state.pop("viewing_backend", None)
        st.rerun()
    if is_admin():
        if st.button("进入后台", key="go_admin", type="primary"):
            st.session_state.viewing_backend = True
            st.rerun()

# 管理员查看后台时：仅在此处展示后台内容，不显示首页（且无独立“后台”页面，侧栏无后台入口）
if is_logged_in() and is_admin() and st.session_state.get("viewing_backend"):
    st.title("🔧 后台")
    st.caption("牌堆配置、用户管理、提交数据查看与下载。")
    st.markdown("---")
    if st.button("← 返回首页", key="back_from_admin"):
        st.session_state.viewing_backend = False
        st.rerun()
    st.markdown("---")
    tab_deck, tab_users, tab_self, tab_others = st.tabs([
        "🃏 牌堆配置", "👥 用户管理", "👤 自己玩（用户轨迹）", "📊 其他模块（Delta / Q-learning / ORL / 仪表盘）",
    ])
    with tab_deck:
        st.subheader("🃏 牌堆配置（全局）")
        st.caption("仅管理员可修改。保存后，当「允许用户自行修改」关闭时，所有人的牌堆与此一致。")
        cfg = load_config()
        with st.form("admin_deck_config"):
            allow = st.checkbox("允许用户自行修改牌堆收益与概率", value=cfg.get("allow_user_edit", False))
            st.markdown("---")
            for k in IGTEnv.DECK_NAMES:
                w, p, L = cfg.get("decks", {}).get(k, list(IGTEnv.DEFAULT_DECKS[k]))
                if isinstance(w, (list, tuple)):
                    w, p, L = w[0], w[1], w[2]
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.number_input(f"牌堆 {k} 每次收益", min_value=1, value=int(w), step=10, key=f"admin_deck_{k}_w")
                with c2:
                    st.slider(f"牌堆 {k} 罚金概率", 0.0, 1.0, float(p), 0.05, key=f"admin_deck_{k}_p")
                with c3:
                    st.number_input(f"牌堆 {k} 罚金金额（负数）", value=int(L), step=50, key=f"admin_deck_{k}_L")
            if st.form_submit_button("保存牌堆配置"):
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
                st.success("已保存。关闭「允许用户自行修改」时，所有人将使用上述配置。")
                st.rerun()
    with tab_users:
        st.subheader("👥 用户管理")
        st.caption("从提交数据中汇总的用户列表；可删除某学号的全部提交数据。")
        users = list_users()
        if not users:
            st.info("暂无用户数据（尚未有人提交）。")
        else:
            for uid, nick in users:
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**学号** {uid} · **昵称** {nick}")
                with c2:
                    if st.button("删除该用户数据", key=f"del_user_{uid}"):
                        delete_user_data(uid)
                        st.success(f"已删除学号 {uid} 的全部提交数据。")
                        st.rerun()
    with tab_self:
        st.subheader("👤 自己玩 · 按学号排列")
        grouped = get_all_grouped_by_user("自己玩")
        if not grouped:
            st.info("暂无用户提交的自己玩数据。")
        else:
            for user_id in sorted(grouped.keys()):
                entries = grouped[user_id]
                nickname = entries[0].get("昵称", "") if entries else ""
                with st.expander(f"学号 **{user_id}** · 昵称 {nickname} · 共 {len(entries)} 条记录", expanded=(len(entries) > 0)):
                    for i, e in enumerate(entries):
                        ts = e.get("时间", "")
                        history = e.get("history", [])
                        n_rounds = len(history)
                        final_balance = history[-1][2] if history else 0
                        st.caption(f"提交 {i+1} · {ts} · {n_rounds} 轮 · 最终余额 ¥{final_balance}")
                    csv_rows = self_play_to_csv_rows(entries)
                    csv_str = to_csv_string(csv_rows)
                    st.download_button(
                        f"下载该用户 CSV（学号 {user_id}）",
                        data=csv_str.encode("utf-8-sig"),
                        file_name=f"igt_自己玩_{user_id}.csv",
                        mime="text/csv",
                        key=f"dl_self_{user_id}",
                    )
            all_self = get_all("自己玩")
            if all_self:
                all_csv = self_play_to_csv_rows(all_self)
                st.download_button(
                    "📥 一键下载全部自己玩数据（CSV）",
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
                    st.info(f"暂无 {mod_name} 模块提交数据。")
                else:
                    grouped = get_all_grouped_by_user(mod_key)
                    for user_id in sorted(grouped.keys()):
                        user_entries = grouped[user_id]
                        nickname = user_entries[0].get("昵称", "") if user_entries else ""
                        with st.expander(f"学号 **{user_id}** · 昵称 {nickname} · 共 {len(user_entries)} 条", expanded=False):
                            for i, e in enumerate(user_entries):
                                ts = e.get("时间", "")
                                n_trials = e.get("n_trials", 0)
                                final_balance = e.get("final_balance", 0)
                                st.caption(f"提交 {i+1} · {ts} · {n_trials} 轮 · 最终余额 ¥{final_balance}")
                            if user_entries and user_entries[0].get("path_rows") is not None:
                                csv_rows = model_run_to_csv_rows(user_entries)
                                st.download_button(
                                    f"下载 CSV（学号 {user_id}）",
                                    data=to_csv_string(csv_rows).encode("utf-8-sig"),
                                    file_name=f"igt_{mod_key}_{user_id}.csv",
                                    mime="text/csv",
                                    key=f"dl_{mod_key}_{user_id}",
                                )
                    if entries and entries[0].get("path_rows") is not None:
                        all_csv = model_run_to_csv_rows(entries)
                        st.download_button(
                            f"📥 一键下载全部 {mod_name} 数据",
                            data=to_csv_string(all_csv).encode("utf-8-sig"),
                            file_name=f"igt_{mod_key}_全部.csv",
                            mime="text/csv",
                            key=f"dl_{mod_key}_all",
                        )
                    elif mod_key == "仪表盘":
                        st.caption("仪表盘数据为三模型对比，无 path_rows 单表，仅展示条目。")
    st.stop()

st.title("🃏 行为经济学实验：爱荷华赌博任务")
st.caption("选择下方任一实验室进入体验。")

with st.expander("📖 游戏说明与牌堆期望", expanded=False):
    decks = st.session_state.igt_decks
    for k in IGTEnv.DECK_NAMES:
        w, p, L = decks[k][0], decks[k][1], decks[k][2]
        exp = w + p * L
        st.markdown(f"- **牌堆 {k}**：每次 +{int(w)}，{float(p)*100:.0f}% 概率 {int(L)} → 期望约 **{exp:.1f}/次**")
    st.markdown("理性策略应多选 C、D；人类常因高收益（A、B）的诱惑而偏向不利牌堆。")
    # 仅当后台「允许用户自行修改」开启时，普通用户可见修改入口
    if get_allow_user_edit():
        if st.button("✏️ 修改牌堆收益以及概率", key="edit_decks_btn"):
            st.session_state.edit_decks = True
        if st.session_state.get("edit_decks", False):
            st.markdown("---")
            st.caption("重新配置每个牌堆的「每次收益」「罚金概率」「罚金金额」后点击保存。")
            with st.form("牌堆配置"):
                new_decks = {}
                for k in IGTEnv.DECK_NAMES:
                    w, p, L = decks[k][0], decks[k][1], decks[k][2]
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        new_w = st.number_input(f"牌堆 {k} 每次收益", min_value=1, value=int(w), step=10, key=f"deck_{k}_w")
                    with c2:
                        new_p = st.slider(f"牌堆 {k} 罚金概率", 0.0, 1.0, float(p), 0.05, key=f"deck_{k}_p")
                    with c3:
                        new_L = st.number_input(f"牌堆 {k} 罚金金额（负数）", value=int(L), step=50, key=f"deck_{k}_L")
                        if new_L > 0:
                            new_L = -new_L
                    new_decks[k] = (new_w, new_p, new_L)
                col_save, col_cancel, _ = st.columns([1, 1, 2])
                with col_save:
                    save = st.form_submit_button("保存")
                with col_cancel:
                    cancel = st.form_submit_button("取消")
                if save:
                    st.session_state.igt_decks = {k: [a, b, c] for k, (a, b, c) in new_decks.items()}
                    st.session_state.edit_decks = False
                    st.rerun()
                if cancel:
                    st.session_state.edit_decks = False
                    st.rerun()

st.markdown("---")

# 两行两列：第一行 自己玩 | Delta，第二行 Q-learning | ORL
row1_col1, row1_col2 = st.columns(2)
row2_col1, row2_col2 = st.columns(2)

with row1_col1:
    st.subheader("👤 自己玩")
    st.markdown("手动选择 A/B/C/D 牌堆，观察余额与奖惩，体验人类决策。")
    if st.button("进入实验室 →", key="go_play", type="primary", use_container_width=True):
        st.switch_page("pages/1_自己玩.py")

with row1_col2:
    st.subheader("📈 Delta 规则")
    st.markdown("观看 Delta 规则智能体逐步选牌与学习过程，查看 V 值与路径。")
    if st.button("进入实验室 →", key="go_delta", type="primary", use_container_width=True):
        st.switch_page("pages/2_Delta算法.py")

with row2_col1:
    st.subheader("🤖 Q-learning")
    st.markdown("观看 Q-learning 智能体逐步选牌与探索/利用，查看 Q 值与路径。")
    if st.button("进入实验室 →", key="go_qlearning", type="primary", use_container_width=True):
        st.switch_page("pages/3_Qlearning.py")

with row2_col2:
    st.subheader("🧠 ORL 模型")
    st.markdown("同时模拟「金额感知」与「频率感知」，解释为什么人会反复掉入 B 堆陷阱。")
    if st.button("进入实验室 →", key="go_orl", type="primary", use_container_width=True):
        st.switch_page("pages/4_ORL算法.py")

st.markdown("---")
st.subheader("📊 仪表盘对比")
st.markdown("同时配置 Delta、Q-learning、ORL 三组参数，一键跑完并查看总收益折线图与牌组选择占比柱状图。")
if st.button("进入仪表盘对比 →", key="go_dashboard", type="primary", use_container_width=True):
    st.switch_page("pages/5_仪表盘对比.py")

st.markdown("---")
st.caption("四个实验室共用同一套 IGT 环境（igt_env.py），规则一致。")
