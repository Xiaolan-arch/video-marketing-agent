# Day 5：档案柜
# 作用：把每次的决策结果存成文件，放进 output/ 文件夹
# 新知识点：
#   open(文件路径, 模式, encoding="utf-8") 打开文件
#   模式 "w" = 写入（会覆盖旧文件）；"a" = 在文件末尾追加
#   with ... as f：用完自动关门（保存），不用手写 close
#   json.dump(表格, f) = 把 Python 表格直接写进文件
# 注意：中文文件必须 encoding="utf-8"，否则 Windows 默认用 GBK，容易乱码

import os
import json
from datetime import datetime

from storyboard import normalize_storyboard, format_script

# __file__ 是"本文件自己的位置"
# dirname 取它所在的文件夹（agent/），再拼上 ../output
# 这样不管从哪个 cmd 启动，路径都不会错
HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(HERE, "..", "output")


def save_result(answer):
    """把答卷存成两个文件：完整 JSON + 人能读的文案 TXT。
    返回 JSON 文件的完整路径，方便主程序告诉用户存哪了。
    """
    # 没有 output 文件夹就先建一个（exist_ok=True 表示已存在也不报错）
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 用当前时间给文件起名，精确到秒，不会重名、也好找
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ---- 文件 1：完整 JSON ----
    json_path = os.path.join(OUTPUT_DIR, f"决策_{stamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(answer, f, ensure_ascii=False, indent=2)

    # ---- 文件 2：三平台文案（人直接看）----
    copy = answer.get("copy") or {}
    if any(copy.values()):
        txt_path = os.path.join(OUTPUT_DIR, f"文案_{stamp}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            note = answer.get("note", "")
            if note:
                f.write(f"[大模型留言] {note}\n\n")
            for key, label in [("xiaohongshu", "小红书"),
                               ("moments", "朋友圈"),
                               ("detail", "商品详情页")]:
                text = copy.get(key, "")
                if text:
                    f.write(f"===== {label} =====\n{text}\n\n")
        print(f"文案已保存：{os.path.abspath(txt_path)}")

    # ---- 文件 3：视频分镜脚本（视频任务才有）----
    board = normalize_storyboard(answer)
    if board:
        sb_path = os.path.join(OUTPUT_DIR, f"分镜_{stamp}.txt")
        with open(sb_path, "w", encoding="utf-8") as f:
            note = answer.get("note", "")
            if note:
                f.write(f"[大模型留言] {note}\n\n")
            f.write(format_script(board))
        print(f"分镜脚本已保存：{os.path.abspath(sb_path)}")

    print(f"决策已保存：{os.path.abspath(json_path)}")
    return json_path
