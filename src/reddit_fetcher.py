"""
Reddit RSS 抓取模块
通过Reddit原生RSS获取帖子、评论和搜索结果，无需API Key
"""

import feedparser
import json
import os
import re
import time
import urllib.parse
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    SUBREDDITS, POSTS_PER_SUBREDDIT, PROCESSED_POSTS_FILE, MAX_PROCESSED_POSTS,
    MONITOR_COMMENTS, COMMENTS_PER_SUBREDDIT,
    ENABLE_KEYWORD_SEARCH, SEARCH_KEYWORDS, SEARCH_RESULTS_PER_KEYWORD
)

# Reddit RSS 请求间隔（秒），避免被限流
REQUEST_DELAY = 0.3


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


def get_item_id(entry: dict) -> str:
    """从RSS entry中提取唯一ID"""
    return entry.get('id', entry.get('link', ''))


def parse_feed_with_retry(url: str, max_retries: int = 3) -> Optional[feedparser.FeedParserDict]:
    """带重试的RSS解析"""
    for attempt in range(max_retries):
        try:
            feed = feedparser.parse(url, agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
            if not feed.bozo:
                return feed
            if attempt < max_retries - 1:
                time.sleep(REQUEST_DELAY)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(REQUEST_DELAY)
    return None


def fetch_subreddit_posts(subreddit: str, limit: int = 10) -> List[Dict]:
    """
    获取指定Subreddit的最新帖子
    """
    url = f"https://www.reddit.com/r/{subreddit}/new.rss?limit={limit}"
    
    feed = parse_feed_with_retry(url)
    if not feed:
        print(f"[警告] 获取 r/{subreddit} 帖子失败")
        return []
    
    posts = []
    for entry in feed.entries[:limit]:
        content = ""
        if 'content' in entry:
            content = entry.content[0].value if entry.content else ""
        elif 'summary' in entry:
            content = entry.summary
        
        post = {
            'id': get_item_id(entry),
            'type': 'post',  # 标记类型
            'title': entry.get('title', ''),
            'content': clean_html(content),
            'link': entry.get('link', ''),
            'author': entry.get('author', 'unknown'),
            'subreddit': subreddit,
            'published': entry.get('published', ''),
        }
        posts.append(post)
    
    print(f"[帖子] r/{subreddit}: 获取 {len(posts)} 条")
    time.sleep(REQUEST_DELAY)
    return posts


def fetch_subreddit_comments(subreddit: str, limit: int = 25) -> List[Dict]:
    """
    获取指定Subreddit的最新评论
    """
    url = f"https://www.reddit.com/r/{subreddit}/comments.rss?limit={limit}"
    
    feed = parse_feed_with_retry(url)
    if not feed:
        print(f"[警告] 获取 r/{subreddit} 评论失败")
        return []
    
    comments = []
    for entry in feed.entries[:limit]:
        content = ""
        if 'content' in entry:
            content = entry.content[0].value if entry.content else ""
        elif 'summary' in entry:
            content = entry.summary
        
        # 评论的标题通常包含原帖信息
        title = entry.get('title', '')
        
        comment = {
            'id': get_item_id(entry),
            'type': 'comment',  # 标记类型
            'title': title,  # 评论的上下文标题
            'content': clean_html(content),
            'link': entry.get('link', ''),
            'author': entry.get('author', 'unknown'),
            'subreddit': subreddit,
            'published': entry.get('published', ''),
        }
        comments.append(comment)
    
    print(f"[评论] r/{subreddit}: 获取 {len(comments)} 条")
    time.sleep(REQUEST_DELAY)
    return comments


def fetch_keyword_search(keyword: str, limit: int = 10) -> List[Dict]:
    """
    全站搜索关键词
    """
    # URL编码关键词
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://www.reddit.com/search.rss?q={encoded_keyword}&sort=new&limit={limit}"
    
    feed = parse_feed_with_retry(url)
    if not feed:
        print(f"[警告] 搜索 '{keyword}' 失败")
        return []
    
    results = []
    for entry in feed.entries[:limit]:
        content = ""
        if 'content' in entry:
            content = entry.content[0].value if entry.content else ""
        elif 'summary' in entry:
            content = entry.summary
        
        # 尝试从链接中提取subreddit
        link = entry.get('link', '')
        subreddit_match = re.search(r'/r/([^/]+)/', link)
        subreddit = subreddit_match.group(1) if subreddit_match else 'unknown'
        
        result = {
            'id': get_item_id(entry),
            'type': 'search',  # 标记为搜索结果
            'title': entry.get('title', ''),
            'content': clean_html(content),
            'link': link,
            'author': entry.get('author', 'unknown'),
            'subreddit': subreddit,
            'published': entry.get('published', ''),
            'search_keyword': keyword,  # 记录搜索关键词
        }
        results.append(result)
    
    print(f"[搜索] '{keyword}': 获取 {len(results)} 条")
    time.sleep(REQUEST_DELAY)
    return results


def load_processed_posts() -> set:
    """加载已处理的帖子ID集合"""
    try:
        if os.path.exists(PROCESSED_POSTS_FILE):
            with open(PROCESSED_POSTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('processed_ids', []))
    except Exception as e:
        print(f"[警告] 加载已处理记录失败: {e}")
    return set()


def save_processed_posts(processed_ids: set):
    """保存已处理的帖子ID"""
    try:
        os.makedirs(os.path.dirname(PROCESSED_POSTS_FILE), exist_ok=True)
        
        ids_list = list(processed_ids)
        if len(ids_list) > MAX_PROCESSED_POSTS:
            ids_list = ids_list[-MAX_PROCESSED_POSTS:]
        
        data = {
            'processed_ids': ids_list,
            'last_updated': datetime.now().isoformat()
        }
        
        with open(PROCESSED_POSTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"[存储] 保存了 {len(ids_list)} 条已处理记录")
    except Exception as e:
        print(f"[错误] 保存已处理记录失败: {e}")


def fetch_all_new_posts() -> List[Dict]:
    """
    获取所有来源的新内容（帖子、评论、搜索结果）
    
    Returns:
        新内容列表（已去重）
    """
    processed_ids = load_processed_posts()
    all_new_items = []
    
    stats = {'posts': 0, 'comments': 0, 'search': 0}
    
    # 1. 获取Subreddit帖子
    print("\n📝 获取帖子...")
    print("-" * 40)
    for subreddit in SUBREDDITS:
        posts = fetch_subreddit_posts(subreddit, POSTS_PER_SUBREDDIT)
        for post in posts:
            if post['id'] not in processed_ids:
                all_new_items.append(post)
                processed_ids.add(post['id'])
                stats['posts'] += 1
    
    # 2. 获取Subreddit评论
    if MONITOR_COMMENTS:
        print("\n💬 获取评论...")
        print("-" * 40)
        for subreddit in SUBREDDITS:
            comments = fetch_subreddit_comments(subreddit, COMMENTS_PER_SUBREDDIT)
            for comment in comments:
                if comment['id'] not in processed_ids:
                    all_new_items.append(comment)
                    processed_ids.add(comment['id'])
                    stats['comments'] += 1
    
    # 3. 关键词搜索
    if ENABLE_KEYWORD_SEARCH:
        print("\n🔍 关键词搜索...")
        print("-" * 40)
        for keyword in SEARCH_KEYWORDS:
            results = fetch_keyword_search(keyword, SEARCH_RESULTS_PER_KEYWORD)
            for result in results:
                if result['id'] not in processed_ids:
                    all_new_items.append(result)
                    processed_ids.add(result['id'])
                    stats['search'] += 1
    
    # 保存更新后的已处理记录
    save_processed_posts(processed_ids)
    
    # 打印统计
    print(f"\n{'=' * 40}")
    print(f"[汇总] 新内容统计:")
    print(f"  - 帖子: {stats['posts']} 条")
    print(f"  - 评论: {stats['comments']} 条")
    print(f"  - 搜索: {stats['search']} 条")
    print(f"  - 总计: {len(all_new_items)} 条")
    print(f"{'=' * 40}")
    
    return all_new_items


if __name__ == "__main__":
    # 测试运行
    items = fetch_all_new_posts()
    for item in items[:5]:
        print(f"\n--- [{item['type']}] r/{item['subreddit']} ---")
        print(f"标题: {item['title'][:80]}...")
        print(f"链接: {item['link']}")
        if item.get('search_keyword'):
            print(f"关键词: {item['search_keyword']}")
