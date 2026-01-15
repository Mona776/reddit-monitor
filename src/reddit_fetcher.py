"""
Reddit RSS 抓取模块
通过Reddit原生RSS获取帖子，无需API Key
"""

import feedparser
import json
import os
import re
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SUBREDDITS, POSTS_PER_SUBREDDIT, PROCESSED_POSTS_FILE, MAX_PROCESSED_POSTS


def clean_html(html_content: str) -> str:
    """清理HTML内容，提取纯文本"""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, 'html.parser')
    # 移除所有脚本和样式
    for script in soup(["script", "style"]):
        script.decompose()
    text = soup.get_text(separator=' ', strip=True)
    # 清理多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def get_post_id(entry: dict) -> str:
    """从RSS entry中提取帖子唯一ID"""
    # Reddit的entry id格式: t3_xxxxx
    return entry.get('id', entry.get('link', ''))


def fetch_subreddit_posts(subreddit: str, limit: int = 10) -> List[Dict]:
    """
    获取指定Subreddit的最新帖子
    
    Args:
        subreddit: Subreddit名称（不含r/）
        limit: 获取帖子数量
    
    Returns:
        帖子列表
    """
    url = f"https://www.reddit.com/r/{subreddit}/new.rss?limit={limit}"
    
    try:
        # 设置User-Agent避免被拒绝
        feed = feedparser.parse(url, agent='Mozilla/5.0 (compatible; RedditMonitor/1.0)')
        
        if feed.bozo:  # 解析错误
            print(f"[警告] 解析 r/{subreddit} RSS 失败: {feed.bozo_exception}")
            return []
        
        posts = []
        for entry in feed.entries[:limit]:
            # 提取帖子内容
            content = ""
            if 'content' in entry:
                content = entry.content[0].value if entry.content else ""
            elif 'summary' in entry:
                content = entry.summary
            
            post = {
                'id': get_post_id(entry),
                'title': entry.get('title', ''),
                'content': clean_html(content),
                'link': entry.get('link', ''),
                'author': entry.get('author', 'unknown'),
                'subreddit': subreddit,
                'published': entry.get('published', ''),
            }
            posts.append(post)
        
        print(f"[成功] 从 r/{subreddit} 获取了 {len(posts)} 条帖子")
        return posts
        
    except Exception as e:
        print(f"[错误] 获取 r/{subreddit} 失败: {e}")
        return []


def load_processed_posts() -> set:
    """加载已处理的帖子ID集合"""
    try:
        if os.path.exists(PROCESSED_POSTS_FILE):
            with open(PROCESSED_POSTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('processed_ids', []))
    except Exception as e:
        print(f"[警告] 加载已处理帖子记录失败: {e}")
    return set()


def save_processed_posts(processed_ids: set):
    """保存已处理的帖子ID"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(PROCESSED_POSTS_FILE), exist_ok=True)
        
        # 只保留最近的记录，防止文件过大
        ids_list = list(processed_ids)
        if len(ids_list) > MAX_PROCESSED_POSTS:
            ids_list = ids_list[-MAX_PROCESSED_POSTS:]
        
        data = {
            'processed_ids': ids_list,
            'last_updated': datetime.now().isoformat()
        }
        
        with open(PROCESSED_POSTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"[成功] 保存了 {len(ids_list)} 条已处理帖子记录")
    except Exception as e:
        print(f"[错误] 保存已处理帖子记录失败: {e}")


def fetch_all_new_posts() -> List[Dict]:
    """
    获取所有监控Subreddit的新帖子（排除已处理的）
    
    Returns:
        新帖子列表
    """
    processed_ids = load_processed_posts()
    all_new_posts = []
    
    for subreddit in SUBREDDITS:
        posts = fetch_subreddit_posts(subreddit, POSTS_PER_SUBREDDIT)
        
        for post in posts:
            if post['id'] not in processed_ids:
                all_new_posts.append(post)
                processed_ids.add(post['id'])
    
    # 保存更新后的已处理记录
    save_processed_posts(processed_ids)
    
    print(f"\n[汇总] 共获取 {len(all_new_posts)} 条新帖子")
    return all_new_posts


if __name__ == "__main__":
    # 测试运行
    posts = fetch_all_new_posts()
    for post in posts[:3]:
        print(f"\n--- {post['subreddit']} ---")
        print(f"标题: {post['title']}")
        print(f"链接: {post['link']}")
        print(f"内容预览: {post['content'][:200]}...")
