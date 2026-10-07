# Day 15：接入方舟 Agent Plan 生图/生视频
# 作用：把决策层给的提示词直接变成图/视频，不用再手动粘贴到即梦/可灵
# 走 Agent Plan 专属通道（/api/plan/v3），扣的是套餐里的 AFP 物料值
#
# 两个接口长得不一样：
#   生图：同步接口，一次请求等结果（约 10~30 秒）
#   生视频：异步任务，先建任务再轮询（1~5 分钟）
# 注意：Agent Plan 的 key 和 Base URL 与语言模型通道不同，不能混用；
#       Small 套餐不支持生视频，调用会报 UnsupportedModel，由调用方降级处理

import os
import time
import requests

import config

# 和 saver.py 一样的 output 目录约定
HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(HERE, "..", "output")


class MediaError(Exception):
    """生图/生视频失败。str(err) 就是给人看的原因。"""


def _headers():
    """带上 Agent Plan 专属 key 的请求头。没配 key 就给出明确提示。"""
    if not config.MEDIA_API_KEY:
        raise MediaError("未配置 Agent Plan 专属 Key：请先设置环境变量 ARK_AGENT_PLAN_KEY")
    return {
        "Authorization": f"Bearer {config.MEDIA_API_KEY}",
        "Content-Type": "application/json",
    }


def _fail(prefix, e):
    """统一把 requests 的各种异常翻成一句人话。"""
    resp = getattr(e, "response", None)
    reason = resp.text[:200] if resp is not None else str(e)
    raise MediaError(f"{prefix}{reason}")


def _download(url, path):
    """把生成好的图/视频从云端下载到 output 文件夹。"""
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    with open(path, "wb") as f:
        f.write(resp.content)
    return path


def gen_image(prompt, stamp, size="2K"):
    """文生图：提示词 -> 一张图。成功返回本地文件路径，失败抛 MediaError。"""
    try:
        resp = requests.post(
            config.MEDIA_BASE_URL + "/images/generations",
            headers=_headers(),
            json={
                "model": config.IMAGE_MODEL,
                "prompt": prompt,
                "response_format": "url",
                "size": size,
                "watermark": False,
            },
            timeout=180,
        )
        resp.raise_for_status()
        url = resp.json()["data"][0]["url"]
    except MediaError:
        raise
    except Exception as e:
        _fail("生图失败：", e)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"生图_{stamp}.jpeg")
    try:
        _download(url, path)
    except Exception as e:
        raise MediaError(f"图片下载失败：{e}；原始链接：{url[:80]}")
    return path


def gen_video(prompt, stamp, poll_seconds=20, max_wait=600):
    """文生视频：提示词 -> 一段视频。先建任务，再每隔 poll_seconds 秒查一次。
    成功返回本地文件路径；套餐不支持/任务失败/超时抛 MediaError。
    """
    try:
        resp = requests.post(
            config.MEDIA_BASE_URL + "/contents/generations/tasks",
            headers=_headers(),
            json={
                "model": config.VIDEO_MODEL,
                "content": [{"type": "text", "text": prompt}],
                "watermark": False,
            },
            timeout=60,
        )
        resp.raise_for_status()
        task_id = resp.json()["id"]
    except MediaError:
        raise
    except Exception as e:
        _fail("创建视频任务失败：", e)

    # 异步任务状态流转：queued -> running -> succeeded / failed / cancelled
    deadline = time.time() + max_wait
    while time.time() < deadline:
        time.sleep(poll_seconds)
        try:
            r = requests.get(
                config.MEDIA_BASE_URL + "/contents/generations/tasks/" + task_id,
                headers=_headers(),
                timeout=30,
            )
            r.raise_for_status()
            task = r.json()
        except Exception as e:
            raise MediaError(f"查询视频任务失败：{e}")

        status = task.get("status")
        if status == "succeeded":
            url = (task.get("content") or {}).get("video_url", "")
            if not url:
                raise MediaError("视频任务完成但没有返回视频地址")
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            path = os.path.join(OUTPUT_DIR, f"生视频_{stamp}.mp4")
            _download(url, path)
            return path
        if status in ("failed", "cancelled"):
            raise MediaError(f"视频生成未完成（状态：{status}）")

    raise MediaError("视频生成超时（超过 10 分钟），可稍后到方舟控制台查看任务结果")
