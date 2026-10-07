# Day 9：三样例整理
# 作用：校验大模型给的 samples 是否正好是
#       精修同款 / 换风格 / 换场景，并给每段配上即梦画质尾巴

from jimeng_export import QUALITY_SUFFIX

# 规定好的三样例名字（顺序也是展示顺序）
REQUIRED_VARIANTS = ["精修同款", "换风格", "换场景"]


def normalize_samples(answer):
    """把 samples 整理成统一格式的列表。
    返回：[{"variant": 名字, "change": 改动点, "prompt": 即梦提示词}, ...]
    如果模型给的名字/数量不对，返回 None（调用方据此重催）。
    """
    samples = answer.get("samples") or []
    if len(samples) != 3:
        return None

    # 按 variant 名字对齐（防止模型把顺序写乱）
    by_variant = {}
    for s in samples:
        name = (s.get("variant") or "").strip()
        by_variant[name] = s

    result = []
    for name in REQUIRED_VARIANTS:
        s = by_variant.get(name)
        if s is None:
            return None
        description = (s.get("description") or "").strip()
        if len(description) < 10:          # 描述太短说明没认真写
            return None
        result.append({
            "variant": name,
            "change": (s.get("change") or "").strip(),
            "prompt": description + "，" + QUALITY_SUFFIX,
        })
    return result


# 让大模型重交三样例的指令
RETRY_SAMPLES_DIRECTIVE = """
你的 samples 不符合要求：必须正好 3 个，
variant 名称依次为"精修同款、换风格、换场景"，
每个都要带 change（一句话改动点）和
description（基于原图的完整画面描述，六要素齐全、可直接重新生成）。
请立即重新输出完整 JSON，其他内容保持不变。
"""
