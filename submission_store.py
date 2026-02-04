"""
用户提交数据存储：JSON 文件 data/submissions.json，按模块分键。
后台按学号展示、支持 CSV 下载。
"""

import json
import os
from datetime import datetime
from typing import Any, List

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SUBMISSIONS_FILE = os.path.join(DATA_DIR, "submissions.json")

MODULES = ["自己玩", "Delta", "Qlearning", "ORL", "仪表盘"]


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load():
    _ensure_dir()
    if not os.path.exists(SUBMISSIONS_FILE):
        return {m: [] for m in MODULES}
    try:
        with open(SUBMISSIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    for m in MODULES:
        if m not in data:
            data[m] = []
    return data


def _save(data: dict):
    _ensure_dir()
    with open(SUBMISSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_submission(module: str, user_id: str, nickname: str, payload: dict):
    if module not in MODULES:
        MODULES.append(module)
    data = _load()
    entry = {
        "学号": user_id,
        "昵称": nickname,
        "时间": datetime.now().isoformat(),
        **payload,
    }
    data[module].append(entry)
    _save(data)


def get_all(module: str) -> list:
    """获取某模块全部提交（仅后台管理员使用）。"""
    data = _load()
    return data.get(module, [])


def get_all_for_user(module: str, user_id: str) -> list:
    """按学号隔离：仅返回该学号的提交记录，用于普通用户查看自己的数据。"""
    data = _load()
    rows = data.get(module, [])
    return [r for r in rows if r.get("学号") == user_id]


def delete_user_data(user_id: str):
    """删除某学号在所有模块的提交数据（后台用户管理用）。"""
    data = _load()
    for m in MODULES:
        data[m] = [r for r in data.get(m, []) if r.get("学号") != user_id]
    _save(data)


def list_users() -> list:
    """从提交数据中提取所有用户 (学号, 昵称)，用于用户管理列表。"""
    data = _load()
    users = {}
    for m in MODULES:
        for r in data.get(m, []):
            uid = r.get("学号", "")
            if uid and uid not in users:
                users[uid] = r.get("昵称", "")
    return [(uid, users[uid]) for uid in sorted(users.keys())]


def get_all_grouped_by_user(module: str) -> dict:
    """按学号分组，返回 { 学号: [ entries ] }。"""
    rows = get_all(module)
    grouped = {}
    for r in rows:
        uid = r.get("学号", "")
        if uid not in grouped:
            grouped[uid] = []
        grouped[uid].append(r)
    return grouped


def self_play_to_csv_rows(entries: list) -> List[dict]:
    """自己玩：每条 entry 含 history，转为 CSV 行（轮次、选择、收益、余额）。"""
    rows = []
    for e in entries:
        user_id = e.get("学号", "")
        nickname = e.get("昵称", "")
        ts = e.get("时间", "")
        history = e.get("history", [])
        for i, (choice, reward, balance) in enumerate(history, 1):
            rows.append({
                "学号": user_id,
                "昵称": nickname,
                "提交时间": ts,
                "轮次": i,
                "选择": choice,
                "收益": reward,
                "余额": balance,
            })
    return rows


def model_run_to_csv_rows(entries: list) -> List[dict]:
    """Delta/Qlearning/ORL：path_rows 转为 CSV 行。"""
    rows = []
    for e in entries:
        user_id = e.get("学号", "")
        nickname = e.get("昵称", "")
        ts = e.get("时间", "")
        path_rows = e.get("path_rows", [])
        for t, choice, reward, balance in path_rows:
            rows.append({
                "学号": user_id,
                "昵称": nickname,
                "提交时间": ts,
                "轮次": t,
                "选择": choice,
                "收益": reward,
                "余额": balance,
            })
    return rows


def to_csv_string(rows: List[dict]) -> str:
    """将行字典列表转为 CSV 字符串（UTF-8 BOM 便于 Excel）。"""
    import csv
    import io
    if not rows:
        return ""
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return "\ufeff" + out.getvalue()
