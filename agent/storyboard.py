# Day 11：视频分镜整理
# 作用：校验大模型给的 storyboard 是否合格（3-5 镜、每镜格子齐全），
#       并把每个镜头整理成"可复制"的画面提示词，
#       以后逐镜粘贴到可灵/即梦生成视频片段，再用剪映合成成片

from jimeng_export import QUALITY_SUFFIX

# 视频质感只有这两种，多一个字少一个字都算不合格
VIDEO_STYLES = ["电影质感", "带货风格"]

# 景别只能从这五个词里选（行话：远景→特写，越往后画面越"近"）
SCALE_CHOICES = ["远景", "全景", "中景", "近景", "特写"]


def normalize_storyboard(answer):
    """校验并整理分镜。
    返回：{"video_style": 质感, "shots": [整理后的镜头, ...]}
          每个镜头含 shot/scale/camera/light/line/subtitle/prompt
    不合格返回 None（调用方据此拿 RETRY 指令重催一次）。
    """
    video_style = (answer.get("video_style") or "").strip()
    if video_style not in VIDEO_STYLES:
        return None

    # 视频任务必须填主体和场景，否则每镜提示词不知道在拍什么
    base = answer.get("prompt") or {}
    subject = (base.get("subject") or "").strip()
    scene = (base.get("scene") or "").strip()
    if not subject:
        return None

    shots = answer.get("storyboard") or []
    if not 3 <= len(shots) <= 5:        # 3-5 镜，少了多了都不行
        return None

    result = []
    for i, s in enumerate(shots, 1):
        scale = (s.get("scale") or "").strip()
        camera = (s.get("camera") or "").strip()
        light = (s.get("light") or "").strip()
        line = (s.get("line") or "").strip()
        subtitle = (s.get("subtitle") or "").strip()

        # 景别必须是五个标准词之一；运镜、光线不能为空；
        # 旁白和字幕至少要有一个，不然这一镜没内容
        if scale not in SCALE_CHOICES or not camera or not light \
                or not (line or subtitle):
            return None

        # 拼这一镜的画面提示词：主体 + 场景（没有场景就跳过）+ 景别运镜光线 + 画质尾巴
        visual_parts = [subject]
        if scene:
            visual_parts.append(scene)
        visual_parts += [scale, camera, light, QUALITY_SUFFIX]

        result.append({
            "shot": i,                  # 镜头序号重新编号，防止模型编号乱
            "scale": scale,
            "camera": camera,
            "light": light,
            "line": line,
            "subtitle": subtitle,
            "prompt": "，".join(visual_parts),
        })

    # 带货风格的两条硬性要求（电影质感不要求）：
    # 至少一个特写展示商品；每镜都要有卡点字幕
    if video_style == "带货风格":
        if not any(s["scale"] == "特写" for s in result):
            return None
        if not all(s["subtitle"] for s in result):
            return None

    return {"video_style": video_style, "shots": result}


def format_script(board):
    """把整理好的分镜转成纯文本"拍摄脚本"。
    用途：存进 output 的 TXT，或给剪辑师看（人看的版本，不是给 AI 的）。
    """
    lines = [f"视频风格：{board['video_style']}", ""]
    for s in board["shots"]:
        lines.append(f"镜头 {s['shot']}｜{s['scale']}｜运镜：{s['camera']}")
        lines.append(f"光线：{s['light']}")
        if s["line"]:
            lines.append(f"旁白：{s['line']}")
        if s["subtitle"]:
            lines.append(f"字幕：{s['subtitle']}")
        lines.append("")
    return "\n".join(lines)


# 让大模型重交分镜的指令
RETRY_STORYBOARD_DIRECTIVE = """
你的视频答卷不符合要求，请立即重新输出完整 JSON：
1. video_style 必须二选一：电影质感 或 带货风格
2. prompt 里必须填好 subject（商品/主体长什么样），尽量填 scene（在什么环境）
3. storyboard 必须 3-5 个镜头，按播放顺序编号，每镜都要有：
   scale（远景/全景/中景/近景/特写 五选一）、
   camera（运镜）、light（光线），line 旁白或 subtitle 字幕至少一个
4. 电影质感：镜头语言讲究、旁白有叙事感，subtitle 留空；
   带货风格：第 1 镜开场钩子、至少一个特写展示商品、
   每镜都写卡点字幕、最后一镜行动号召
其他内容保持不变。
"""
