"""
Reddit监测工具配置文件
"""

# ============ Subreddit 监控配置 ============

# 要监控的Subreddit列表（游戏开发相关）
SUBREDDITS = [
    "gamedev",           # 游戏开发主社区
    "indiegaming",       # 独立游戏
    "IndieDev",          # 独立开发者
    "godot",             # Godot引擎
    "unity",             # Unity引擎
    "unrealengine",      # Unreal引擎
    "SoloDevelopment",   # 单人开发
    "gamedesign",        # 游戏设计
]

# 每个Subreddit获取的帖子数量
POSTS_PER_SUBREDDIT = 10

# ============ 评论监控配置 ============

# 是否监控评论（关闭以提高速度）
MONITOR_COMMENTS = False

# 每个Subreddit获取的评论数量
COMMENTS_PER_SUBREDDIT = 25

# ============ 关键词搜索配置 ============

# 是否启用关键词全站搜索
ENABLE_KEYWORD_SEARCH = True

# 搜索关键词列表（精简为核心关键词）
SEARCH_KEYWORDS = [
    "no code game",
    "make game without coding",
    "AI game maker",
    "game dev beginner",
    "how to make a game",
]

# 每个关键词获取的搜索结果数量
SEARCH_RESULTS_PER_KEYWORD = 10

# ============ 产品信息 ============

PRODUCT_NAME = "wefun.ai"
PRODUCT_DESCRIPTION = "一个游戏和互动内容AI生成工具与UGC平台，可以通过prompts处理游戏逻辑"

# ============ 预过滤配置 ============

# 相关性关键词（包含这些词的内容更可能相关）
RELEVANCE_KEYWORDS = [
    'no code', 'no-code', 'without coding', 'beginner', 'newbie',
    'easy way', 'simple', 'tool', 'ai', 'generate', 'prompt',
    'help me', 'how to', 'looking for', 'recommend', 'struggling',
    'frustrated', "can't code", "don't know how", 'first game',
    'prototype', 'quick', 'fast', 'easy to use'
]

# 排除关键词（包含这些词的内容明显不相关，直接跳过）
EXCLUDE_KEYWORDS = [
    'hiring', 'job', 'position', 'salary', 'portfolio',
    'showcase', 'released', 'launched', 'check out my', 'i made',
    'my game', 'just released', 'now available', 'on steam',
    'kickstarter', 'crowdfunding', 'giveaway'
]

# ============ 存储配置 ============

# 已处理帖子记录文件路径
PROCESSED_POSTS_FILE = "data/processed_posts.json"

# 最大保留的已处理帖子数量（防止文件过大）
MAX_PROCESSED_POSTS = 5000
