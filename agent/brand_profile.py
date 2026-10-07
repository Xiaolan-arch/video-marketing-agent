# Day 12：品牌档案柜
# 作用：给每个商家建一个 JSON 档案（品牌名/默认风格/色调/口号），
#       存在项目根目录的 brands/ 文件夹，一品牌一文件
# 目的：以后生成素材时自动读取，保证每次风格统一（需求书 2.2 品牌一致性）
#
# 新知识点：
#   os.path.exists(路径)   检查文件存不存在
#   os.listdir(文件夹)     列出文件夹里的全部文件名字
#   re.sub(规则, 新内容, 文字)  按正则规则替换字符

import os
import re
import json

# 风格必须从需求书的风格库里挑（八个，和 prompt_builder 保持一致）
ALLOWED_STYLES = ["商务", "种草", "故事", "促销", "赛博", "国漫", "清新", "奢华"]

HERE = os.path.dirname(os.path.abspath(__file__))
BRANDS_DIR = os.path.join(HERE, "..", "brands")


def _safe_filename(name):
    """把品牌名变成安全的文件名。
    Windows 文件名里不能有 \\ / : * ? " < > | 这九个字符，
    用正则一次性找到，替换成下划线 _。
    """
    # r'[\\/:*?"<>|]' 是一条正则：方括号表示"其中任意一个字符"
    return re.sub(r'[\\/:*?"<>|]', "_", name.strip())


def profile_path(brand_name):
    """根据品牌名，算出它的档案路径（文件不一定已经存在）。"""
    return os.path.join(BRANDS_DIR, _safe_filename(brand_name) + ".json")


def save_profile(info):
    """保存品牌档案。
    入参 info：{"brand_name","style","tone","slogan"}
    成功返回档案路径；必填项缺失或风格不合法时，抛出带中文提示的错误。
    """
    name = (info.get("brand_name") or "").strip()
    style = (info.get("style") or "").strip()
    tone = (info.get("tone") or "").strip()
    slogan = (info.get("slogan") or "").strip()

    if not name:
        raise ValueError("品牌名不能为空")
    if style not in ALLOWED_STYLES:
        raise ValueError(f"风格必须是以下之一：{('、'.join(ALLOWED_STYLES))}")
    if not tone:
        raise ValueError("品牌色调不能为空，例如：暖橙色调")

    clean = {
        "brand_name": name,
        "style": style,
        "tone": tone,
        "slogan": slogan,
    }

    os.makedirs(BRANDS_DIR, exist_ok=True)
    path = profile_path(name)
    with open(path, "w", encoding="utf-8") as f:
        # ensure_ascii=False 老熟人了：让中文直接写进文件
        json.dump(clean, f, ensure_ascii=False, indent=2)
    return path


def load_profile(brand_name):
    """读取品牌档案，返回表格；没建过档案返回 None。
    注意：打开模式是 "r"（read 只读），可不能写成 "w"——
    "w" 会在打开的一瞬间把文件清空！
    """
    path = profile_path(brand_name)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_brands():
    """列出全部已建档品牌，返回 [{档案内容}, ...]，按品牌名排序。"""
    if not os.path.exists(BRANDS_DIR):
        return []
    result = []
    for fname in os.listdir(BRANDS_DIR):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(BRANDS_DIR, fname), "r", encoding="utf-8") as f:
            result.append(json.load(f))
    result.sort(key=lambda b: b.get("brand_name", ""))
    return result


def brand_directive(profile):
    """把一份品牌档案，拼成给大模型的"品牌一致性"指令段落。
    以后每次请求时把这段附在考试指令后面，模型就会照着档案生成。
    """
    # 口号没填就不出现那一行（三目运算：条件成立取前面，否则取空串）
    slogan_line = f"- 品牌口号：{profile['slogan']}\n" if profile.get("slogan") else ""
    return f"""
## 品牌档案（必须严格遵守，保证品牌一致性）
本次服务的品牌是【{profile['brand_name']}】：
- 默认风格：{profile['style']}（输出的 style 必须与之相同）
- 品牌色调：{profile['tone']}（prompt.tone 必须与之协调一致）
{slogan_line}
即使商家没有交代风格色调，也直接采用档案里的设定，
不得因"没说风格色调"返回 need_more_info；
风格色调以品牌档案为准，商家说的商品、场景、卖点等其他要求照常满足。
"""


# 直接运行本文件：问答式建档 + 打印档案柜里的全部品牌
if __name__ == "__main__":
    print("===== 新建品牌档案 =====")
    info = {
        "brand_name": input("品牌名："),
        "style": input(f"默认风格（{'/'.join(ALLOWED_STYLES)}）："),
        "tone": input("品牌色调（例如：暖橙色调）："),
        "slogan": input("品牌口号（没有可直接回车）："),
    }
    try:
        # try："试着"运行中间这段；
        # 如果 ValueError（我们自己抛的中文错误）发生，
        # 就跳到 except，把人话打印出来，程序不崩
        path = save_profile(info)
    except ValueError as e:
        print("没存成：" + str(e))
    else:
        # else：try 里没出错才执行
        print("已保存：" + os.path.abspath(path))

    print("\n===== 档案柜里现有品牌 =====")
    brands = list_brands()
    if not brands:
        print("（还没有品牌）")
    for b in brands:
        print(f"- {b['brand_name']}｜{b['style']}｜{b['tone']}｜{b['slogan']}")
