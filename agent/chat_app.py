# Day 7：网页版聊天界面
# 作用：像微信/ChatGPT 一样，你一句它一句
# 规则：信息不足只问一次；商家补充后仍不完整，自动按默认值补齐

import json

import streamlit as st

from prompt_builder import build_prompt, FORCE_DEFAULTS_DIRECTIVE
from decision import parse_answer
from chat import call_with_history          # 复用：带历史记录请求大模型
from saver import save_result
from jimeng_export import build_jimeng_prompt, NEGATIVE_PROMPT, should_export

st.set_page_config(page_title="营销智能体助手", page_icon="💬")
st.title("💬 营销智能体助手")

# ---- session_state：网页的"小本本" ----
# display_msgs：画在屏幕上的聊天记录（给人看）
# api_history：发给大模型的记录（含考试指令，给模型看）
# asked_once：是否已经问过商家一次
if "display_msgs" not in st.session_state:
    st.session_state.display_msgs = []
if "api_history" not in st.session_state:
    st.session_state.api_history = []
if "asked_once" not in st.session_state:
    st.session_state.asked_once = False


def render_assistant(kind, payload):
    """画一个 AI 气泡。kind 决定里面放什么。
    questions：提问列表；result：最终答卷
    """
    with st.chat_message("assistant"):
        if kind == "questions":
            st.write("我先了解几件事，你随便说，说不全我来补：")
            for q in payload:
                st.markdown(f"- {q}")
        elif kind == "result":
            answer = payload
            note = answer.get("note", "")
            if note:
                st.success(note)

            # 出图提示词：两段【可复制】+ 即梦操作步骤
            if should_export(answer):
                st.write("**🎨 出图提示词（粘贴到即梦）**")
                st.caption(
                    "打开 jimeng.jianying.com →「图像生成」→ 粘贴①②两段 → "
                    "比例选 3:4（小红书竖图）→ 生成，满意后保存到 output 文件夹。")
                st.write("**① 正向提示词【可复制】**")
                st.code(build_jimeng_prompt(answer), language=None)
                st.write("**② 反向提示词【可复制】**")
                st.code(NEGATIVE_PROMPT, language=None)

            copy = answer.get("copy") or {}
            if any(copy.values()):
                st.write("**三平台文案（可直接复制）：**")
                for key, label in [("xiaohongshu", "小红书"),
                                   ("moments", "朋友圈"),
                                   ("detail", "商品详情页")]:
                    text = copy.get(key, "")
                    if text:
                        st.write(f"**【{label}】**")
                        # code 块带复制按钮，方便一键拷走
                        st.code(text, language=None)

            with st.expander("查看完整 JSON（开发者）"):
                st.json(answer)


# ---- 先把历史消息重新画出来 ----
for msg in st.session_state.display_msgs:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.write(msg["content"])
    else:
        render_assistant(msg["kind"], msg["content"])

# 没有任何消息时，给一句欢迎语
if not st.session_state.display_msgs:
    st.info("你好！告诉我你想做什么营销素材，例如：帮我的奶茶店做一张小红书宣传图。")

# ---- 底部输入框 ----
user_text = st.chat_input("输入需求，回车发送……")

if user_text:
    # 1. 画出用户气泡，并记录
    with st.chat_message("user"):
        st.write(user_text)
    st.session_state.display_msgs.append({"role": "user", "content": user_text})

    # 2. 构造发给模型的内容
    if not st.session_state.asked_once:
        # 第一次：带完整考试指令
        model_content = build_prompt(user_text)
    else:
        # 第二次（商家已补充）：强制默认补齐，不准再问
        model_content = f"商家补充：{user_text}\n" + FORCE_DEFAULTS_DIRECTIVE
    st.session_state.api_history.append(
        {"role": "user", "content": model_content})

    # 3. 请求大模型
    with st.spinner("思考中……"):
        raw = call_with_history(st.session_state.api_history)
        answer = parse_answer(raw)

        # 兜底：补充后它还想问，立即强催一次
        if st.session_state.asked_once and \
                answer.get("task_type") == "need_more_info":
            st.session_state.api_history.append(
                {"role": "user", "content": FORCE_DEFAULTS_DIRECTIVE})
            raw = call_with_history(st.session_state.api_history)
            answer = parse_answer(raw)

    # 4. 处理回复
    st.session_state.api_history.append(
        {"role": "assistant", "content": raw})

    if answer.get("task_type") == "need_more_info":
        questions = answer.get("questions", [])
        st.session_state.asked_once = True
        st.session_state.display_msgs.append(
            {"role": "assistant", "kind": "questions", "content": questions})
    else:
        save_result(answer)
        st.session_state.asked_once = False   # 本轮任务结束，标记复位
        st.session_state.display_msgs.append(
            {"role": "assistant", "kind": "result", "content": answer})

    st.rerun()   # 重跑一次，让新消息在 rerun 流程里整齐画出

# ---- 开始新任务：清空小本本 ----
if st.session_state.display_msgs:
    if st.button("🔄 开始新任务"):
        st.session_state.display_msgs = []
        st.session_state.api_history = []
        st.session_state.asked_once = False
        st.rerun()
