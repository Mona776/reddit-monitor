"""
Gemini AI 分析模块
分析Reddit帖子的相关性，并生成参考回复
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

# 分析Prompt模板
ANALYSIS_PROMPT = f"""Role: You are an experienced indie game developer and community member.

Task: Analyze the Reddit post below and determine if it's relevant to {PRODUCT_NAME}.

About {PRODUCT_NAME}: {PRODUCT_DESCRIPTION}

Target Users (ACCEPT these posts):
- Users frustrated with coding/programming for games
- Users asking for no-code or low-code game development tools
- Users showing simple game ideas but struggling to implement
- Users discussing AI tools for game development
- Users looking for ways to prototype games quickly
- Beginners wanting to make games without deep coding knowledge

REJECT these posts:
- Spam, hate speech, or pure self-promotion
- Politics, finance, or completely unrelated topics
- Advanced technical discussions that wouldn't benefit from no-code tools
- Posts just showing off completed games (not seeking help)
- Job postings or hiring threads

If ACCEPTED, write a short, casual, empathetic reply (under 50 words):
- Validate their feeling/struggle first
- Be genuinely helpful, not salesy
- Naturally mention: "I've been prototyping with {PRODUCT_NAME} recently, it handles this kind of logic via prompts. Might be worth checking out."
- Sound like a fellow developer, not a marketer

CRITICAL OUTPUT RULES:
1. Output STRICT VALID JSON only
2. Do NOT use markdown code blocks
3. Do NOT add any intro or outro text
4. Use this exact structure:

{{"is_relevant": true/false, "reason": "Brief reason for decision", "reply_draft": "Your reply if accepted, empty string if rejected"}}

---
POST TO ANALYZE:

Subreddit: r/{{subreddit}}
Title: {{title}}
Content: {{content}}
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


def analyze_post(post: Dict) -> Optional[Dict]:
    """
    使用Gemini分析单个帖子
    
    Args:
        post: 帖子信息字典，包含title, content, subreddit等
    
    Returns:
        分析结果字典，包含is_relevant, reason, reply_draft
        如果分析失败返回None
    """
    try:
        init_gemini()
        
        # 构建完整prompt
        prompt = ANALYSIS_PROMPT.replace('{{subreddit}}', post.get('subreddit', ''))
        prompt = prompt.replace('{{title}}', post.get('title', ''))
        
        # 限制内容长度，避免token过多
        content = post.get('content', '')[:2000]
        prompt = prompt.replace('{{content}}', content)
        
        # 调用Gemini
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,  # 降低随机性，保持一致性
                max_output_tokens=500,
            )
        )
        
        # 解析响应
        result = parse_json_response(response.text)
        
        if result and 'is_relevant' in result:
            print(f"[分析完成] {post['title'][:50]}... -> 相关: {result['is_relevant']}")
            return result
        else:
            print(f"[警告] 无法解析Gemini响应: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"[错误] 分析帖子失败: {e}")
        return None


def analyze_posts_batch(posts: list) -> list:
    """
    批量分析帖子
    
    Args:
        posts: 帖子列表
    
    Returns:
        包含分析结果的帖子列表（只返回相关的）
    """
    relevant_posts = []
    
    for post in posts:
        result = analyze_post(post)
        
        if result and result.get('is_relevant', False):
            # 将分析结果合并到帖子信息中
            post['analysis'] = result
            relevant_posts.append(post)
    
    print(f"\n[汇总] 共 {len(posts)} 条帖子，{len(relevant_posts)} 条相关")
    return relevant_posts


if __name__ == "__main__":
    # 测试运行
    test_post = {
        'id': 'test123',
        'title': 'I want to make a simple puzzle game but coding is so frustrating',
        'content': 'I have this idea for a match-3 puzzle game but every time I try to code the logic I get stuck. Is there an easier way to prototype game mechanics without writing tons of code?',
        'subreddit': 'gamedev',
        'link': 'https://reddit.com/test',
        'author': 'testuser'
    }
    
    result = analyze_post(test_post)
    if result:
        print(f"\n结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
