"""
全局牌堆配置：存储于 data/app_config.json。
管理员在后台修改；开关关闭时仅管理员可改、所有人使用同一配置；开关打开时所有人可自行修改。
"""

import json
import os
from igt_env import IGTEnv

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
APP_CONFIG_FILE = os.path.join(DATA_DIR, "app_config.json")


def _default_decks():
    return {k: list(v) for k, v in IGTEnv.DEFAULT_DECKS.items()}


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_config():
    _ensure_dir()
    if not os.path.exists(APP_CONFIG_FILE):
        return {"allow_user_edit": False, "decks": _default_decks()}
    try:
        with open(APP_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    if "decks" not in data:
        data["decks"] = _default_decks()
    for k in IGTEnv.DECK_NAMES:
        if k not in data["decks"]:
            data["decks"][k] = list(IGTEnv.DEFAULT_DECKS[k])
    if "allow_user_edit" not in data:
        data["allow_user_edit"] = False
    return data


def save_config(allow_user_edit: bool = None, decks: dict = None):
    data = load_config()
    if allow_user_edit is not None:
        data["allow_user_edit"] = allow_user_edit
    if decks is not None:
        data["decks"] = {k: list(v) for k, v in decks.items() if k in IGTEnv.DECK_NAMES}
    _ensure_dir()
    with open(APP_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_decks():
    """当前全局牌堆配置（列表形式，与 IGTEnv 一致）。"""
    c = load_config()
    return {k: list(v) for k, v in c["decks"].items()}


def get_allow_user_edit():
    """是否允许所有用户自行修改牌堆。"""
    return load_config().get("allow_user_edit", False)
