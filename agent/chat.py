# Day 4：会聊天的决策引擎
# 作用：信息不够就追问（最多 3 轮），补全后把结果和三平台文案友好展示
# 和 decision.py 的区别：decision.py 只问一轮；本文件能拿着聊天记录反复沟通

import json
import requests

import config
from prompt_builder import build_prompt
from decision import parse_answer          # 复用 Day 3 写好的 JSON 解析函数
from saver import save_result              # Day 5：把结果存进 output/
from prompt_builder import FORCE_DEFAULTS_DIRECTIVE  # 补充后强制默认补齐


def call_with_history(history):
    """带着完整聊天记录请求大模型，返回答卷文字。"""
    resp = requests.post(
        config.BASE_URL + "/v1/messages",
        headers={
            "Authorization": f"Bearer {config.API_KEY}",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": config.MODEL,
            "max_tokens": config.MAX_TOKENS,
            # 这次发的是整段聊天记录：一组 {"role": 角色, "content": 内容}
            "messages": history,
        },
        timeout=config.TIMEOUT,
    )
    resp.raise_for_status()
    # 只取 text 方块，跳过 thinking
    return "".join(
        block.get("text", "")
        for block in resp.json()["content"]
        if block.get("type") == "text"
    )


def show_result(answer):
    """把最终答卷用人话展示：先 note，再三平台文案，最后完整 JSON。"""
    note = answer.get("note", "")
    if note:
        print("[大模型留言] " + note)

    # ---- 三平台文案 ----
    copy = answer.get("copy") or {}
    if any(copy.values()):
        print("\n================ 三平台文案 ================")
        for key, label in [("xiaohongshu", "小红书"),
                           ("moments", "朋友圈"),
                           ("detail", "商品详情页")]:
            text = copy.get(key, "")
            if text:
                print(f"\n【{label} | 可复制】\n{text}")

    # ---- 完整 JSON（给程序看的部分）----
    print("\n================ 完整 JSON ================")
    print(json.dumps(answer, ensure_ascii=False, indent=2))


def main():
    history = []
    first = input("请输入商家的一句话需求：")
    # 第一轮带上完整的考试指令，以后各轮靠聊天记录延续
    history.append({"role": "user", "content": build_prompt(first)})

    # 规则：只主动问 1 次；补充后仍不完整就强制默认补齐，不再追问
    # 循环多留余量，用于模型不听话时强催；正常情况第 2 轮必出结果
    for turn in range(1, 4):
        print(f"[第 {turn} 轮] 正在请求大模型，请耐心等待……")
        raw = call_with_history(history)
        answer = parse_answer(raw)
        history.append({"role": "assistant", "content": raw})

        if answer.get("task_type") != "need_more_info":
            save_result(answer)             # 先存盘
            show_result(answer)             # 再屏幕展示
            return

        # ---- 它说信息不足 ----
        if turn == 1:
            # 第 1 轮：把问题列给商家；补充后带"强制补齐"指令，下轮必须出结果
            questions = answer.get("questions", [])
            if not questions:
                print("它说信息不足却没列出问题，把下面原文发给老师：")
                print(raw)
                return

            print("\n它想先了解这些（不用逐条对应，一句话说清就行）：")
            for i, q in enumerate(questions, 1):
                print(f"  {i}. {q}")
            reply = input("\n请补充后按回车（补充不全也没关系，系统会替你补齐）：")
            history.append({
                "role": "user",
                "content": f"商家补充：{reply}\n" + FORCE_DEFAULTS_DIRECTIVE,
            })
        else:
            # 第 2 轮后还提问 = 模型没听话，原指令再强催一次
            print("[系统提示] 它还想继续问，已要求它直接按默认值补齐……")
            history.append({"role": "user", "content": FORCE_DEFAULTS_DIRECTIVE})

    print("多次尝试仍未能生成结果，请把聊天情况发给老师。")


if __name__ == "__main__":
    main()
