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
    "learnprogramming",  # 学习编程（可能有想做游戏的新手）
]

# 每个Subreddit获取的帖子数量
POSTS_PER_SUBREDDIT = 10

# ============ 评论监控配置 ============

# 是否监控评论
MONITOR_COMMENTS = True

# 每个Subreddit获取的评论数量
COMMENTS_PER_SUBREDDIT = 25

# ============ 关键词搜索配置 ============

# 是否启用关键词全站搜索
ENABLE_KEYWORD_SEARCH = True

# 搜索关键词列表（会在全站搜索）
SEARCH_KEYWORDS = [
    "no code game",
    "make game without coding",
    "game prototype tool",
    "AI game maker",
    "frustrated with unity",
    "frustrated with godot",
    "game dev beginner",
    "simple game idea",
    "how to make a game",
    "game development help",
    "want to make a game",
    "game without programming",
]

# 每个关键词获取的搜索结果数量
SEARCH_RESULTS_PER_KEYWORD = 10

# ============ 产品信息 ============

PRODUCT_NAME = "wefun.ai"
PRODUCT_DESCRIPTION = "一个游戏和互动内容AI生成工具与UGC平台，可以通过prompts处理游戏逻辑"

# ============ AI 配置 ============

# Gemini模型配置
# 注意：如果报错404，可以尝试其他模型如 "gemini-2.0-flash-exp" 或 "gemini-pro"
GEMINI_MODEL = "gemini-2.0-flash-exp"  # 最新的快速模型

# ============ 存储配置 ============

# 已处理帖子记录文件路径
PROCESSED_POSTS_FILE = "data/processed_posts.json"

# 最大保留的已处理帖子数量（防止文件过大）
MAX_PROCESSED_POSTS = 5000
