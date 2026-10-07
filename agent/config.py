# Day 3：配置文件
# 作用：把"可能会变的东西"（key、网址、模型名）集中放在一个文件里
# 好处：以后换模型、换网址，只改这一个文件，不用翻遍全部代码

import os

# key 从环境变量读取，不直接写在代码里
# （代码可能给别人看，写死 key 等于把家门钥匙交出去）
# 找不到时给个空字符串，程序会在调用时给出明确报错
API_KEY = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")

# 走方舟的 Claude Code 编程通道（已实测可用）
# 注意：方舟的标准按量通道 /api/compatible 本账户未开通任何模型，不能用
BASE_URL = "https://ark.cn-beijing.volces.com/api/coding"

# 模型名（coding 通道认识的写法）
MODEL = "doubao-seed-2.1-pro"

# 每次回复最多多少 token（三样例要写 3 段完整描述，给宽一点）
MAX_TOKENS = 4096

# 等待大模型回复的秒数（thinking 模型要思考，给宽一点）
TIMEOUT = 300

# ---- Day 15：Agent Plan 生图/生视频 ----
# 注意：Agent Plan 有专属的 key 和 Base URL（/api/plan），和上面的语言模型通道不能混用
MEDIA_API_KEY = os.environ.get("ARK_AGENT_PLAN_KEY", "")
MEDIA_BASE_URL = "https://ark.cn-beijing.volces.com/api/plan/v3"

# 生图模型（Small 套餐即可用；注意官方文档里的 5.0-lite 已下线，实测会报 UnsupportedModel）
IMAGE_MODEL = "doubao-seedream-5.0-pro"
# 生视频模型（需要 Medium 及以上套餐；Small 调用会报 UnsupportedModel，程序自动降级为手动粘贴提示词）
VIDEO_MODEL = "doubao-seedance-1.5-pro"
