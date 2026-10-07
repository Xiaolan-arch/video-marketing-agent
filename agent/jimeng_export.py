# Day 8：出图提示词导出（对接免费工具"即梦"）
# 作用：把 JSON 答题卡里 prompt 的六个格子，拼成一段通顺的话
# 商家复制这段话，粘贴到即梦网页的输入框，就能出图
# 对应需求书 CLAUDE.md 6.3：把决策层 JSON 转成目标平台可粘贴文本

# 即梦看不懂"格子名"，它需要一句通顺的画面描述
# 顺序就是拍照时关注的顺序：先有什么 → 在哪 → 什么光 → 怎么取景 → 什么风格 → 什么色调
_ELEMENTS = [
    ("subject", "主体"),
    ("scene", "场景"),
    ("light", "光线"),
    ("composition", "构图"),
    ("style", "风格"),
    ("tone", "色调"),
]

# 尾巴上加几个"画质要求"，出图更精致（通用加分词）
QUALITY_SUFFIX = "高清细节，商业摄影质感，画面干净，8k超清"

# 反向提示词：告诉 AI "不要什么"，即梦有专门的输入框
NEGATIVE_PROMPT = "低清晰度，模糊，噪点，变形，畸形，多余手指，文字错乱，水印，构图杂乱"


def build_jimeng_prompt(answer):
    """把答卷里的 prompt 拼成即梦正向提示词（一段通顺文字）。
    没有内容的格子自动跳过，不会出现"主体："这种空壳。
    """
    prompt = answer.get("prompt") or {}
    parts = []
    for key, _label in _ELEMENTS:
        value = prompt.get(key, "")
        if value:
            parts.append(value.strip())
    if not parts:
        return ""
    return "，".join(parts) + "，" + QUALITY_SUFFIX


# 需要展示出图提示词的任务类型
IMAGE_TASK_TYPES = {"text_to_image", "image_optimize", "poster"}


def should_export(answer):
    """这次任务要不要给出即梦提示词。"""
    if answer.get("task_type") not in IMAGE_TASK_TYPES:
        return False
    return bool(build_jimeng_prompt(answer))
