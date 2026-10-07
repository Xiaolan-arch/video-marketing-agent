# Day 10：商业海报合成
# 作用：背景图 + 标题/副标题/行动号召 → 合成一张排版好的海报
# 工具箱：Pillow（PIL），处理图片用
#   Image      图片本身（打开、裁剪、缩放）
#   ImageDraw  在图片上"画画"（画字、画方块）
#   ImageFont  字体（字号、字体文件）

import os
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

# ---- 固定规格 ----
CANVAS_W, CANVAS_H = 1080, 1440     # 3:4 竖版（小红书海报规格）
MARGIN_X = 70                       # 文字离左右边的距离

# ---- 字体（用 Windows 自带的微软雅黑；B = Bold 粗体）----
_FONT_TITLE = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 82)
_FONT_SUB = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 42)
_FONT_CTA = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 40)

# 颜色（RGB）
WHITE = (255, 255, 255)
ACCENT = (232, 84, 62)             # 行动号召按钮的暖红色

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(HERE, "..", "output")


def _cover_crop(img):
    """把任意比例的图居中裁剪并缩放到 1080x1440（铺满、不变形）。"""
    src_ratio = img.width / img.height
    dst_ratio = CANVAS_W / CANVAS_H
    if src_ratio > dst_ratio:
        # 原图太宽：按高度铺满，裁左右
        new_h = img.height
        new_w = int(new_h * dst_ratio)
    else:
        # 原图太高：按宽度铺满，裁上下
        new_w = img.width
        new_h = int(new_w / dst_ratio)
    left = (img.width - new_w) // 2
    top = (img.height - new_h) // 2
    img = img.crop((left, top, left + new_w, top + new_h))
    return img.resize((CANVAS_W, CANVAS_H), Image.LANCZOS)


def _gradient_layer(side):
    """做一层黑色渐变（盖在图上让白字看得清）。
    side="top" 上方深下方透明；"bottom" 反过来。
    """
    layer = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    band_h = int(CANVAS_H * 0.42)          # 渐变占画面 42%
    for i in range(band_h):
        alpha = int(190 * (1 - i / band_h))   # 190（深）→ 0（透明）
        y = i if side == "top" else CANVAS_H - 1 - i
        draw.line([(0, y), (CANVAS_W, y)], fill=(0, 0, 0, alpha))
    return layer


def _wrap_chinese(text, font, max_width, draw):
    """中文按宽度换行：一个字一个字试，超宽就另起一行。"""
    lines, current = [], ""
    for ch in text:
        if draw.textlength(current + ch, font=font) <= max_width:
            current += ch
        else:
            lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines


def _draw_cta(draw, x, y, text):
    """画"行动号召"胶囊按钮，返回这块的高度。"""
    pad_x, pad_y = 36, 18
    w = draw.textlength(text, font=_FONT_CTA)
    box = (x, y, x + w + pad_x * 2, y + 40 + pad_y * 2)
    draw.rounded_rectangle(box, radius=999, fill=ACCENT)
    draw.text((x + pad_x, y + pad_y - 4), text, font=_FONT_CTA, fill=WHITE)
    return box[3] - box[1]


def make_poster(bg_source, poster_info):
    """合成海报，主入口。
    bg_source：背景图（文件路径，或 Streamlit 上传的文件对象）
    poster_info：{"title","subtitle","cta","layout"}
    返回：海报文件的完整路径
    """
    bg = Image.open(bg_source).convert("RGB")
    canvas = _cover_crop(bg).convert("RGBA")

    side = "top" if poster_info.get("layout") == "top" else "bottom"
    canvas.alpha_composite(_gradient_layer(side))

    draw = ImageDraw.Draw(canvas)
    max_text_w = CANVAS_W - MARGIN_X * 2

    # 标题（最多允许 2 行）
    title_lines = _wrap_chinese(poster_info.get("title", ""),
                                _FONT_TITLE, max_text_w, draw)[:2]
    sub_lines = _wrap_chinese(poster_info.get("subtitle", ""),
                              _FONT_SUB, max_text_w, draw)[:2]

    # 先算出整块文字有多高，好决定从哪个 y 开始画
    title_h = len(title_lines) * 100
    sub_h = len(sub_lines) * 58
    block_h = title_h + 30 + sub_h + 40 + 96     # 含间距和按钮高度
    y = 90 if side == "top" else CANVAS_H - block_h - 90

    for line in title_lines:
        draw.text((MARGIN_X, y), line, font=_FONT_TITLE, fill=WHITE)
        y += 100
    y += 30
    for line in sub_lines:
        draw.text((MARGIN_X, y), line, font=_FONT_SUB, fill=(235, 235, 235))
        y += 58

    cta_text = poster_info.get("cta", "")
    if cta_text:
        _draw_cta(draw, MARGIN_X, y + 40, cta_text)

    # ---- 存进 output，文件名带时间戳 ----
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # 加毫秒，避免同一秒生成多张时文件名撞车
    now = datetime.now()
    stamp = now.strftime("%Y%m%d_%H%M%S") + f"_{now.microsecond // 1000:03d}"
    out_path = os.path.abspath(os.path.join(OUTPUT_DIR, f"海报_{stamp}.png"))
    canvas.convert("RGB").save(out_path, "PNG")
    return out_path
