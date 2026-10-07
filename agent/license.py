# Day 14：激活码与次数配额
# 作用：管"还能用几次"——免费试用 3 次，用完必须输激活码加次数
#       配额记录在项目根目录的 quota.json（一个超迷你的"数据库"）
#
# 产品逻辑（需求书 2.3 / 流程表第 10 项：试用→买断→次数包）：
#   1. 新用户默认有 3 次试用
#   2. 每次生成成功 consume() 扣 1 次
#   3. 次数为 0 时网页拒绝生成，要求输激活码
#   4. activate(码) 校验：码存在且没用过 → 加次数，并记下此码已用

import os
import json

# 每个新用户的免费试用次数
TRIAL_QUOTA = 3

# 激活码表：码 → 能加多少次
# （真产品里这张表放在服务器上，商家看不到；Demo 先写在这里）
CODE_PACKS = {
    "NEWBIE10": 10,     # 新手体验码
    "VIP100": 100,      # 假装是"买断大客户"
}

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, "..", "quota.json")


def _default_state():
    """一份全新的初始记录。"""
    return {"remaining": TRIAL_QUOTA, "used_codes": []}


def load_state():
    """读配额记录；文件还不存在（第一次用）时，返回并自动落盘一份初始记录。"""
    if not os.path.exists(STATE_FILE):
        state = _default_state()
        save_state(state)
        return state
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    """把记录写回文件。"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def remaining():
    """还剩几次。"""
    return load_state()["remaining"]


def consume():
    """生成成功后扣 1 次。返回扣完后剩余的次数。"""
    state = load_state()
    state["remaining"] -= 1
    save_state(state)
    return state["remaining"]


def activate(code):
    """用激活码加次数。
    返回：(是否成功, 给人看的消息)
    失败原因有两种：码不存在、码已经用过。
    """
    code = (code or "").strip().upper()   # upper：转大写，输入小写也认
    state = load_state()

    if code not in CODE_PACKS:
        return False, "激活码无效，请检查后重试"
    if code in state["used_codes"]:
        return False, "这个激活码已经使用过了"

    add = CODE_PACKS[code]
    state["remaining"] += add
    state["used_codes"].append(code)
    save_state(state)
    return True, f"激活成功！已增加 {add} 次，当前共 {state['remaining']} 次"
