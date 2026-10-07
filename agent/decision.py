# Day 3：决策引擎主程序
# 作用：商家输入一句话 -> 拼考试指令 -> 联网发给大模型 -> 拿回规范 JSON

import json
import requests

import config                                  # 同文件夹的配置文件
from prompt_builder import build_prompt        # Day 2 写的拼指令函数


def call_model(content):
    """把考试内容发给大模型，返回它写的答卷文字。
    入参 content：
      可以是一段文字（字符串）；
      也可以是一组方块（列表），例如 [图片方块, 文字方块]，用于看图任务
    返回：大模型答卷的纯文本
    """
    resp = requests.post(
        config.BASE_URL + "/v1/messages",
        headers={
            # Bearer 后面跟 key，是服务器认人的方式
            "Authorization": f"Bearer {config.API_KEY}",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": config.MODEL,
            "max_tokens": config.MAX_TOKENS,
            "messages": [{"role": "user", "content": content}],
        },
        timeout=config.TIMEOUT,
    )

    # 如果状态码不是 200，这里直接报错停下，并把服务器的回话带出来
    resp.raise_for_status()

    data = resp.json()
    # 返回的 content 里可能有两种方块：
    #   thinking = 它的内心思考过程（我们不要）
    #   text     = 正式答卷（我们要的）
    return "".join(
        block.get("text", "")
        for block in data["content"]
        if block.get("type") == "text"
    )


def parse_answer(raw_text):
    """从答卷文字里取出 JSON。
    正常情况文字本身就是 JSON；
    万一它外面包了 ```json 这样的代码块标记，也帮它剥掉，兜底用。
    """
    s = raw_text.strip()
    if s.startswith("```"):
        s = s.strip("`").strip()
        if s[:4].lower() == "json":
            s = s[4:].strip()
    # 截取从第一个 { 到最后一个 }，防止前后有零星文字
    start, end = s.find("{"), s.rfind("}")
    return json.loads(s[start:end + 1])


# 直接运行本文件时执行
if __name__ == "__main__":
    user_text = input("请输入商家的一句话需求：")
    print("大模型思考中，请耐心等 30 秒到 2 分钟……")

    prompt = build_prompt(user_text)       # Day 2：拼指令
    raw = call_model(prompt)               # 联网：发指令、拿回执
    answer = parse_answer(raw)             # 解析成 Python 表格

    # 把 Python 表格再转回整齐的 JSON 文字，打印出来
    print(json.dumps(answer, ensure_ascii=False, indent=2))
