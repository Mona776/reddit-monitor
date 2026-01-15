"""
Reddit监测工具配置文件
"""

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

# 产品信息（用于Prompt）
PRODUCT_NAME = "wefun.ai"
PRODUCT_DESCRIPTION = "一个游戏和互动内容AI生成工具与UGC平台，可以通过prompts处理游戏逻辑"

# Gemini模型配置
GEMINI_MODEL = "gemini-1.5-flash"  # 快速且便宜

# 已处理帖子记录文件路径
PROCESSED_POSTS_FILE = "data/processed_posts.json"

# 最大保留的已处理帖子数量（防止文件过大）
MAX_PROCESSED_POSTS = 5000
