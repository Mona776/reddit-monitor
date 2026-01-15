"""
Gemini AI 分析模块
批量分析Reddit帖子、评论的相关性，并生成参考回复
"""

import os
import json
import re
import time
from typing import Dict, List, Optional
import google.generativeai as genai

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_MODEL, PRODUCT_NAME, PRODUCT_DESCRIPTION


# 从环境变量获取API Key
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# 每批处理的内容数量
BATCH_SIZE = 10

# 请求间隔（秒）
REQUEST_DELAY = 2.0

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


def init_gemini():
    """初始化Gemini客户端"""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY 环境变量未设置")
    genai.configure(api_key=GEMINI_API_KEY)


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


def analyze_batch(items: List[Dict], batch_start_index: int) -> List[Dict]:
    """
    批量分析一组内容
    
    Args:
        items: 要分析的内容列表
        batch_start_index: 批次起始索引（用于日志）
    
    Returns:
        分析结果列表
    """
    if not items:
        return []
    
    try:
        init_gemini()
        
        # 构建批量prompt
        prompt = BATCH_ANALYSIS_PROMPT
        for i, item in enumerate(items):
            prompt += format_item_for_prompt(i, item)
        
        # 调用Gemini
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=2000,  # 增加输出长度以容纳多个结果
            )
        )
        
        # 解析响应
        results = parse_batch_response(response.text)
        
        if results:
            print(f"  批次 {batch_start_index//BATCH_SIZE + 1}: 成功分析 {len(results)} 条")
            return results
        else:
            print(f"  批次 {batch_start_index//BATCH_SIZE + 1}: 解析失败")
            return []
            
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower():
            print(f"  批次 {batch_start_index//BATCH_SIZE + 1}: 配额限制，等待后重试...")
            time.sleep(30)  # 等待30秒后重试
            try:
                return analyze_batch(items, batch_start_index)
            except:
                pass
        print(f"  批次 {batch_start_index//BATCH_SIZE + 1}: 错误 - {error_msg[:100]}")
        return []


def analyze_posts_batch(items: list) -> list:
    """
    批量分析所有内容
    
    Args:
        items: 内容列表（帖子、评论、搜索结果）
    
    Returns:
        包含分析结果的内容列表（只返回相关的）
    """
    if not items:
        return []
    
    relevant_items = []
    total_batches = (len(items) + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"\n开始批量分析 {len(items)} 条内容（{total_batches} 批，每批 {BATCH_SIZE} 条）...")
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
        
        # 分析当前批次
        results = analyze_batch(batch_items, batch_idx)
        
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
        
        # 批次间延迟
        if batch_idx + BATCH_SIZE < len(items):
            time.sleep(REQUEST_DELAY)
    
    # 打印统计
    print("-" * 50)
    print(f"[分析完成]")
    print(f"  帖子: {relevant_stats.get('post', 0)}/{stats.get('post', 0)} 相关")
    print(f"  评论: {relevant_stats.get('comment', 0)}/{stats.get('comment', 0)} 相关")
    print(f"  搜索: {relevant_stats.get('search', 0)}/{stats.get('search', 0)} 相关")
    print(f"  总计: {len(relevant_items)}/{len(items)} 相关")
    
    return relevant_items


# 保持向后兼容的单条分析函数
def analyze_item(item: Dict) -> Optional[Dict]:
    """分析单个内容（向后兼容）"""
    results = analyze_batch([item], 0)
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
        {
            'id': 'test2',
            'type': 'comment',
            'title': 'Re: Best tools for beginners?',
            'content': 'I really wish there was a way to make games without learning to code. Unity is too complex for me.',
            'subreddit': 'gamedev',
            'link': 'https://reddit.com/test2',
            'author': 'testuser2'
        },
        {
            'id': 'test3',
            'type': 'post',
            'title': 'Check out my new FPS game!',
            'content': 'Just released my game on Steam after 2 years of development. Link in comments.',
            'subreddit': 'gamedev',
            'link': 'https://reddit.com/test3',
            'author': 'testuser3'
        }
    ]
    
    results = analyze_posts_batch(test_items)
    print(f"\n相关内容: {len(results)} 条")
    for item in results:
        print(f"\n{item['type']}: {item['title']}")
        print(f"回复建议: {item['analysis']['reply_draft']}")
