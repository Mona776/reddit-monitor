"""
Gemini AI 分析模块
分析Reddit帖子、评论的相关性，并生成参考回复
"""

import os
import json
import re
from typing import Dict, Optional
import google.generativeai as genai

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_MODEL, PRODUCT_NAME, PRODUCT_DESCRIPTION


# 从环境变量获取API Key
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# 分析Prompt模板（支持帖子和评论）
ANALYSIS_PROMPT = f"""Role: You are an experienced indie game developer and community member.

Task: Analyze the Reddit content below and determine if it's relevant to {PRODUCT_NAME}.

About {PRODUCT_NAME}: {PRODUCT_DESCRIPTION}

Target Users (ACCEPT these):
- Users frustrated with coding/programming for games
- Users asking for no-code or low-code game development tools
- Users showing simple game ideas but struggling to implement
- Users discussing AI tools for game development
- Users looking for ways to prototype games quickly
- Beginners wanting to make games without deep coding knowledge
- Users expressing interest in creating interactive content easily

REJECT these:
- Spam, hate speech, or pure self-promotion
- Politics, finance, or completely unrelated topics
- Advanced technical discussions that wouldn't benefit from no-code tools
- Content just showing off completed games (not seeking help)
- Job postings or hiring threads
- Generic discussions without a clear need

Content Types:
- "post": A Reddit post - respond as if replying to the post
- "comment": A Reddit comment - respond as if replying to the comment
- "search": A search result - treat same as post

If ACCEPTED, write a short, casual, empathetic reply (under 50 words):
- Validate their feeling/struggle first
- Be genuinely helpful, not salesy
- Naturally mention: "I've been prototyping with {PRODUCT_NAME} recently, it handles this kind of logic via prompts. Might be worth checking out."
- Sound like a fellow developer, not a marketer
- For comments: respond directly to what they said

CRITICAL OUTPUT RULES:
1. Output STRICT VALID JSON only
2. Do NOT use markdown code blocks
3. Do NOT add any intro or outro text
4. Use this exact structure:

{{"is_relevant": true/false, "reason": "Brief reason for decision", "reply_draft": "Your reply if accepted, empty string if rejected"}}

---
CONTENT TO ANALYZE:

Type: {{type}}
Subreddit: r/{{subreddit}}
Title/Context: {{title}}
Content: {{content}}
{{extra_info}}
"""


def init_gemini():
    """初始化Gemini客户端"""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY 环境变量未设置")
    genai.configure(api_key=GEMINI_API_KEY)


def parse_json_response(text: str) -> Optional[Dict]:
    """
    解析Gemini返回的JSON，处理各种格式问题
    """
    # 移除可能的markdown代码块
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试提取JSON部分
        match = re.search(r'\{[^{}]*"is_relevant"[^{}]*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    
    return None


def analyze_item(item: Dict) -> Optional[Dict]:
    """
    使用Gemini分析单个内容（帖子、评论或搜索结果）
    
    Args:
        item: 内容信息字典，包含type, title, content, subreddit等
    
    Returns:
        分析结果字典，包含is_relevant, reason, reply_draft
        如果分析失败返回None
    """
    try:
        init_gemini()
        
        # 获取内容类型
        content_type = item.get('type', 'post')
        
        # 构建额外信息
        extra_info = ""
        if item.get('search_keyword'):
            extra_info = f"Search Keyword: {item['search_keyword']}"
        
        # 构建完整prompt
        prompt = ANALYSIS_PROMPT.replace('{{type}}', content_type)
        prompt = prompt.replace('{{subreddit}}', item.get('subreddit', ''))
        prompt = prompt.replace('{{title}}', item.get('title', ''))
        prompt = prompt.replace('{{extra_info}}', extra_info)
        
        # 限制内容长度，避免token过多
        content = item.get('content', '')[:2000]
        prompt = prompt.replace('{{content}}', content)
        
        # 调用Gemini
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=500,
            )
        )
        
        # 解析响应
        result = parse_json_response(response.text)
        
        if result and 'is_relevant' in result:
            # 简化日志输出
            type_icon = {'post': '📝', 'comment': '💬', 'search': '🔍'}.get(content_type, '📄')
            title_preview = item.get('title', '')[:40]
            status = '✓' if result['is_relevant'] else '✗'
            print(f"  {type_icon} [{status}] {title_preview}...")
            return result
        else:
            print(f"  [警告] 无法解析响应: {response.text[:100]}")
            return None
            
    except Exception as e:
        print(f"  [错误] 分析失败: {e}")
        return None


def analyze_posts_batch(items: list) -> list:
    """
    批量分析内容
    
    Args:
        items: 内容列表（帖子、评论、搜索结果）
    
    Returns:
        包含分析结果的内容列表（只返回相关的）
    """
    relevant_items = []
    
    # 按类型统计
    stats = {'post': 0, 'comment': 0, 'search': 0}
    relevant_stats = {'post': 0, 'comment': 0, 'search': 0}
    
    print(f"\n开始分析 {len(items)} 条内容...")
    print("-" * 40)
    
    for item in items:
        content_type = item.get('type', 'post')
        stats[content_type] = stats.get(content_type, 0) + 1
        
        result = analyze_item(item)
        
        if result and result.get('is_relevant', False):
            item['analysis'] = result
            relevant_items.append(item)
            relevant_stats[content_type] = relevant_stats.get(content_type, 0) + 1
    
    # 打印统计
    print("-" * 40)
    print(f"[分析完成]")
    print(f"  帖子: {relevant_stats.get('post', 0)}/{stats.get('post', 0)} 相关")
    print(f"  评论: {relevant_stats.get('comment', 0)}/{stats.get('comment', 0)} 相关")
    print(f"  搜索: {relevant_stats.get('search', 0)}/{stats.get('search', 0)} 相关")
    print(f"  总计: {len(relevant_items)}/{len(items)} 相关")
    
    return relevant_items


# 保持向后兼容
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
        }
    ]
    
    results = analyze_posts_batch(test_items)
    print(f"\n相关内容: {len(results)} 条")
    for item in results:
        print(f"\n{item['type']}: {item['title']}")
        print(f"回复建议: {item['analysis']['reply_draft']}")
