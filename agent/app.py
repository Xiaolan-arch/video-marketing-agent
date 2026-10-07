# Day 6/9：Streamlit 网页
# Day 6：输入框 + 按钮的决策网页
# Day 9：新增"上传原图"，支持图片优化三样例（精修同款/换风格/换场景）
# Streamlit 的规则：代码从上到下执行一遍，就画出一个网页

import base64
from datetime import datetime

import streamlit as st

from prompt_builder import (build_prompt, FORCE_DEFAULTS_DIRECTIVE,
                            RETRY_POSTER_DIRECTIVE)
from decision import call_model, parse_answer
from saver import save_result
from jimeng_export import build_jimeng_prompt, NEGATIVE_PROMPT, should_export
from samples import normalize_samples, RETRY_SAMPLES_DIRECTIVE
from poster_maker import make_poster
from storyboard import (normalize_storyboard, format_script,
                        RETRY_STORYBOARD_DIRECTIVE)
from brand_profile import list_brands, brand_directive
import ark_media
import license

# 网页标题栏的基本设置（必须放在最前面）
st.set_page_config(page_title="营销素材决策引擎", page_icon="🎨")

st.title("🎨 营销素材决策引擎")
st.caption("可以只输入文字，也可以上传原图做三样例。信息不全时它只问一次，再不全自动补齐。")

# ---- 输入区：先上传图片（可选） ----
# file_uploader = 文件选择框；type 限制图片格式
uploaded = st.file_uploader("① 上传原图（可选，做图片优化时使用）",
                            type=["png", "jpg", "jpeg", "webp"])
if uploaded is not None:
    # 把图显示在页面上确认没传错
    st.image(uploaded, caption="已上传的原图", width=280)

# ---- 输入区：文字 ----
user_text = st.text_area(
    "② 商家的一句话需求（上传了原图也可以补充要求）：",
    height=110,
    placeholder="例如：帮我的奶茶店做一张清新风格的海报，用于小红书；上传图片时可留空",
)

# ---- 选择品牌档案 ----
# selectbox = 下拉选择框；options 第一项是"不使用"
brands = list_brands()
brand_choice = st.selectbox(
    "③ 选择品牌档案（可选，选中后自动按该品牌的风格/色调生成）",
    options=["（不使用品牌档案）"] + [b["brand_name"] for b in brands])
# next：在列表里找出名字匹配的那份档案；找不到就是 None
selected = next((b for b in brands if b["brand_name"] == brand_choice), None)
if selected:
    st.caption(f"✅ 当前品牌：{selected['brand_name']}"
               f"｜风格 {selected['style']}｜色调 {selected['tone']}")

clicked = st.button("🚀 生成决策", type="primary")

# session_state：网页的"小本本"，记住是否已经问过商家一次
if "asked_once" not in st.session_state:
    st.session_state.asked_once = False

# ---- 点按钮之后才执行 ----
if clicked:
    if not uploaded and not user_text.strip():
        st.warning("请先输入文字需求，或上传一张原图～")
    elif license.remaining() <= 0:
        st.error("次数已用完：请在左侧「授权中心」输入激活码后再生成。")
    else:
        with st.spinner("大模型看图/思考中，约 30 秒到 2 分钟，请耐心等待……"):
            # 选中了品牌，就备好品牌指令段落（否则是空串，加了也没影响）
            brand_text = brand_directive(selected) if selected else ""

            if uploaded is not None:
                # 图片转成 base64 文字，放进"图片方块"
                img_block = {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": uploaded.type,
                        "data": base64.b64encode(uploaded.getvalue()).decode(),
                    },
                }
                exam_text = build_prompt(
                    user_text.strip()
                    or "请基于这张原图做图片优化，给出三样例：精修同款、换风格、换场景")
                exam_text += brand_text
                if st.session_state.asked_once:
                    exam_text += FORCE_DEFAULTS_DIRECTIVE
                # 内容 = [图片方块, 文字方块]
                content = [img_block, {"type": "text", "text": exam_text}]
            else:
                content = build_prompt(user_text) + brand_text
                if st.session_state.asked_once:
                    content += FORCE_DEFAULTS_DIRECTIVE

            raw = call_model(content)
            answer = parse_answer(raw)

            # 兜底一：补充后它还想问，立刻强催
            if st.session_state.asked_once and \
                    answer.get("task_type") == "need_more_info":
                raw = call_model(
                    content + [{"type": "text", "text": FORCE_DEFAULTS_DIRECTIVE}]
                    if isinstance(content, list)
                    else content + FORCE_DEFAULTS_DIRECTIVE)
                answer = parse_answer(raw)

            # 兜底二：图片优化但 samples 不合格，带原图重催一次
            sample_cards = None
            if answer.get("task_type") == "image_optimize":
                sample_cards = normalize_samples(answer)
                if sample_cards is None:
                    retry_content = (
                        content + [{"type": "text", "text": RETRY_SAMPLES_DIRECTIVE}]
                        if isinstance(content, list)
                        else content + RETRY_SAMPLES_DIRECTIVE)
                    answer = parse_answer(call_model(retry_content))
                    sample_cards = normalize_samples(answer)

            # 兜底三：海报字段缺失，带原图重催一次
            if answer.get("task_type") == "poster" and \
                    not (answer.get("poster") or {}).get("title"):
                retry_content = (
                    content + [{"type": "text", "text": RETRY_POSTER_DIRECTIVE}]
                    if isinstance(content, list)
                    else content + RETRY_POSTER_DIRECTIVE)
                answer = parse_answer(call_model(retry_content))

            # 兜底四：视频分镜不合格，重催一次
            board = None
            if answer.get("task_type") == "video":
                board = normalize_storyboard(answer)
                if board is None:
                    retry_content = (
                        content + [{"type": "text", "text": RETRY_STORYBOARD_DIRECTIVE}]
                        if isinstance(content, list)
                        else content + RETRY_STORYBOARD_DIRECTIVE)
                    answer = parse_answer(call_model(retry_content))
                    board = normalize_storyboard(answer)

        # ---- 情况一：信息不足，把问题摆出来 ----
        if answer.get("task_type") == "need_more_info":
            st.session_state.asked_once = True
            st.info("它还想先了解这些，请补充后再点一次「生成决策」：")
            for q in answer.get("questions", []):
                st.markdown(f"- {q}")
            st.caption("💡 补充不全也没关系：再次点击后系统会自动按默认值补齐，不会继续追问。")

        # ---- 情况二：信息够了，展示成果 ----
        else:
            st.session_state.asked_once = False
            save_result(answer)

            # ---- Day 15：自动生成媒体（生图/生视频）----
            # 规则：完整一次输出（决策 + 媒体都成功）才扣 1 次；
            #       媒体生成失败（含 Small 套餐不支持生视频）不扣，降级为手动粘贴提示词
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            media_ok = True

            if board:
                # 视频任务：拿镜头 1 的提示词去生成
                try:
                    with st.spinner("Seedance 正在生成视频片段（1~5 分钟）……"):
                        video_path = ark_media.gen_video(board["shots"][0]["prompt"], stamp)
                    st.subheader("🎬 自动生成视频片段（镜头 1）")
                    st.video(video_path)
                    st.caption("已保存到：" + video_path)
                except ark_media.MediaError as e:
                    media_ok = False
                    st.warning(f"⚠️ 视频自动生成没成功：{e}\n\n"
                               f"**本次不消耗次数**；可复制下方提示词到可灵/即梦手动生成。"
                               f"（升级 Agent Plan Medium 套餐后可自动生成）")
            else:
                # 图类任务：三样例用第 1 张的提示词，其余用六要素拼的出图提示词
                img_prompt = (sample_cards[0]["prompt"] if sample_cards
                              else build_jimeng_prompt(answer))
                if img_prompt:
                    try:
                        with st.spinner("Seedream 正在生成主图（约 10~30 秒）……"):
                            img_path = ark_media.gen_image(img_prompt, stamp)
                        st.subheader("🖼 自动生成主图")
                        st.image(img_path, width=360)
                        st.caption("已保存到：" + img_path)
                    except ark_media.MediaError as e:
                        media_ok = False
                        st.warning(f"⚠️ 自动生图没成功：{e}\n\n"
                                   f"**本次不消耗次数**；可复制下方提示词到即梦手动生成。")

            # 配额 -1（只有完整输出成功才扣），并告诉用户还剩几次
            if media_ok:
                left = license.consume()
                st.toast(f"已生成，本次消耗 1 次，剩余 {left} 次")
            else:
                st.info("本次输出不完整，未消耗次数。")

            note = answer.get("note", "")
            if note:
                st.success(note)

            # ---- 商业海报：上传了背景图就合成 ----
            poster_path = None
            if answer.get("task_type") == "poster":
                poster_info = answer.get("poster") or {}
                if uploaded is None:
                    st.info("海报需要一张背景图：可先用下面的提示词到即梦出图，"
                            "把图保存后上传到本页顶部，再点一次「生成决策」。")
                else:
                    with st.spinner("正在排版合成海报……"):
                        poster_path = make_poster(uploaded, poster_info)
                    st.subheader("📌 合成海报")
                    st.image(poster_path, width=360)
                    st.caption("已保存到：" + poster_path)

            # ---- 三样例（图片优化）----
            if sample_cards:
                st.subheader("🖼 三样例：粘贴到即梦分别生成")
                st.caption("即梦「图像生成」→ 每张粘贴对应提示词 → 比例 3:4 → 生成；满意的存进 output 文件夹。")
                for i, card in enumerate(sample_cards, 1):
                    st.markdown(f"**样例 {i}｜{card['variant']}**")
                    if card["change"]:
                        st.caption("改动点：" + card["change"])
                    st.code(card["prompt"], language=None)

            # ---- 文生图/海报的出图提示词（海报已合成就不再重复显示）----
            elif should_export(answer) and not poster_path:
                st.subheader("🎨 出图提示词（粘贴到即梦）")
                st.caption(
                    "打开 jimeng.jianying.com →「图像生成」→ 粘贴①② → "
                    "比例选 3:4（小红书竖图）→ 生成，满意后保存到 output 文件夹。")
                st.write("**① 正向提示词【可复制】**")
                st.code(build_jimeng_prompt(answer), language=None)
                st.write("**② 反向提示词【可复制】**")
                st.code(NEGATIVE_PROMPT, language=None)

            # ---- 三平台文案 ----
            copy = answer.get("copy") or {}
            if any(copy.values()):
                st.subheader("三平台文案")
                tab1, tab2, tab3 = st.tabs(["小红书", "朋友圈", "商品详情页"])
                with tab1:
                    st.write(copy.get("xiaohongshu", "（本次未生成）"))
                with tab2:
                    st.write(copy.get("moments", "（本次未生成）"))
                with tab3:
                    st.write(copy.get("detail", "（本次未生成）"))

            # ---- 视频分镜 ----
            if board:
                st.subheader("🎬 视频分镜｜" + board["video_style"])
                st.caption("逐镜复制画面提示词到可灵/即梦「视频生成」→ 生成片段 → "
                           "剪映按旁白/字幕卡点合成成片。")
                # download_button：把文字变成浏览器下载的小文件
                st.download_button("📄 下载分镜脚本 TXT",
                                   format_script(board),
                                   file_name="分镜脚本.txt",
                                   mime="text/plain")
                for s in board["shots"]:
                    st.markdown(f"**镜头 {s['shot']}｜{s['scale']}**")
                    # 两个全角空格把运镜和光线隔开
                    st.caption(f"运镜：{s['camera']}　|　光线：{s['light']}")
                    if s["line"]:
                        st.markdown(f"🎙 旁白：{s['line']}")
                    if s["subtitle"]:
                        st.markdown(f"📝 字幕：{s['subtitle']}")
                    st.code(s["prompt"], language=None)

            # ---- 完整 JSON ----
            with st.expander("查看完整 JSON（开发者）"):
                st.json(answer)

# ---- 侧边栏：授权中心（放在脚本末尾，保证读到的是扣减/激活后的最新次数）----
# Streamlit 从上到下执行一遍画出页面：如果这段放最前面，
# 侧边栏会比"生成后扣次数"先渲染，显示的就永远是旧值。
with st.sidebar:
    st.header("🔑 授权中心")
    st.write(f"剩余可用次数：**{license.remaining()}** 次")
    st.caption("新用户赠送 3 次免费试用")
    act_code = st.text_input("输入激活码")
    if st.button("激活"):
        ok, msg = license.activate(act_code)
        if ok:
            st.success(msg)
        else:
            st.error(msg)
