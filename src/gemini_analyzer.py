"""
Gemini AI 分析模块
批量分析Reddit帖子、评论的相关性，并生成参考回复
使用新版 google-genai SDK
"""

import os
import json
import re
import time
from typing import Dict, List, Optional
from google import genai

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PRODUCT_NAME, PRODUCT_DESCRIPTION


# 从环境变量获取API Key
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# 使用的模型 (官方稳定版本，确认可用至2026年2月)
MODEL_NAME = "gemini-2.0-flash-001"

# 每批处理的内容数量
BATCH_SIZE = 10

# 请求间隔（秒）
REQUEST_DELAY = 1.0

# 最大重试次数
MAX_RETRIES = 2

# 批量分析Prompt模板
BATCH_ANALYSIS_PROMPT = f"""Role: You are an experienced indie game developer helping to identify potential users for {PRODUCT_NAME}.

About {PRODUCT_NAME}: {PRODUCT_DESCRIPTION}

Task: Analyze the following Reddit content items and determine which ones are relevant.

Target Users (ACCEPT):
- Users frustrated with coding/programming for games
- Users asking for no-code or low-code game development tools
- Users with simple game ideas but struggling to implement
- Users discussing AI tools for game development
- Users looking for ways to prototype games quickly
- Beginners wanting to make games without deep coding knowledge

REJECT:
- Spam, hate speech, self-promotion
- Politics, finance, unrelated topics
- Advanced technical discussions
- Showing off completed games (not seeking help)
- Job postings

For ACCEPTED items, write a short, casual reply (under 50 words):
- Validate their struggle first
- Be genuinely helpful, not salesy
- Naturally mention: "I've been prototyping with {PRODUCT_NAME} recently, it handles this kind of logic via prompts. Might be worth checking out."
- Sound like a fellow developer

CRITICAL OUTPUT RULES:
1. Output a JSON ARRAY only
2. Each item must have: "index", "is_relevant", "reason", "reply_draft"
3. Do NOT use markdown code blocks
4. Example output format:
[
  {{"index": 0, "is_relevant": true, "reason": "...", "reply_draft": "..."}},
  {{"index": 1, "is_relevant": false, "reason": "...", "reply_draft": ""}}
]

---
CONTENT ITEMS TO ANALYZE:

"""

# 初始化客户端
client = None


def init_gemini():
    """初始化Gemini客户端"""
    global client
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY 环境变量未设置")
    client = genai.Client(api_key=GEMINI_API_KEY)


def parse_batch_response(text: str) -> List[Dict]:
    """解析批量分析的JSON数组响应"""
    # 移除markdown代码块
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    
    # 尝试提取JSON数组
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
    
    return []


def format_item_for_prompt(index: int, item: Dict) -> str:
    """格式化单个内容项用于prompt"""
    content = item.get('content', '')[:500]  # 限制每条内容长度
    title = item.get('title', '')[:200]
    
    text = f"""
[Item {index}]
Type: {item.get('type', 'post')}
Subreddit: r/{item.get('subreddit', '')}
Title: {title}
Content: {content}
"""
    if item.get('search_keyword'):
        text += f"Search Keyword: {item['search_keyword']}\n"
    
    return text


def analyze_batch(items: List[Dict], batch_num: int, retry_count: int = 0) -> List[Dict]:
    """
    批量分析一组内容
    
    Args:
        items: 要分析的内容列表
        batch_num: 批次编号（用于日志）
        retry_count: 当前重试次数
    
    Returns:
        分析结果列表
    """
    global client
    
    if not items:
        return []
    
    try:
        if client is None:
            init_gemini()
        
        # 构建批量prompt
        prompt = BATCH_ANALYSIS_PROMPT
        for i, item in enumerate(items):
            prompt += format_item_for_prompt(i, item)
        
        # 调用Gemini (新版SDK)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config={
                "temperature": 0.3,
                "max_output_tokens": 2000,
            }
        )
        
        # 解析响应
        results = parse_batch_response(response.text)
        
        if results:
            print(f"  批次 {batch_num}: 成功分析 {len(results)} 条")
            return results
        else:
            print(f"  批次 {batch_num}: 解析失败，跳过")
            return []
            
    except Exception as e:
        error_msg = str(e)
        
        # 配额限制错误，有限重试
        if ("429" in error_msg or "quota" in error_msg.lower()) and retry_count < MAX_RETRIES:
            wait_time = 10 * (retry_count + 1)  # 递增等待：10秒, 20秒
            print(f"  批次 {batch_num}: 配额限制，等待 {wait_time} 秒后重试 ({retry_count + 1}/{MAX_RETRIES})...")
            time.sleep(wait_time)
            return analyze_batch(items, batch_num, retry_count + 1)
        
        # 其他错误或重试次数用尽，跳过此批次
        print(f"  批次 {batch_num}: 错误 - {error_msg[:80]}，跳过")
        return []


def analyze_posts_batch(items: list) -> list:
    """
    批量分析所有内容
    """
    if not items:
        return []
    
    relevant_items = []
    total_batches = (len(items) + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"\n开始批量分析 {len(items)} 条内容（{total_batches} 批）...")
    print("-" * 50)
    
    # 按类型统计
    stats = {'post': 0, 'comment': 0, 'search': 0}
    relevant_stats = {'post': 0, 'comment': 0, 'search': 0}
    
    for item in items:
        content_type = item.get('type', 'post')
        stats[content_type] = stats.get(content_type, 0) + 1
    
    # 分批处理
    for batch_idx in range(0, len(items), BATCH_SIZE):
        batch_items = items[batch_idx:batch_idx + BATCH_SIZE]
        batch_num = batch_idx // BATCH_SIZE + 1
        
        # 分析当前批次
        results = analyze_batch(batch_items, batch_num)
        
        # 匹配结果到原始内容
        for result in results:
            if not isinstance(result, dict):
                continue
            
            idx = result.get('index')
            if idx is None or idx >= len(batch_items):
                continue
            
            if result.get('is_relevant', False):
                item = batch_items[idx].copy()
                item['analysis'] = {
                    'is_relevant': True,
                    'reason': result.get('reason', ''),
                    'reply_draft': result.get('reply_draft', '')
                }
                relevant_items.append(item)
                
                content_type = item.get('type', 'post')
                relevant_stats[content_type] = relevant_stats.get(content_type, 0) + 1
        
        # 批次间延迟（不是最后一批才延迟）
        if batch_idx + BATCH_SIZE < len(items):
            time.sleep(REQUEST_DELAY)
    
    # 打印统计
    print("-" * 50)
    print(f"[分析完成] 相关: {len(relevant_items)}/{len(items)}")
    
    return relevant_items


# 保持向后兼容的单条分析函数
def analyze_item(item: Dict) -> Optional[Dict]:
    """分析单个内容（向后兼容）"""
    results = analyze_batch([item], 1)
    if results and len(results) > 0:
        result = results[0]
        if isinstance(result, dict) and 'is_relevant' in result:
            return result
    return None


def analyze_post(post: Dict) -> Optional[Dict]:
    """向后兼容的函数名"""
    return analyze_item(post)


if __name__ == "__main__":
    # 测试运行
    test_items = [
        {
            'id': 'test1',
            'type': 'post',
            'title': 'I want to make a simple puzzle game but coding is so frustrating',
            'content': 'I have this idea for a match-3 puzzle game but every time I try to code the logic I get stuck.',
            'subreddit': 'gamedev',
            'link': 'https://reddit.com/test1',
            'author': 'testuser1'
        },
    ]
    
    results = analyze_posts_batch(test_items)
    print(f"\n相关内容: {len(results)} 条")
