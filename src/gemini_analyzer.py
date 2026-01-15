"""
AI 分析模块
批量分析Reddit帖子、评论的相关性，并生成参考回复
支持 Gemini 和 DeepSeek 双模型，自动故障转移
"""

import os
import json
import re
import time
from typing import Dict, List, Optional

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PRODUCT_NAME, PRODUCT_DESCRIPTION


# ============ API Keys ============
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')

# ============ 模型配置 ============
GEMINI_MODEL = "gemini-2.0-flash-lite"
DEEPSEEK_MODEL = "deepseek-chat"

# ============ 处理配置 ============
BATCH_SIZE = 20
REQUEST_DELAY = 15.0
MAX_RETRIES = 1  # Gemini 重试次数，失败后切换到 DeepSeek

# ============ 当前使用的模型 ============
current_provider = "gemini"  # gemini 或 deepseek
gemini_exhausted = False  # Gemini 配额是否用完

# ============ Prompt 模板 ============
BATCH_ANALYSIS_PROMPT = f"""# Role & Persona
You are a scatterbrained, slightly tired indie dev browsing Reddit at 3 AM. You are NOT a helpful assistant. You are just a fellow dev reacting naturally.

About {PRODUCT_NAME}: {PRODUCT_DESCRIPTION}

# Task
Analyze Reddit posts to find potential users for {PRODUCT_NAME}, then write replies that sound like a real human dev.

# Target Users (ACCEPT):
- Users frustrated with coding/programming for games
- Users asking for no-code or low-code game development tools
- Users with simple game ideas but struggling to implement
- Users discussing AI tools for game development
- Users looking for ways to prototype games quickly
- Beginners wanting to make games without deep coding knowledge

# REJECT:
- Spam, hate speech, self-promotion
- Politics, finance, unrelated topics
- Advanced technical discussions (they don't need our tool)
- Showing off completed games (not seeking help)
- Job postings

# Reply Style Rules (CRITICAL - read carefully)
For ACCEPTED items, write a reply that sounds like a tired dev at 3am:

1. **lowercase only** - no capital letters
2. **no transitions** - don't use "However", "Also", "In addition". just jump to next thought
3. **fragments ok** - "honestly idk. maybe check your collider?" is better than full sentences
4. **be jumpy** - start with one thought, jump to another, circle back
5. **DO NOT always mention {PRODUCT_NAME}** - only mention it ~20% of the time when it fits VERY naturally. most replies should just be genuine community interaction without any product mention.
6. **under 50 words**
7. **goal is to sound like a real community member** - helpful, relatable, human

# Example Good Replies (most WITHOUT product mention):
- "oh man i feel this. spent 3 days on pathfinding last month lol. unity navmesh is weird but once it clicks its fine"
- "honestly just start with a game jam project. 48 hours forces you to scope small. learned more from jams than any tutorial"
- "yeah the node system takes getting used to. i kept trying to do everything in code at first. big mistake"
- "dude same. i rewrote my inventory system like 4 times before it worked lmao"
- (rarely, only when very relevant) "been messing with {PRODUCT_NAME} for prototyping lately, handles logic via prompts. might be worth a look if coding isnt ur thing"

# Output Format
JSON ARRAY only. No markdown code blocks.
[
  {{"index": 0, "is_relevant": true, "reason": "...", "reply_draft": "..."}},
  {{"index": 1, "is_relevant": false, "reason": "...", "reply_draft": ""}}
]

---
CONTENT ITEMS TO ANALYZE:

"""


def parse_batch_response(text: str) -> List[Dict]:
    """解析批量分析的JSON数组响应"""
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    
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
    content = item.get('content', '')[:500]
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


def call_gemini(prompt: str) -> Optional[str]:
    """调用 Gemini API"""
    from google import genai
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "temperature": 0.3,
            "max_output_tokens": 2000,
        }
    )
    return response.text


def call_deepseek(prompt: str) -> Optional[str]:
    """调用 DeepSeek API (OpenAI 兼容)"""
    import openai
    
    client = openai.OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )
    
    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that analyzes Reddit content and outputs JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=2000
    )
    
    return response.choices[0].message.content


def analyze_batch(items: List[Dict], batch_num: int, retry_count: int = 0) -> List[Dict]:
    """
    批量分析一组内容，支持 Gemini/DeepSeek 故障转移
    """
    global gemini_exhausted, current_provider
    
    if not items:
        return []
    
    # 构建 prompt
    prompt = BATCH_ANALYSIS_PROMPT
    for i, item in enumerate(items):
        prompt += format_item_for_prompt(i, item)
    
    # 选择使用哪个模型
    use_deepseek = gemini_exhausted or not GEMINI_API_KEY
    
    if use_deepseek and not DEEPSEEK_API_KEY:
        print(f"  批次 {batch_num}: 无可用的 API Key，跳过")
        return []
    
    try:
        if use_deepseek:
            current_provider = "deepseek"
            print(f"  批次 {batch_num}: 使用 DeepSeek...")
            response_text = call_deepseek(prompt)
        else:
            current_provider = "gemini"
            response_text = call_gemini(prompt)
        
        # 解析响应
        results = parse_batch_response(response_text)
        
        if results:
            print(f"  批次 {batch_num}: 成功分析 {len(results)} 条 ({current_provider})")
            return results
        else:
            print(f"  批次 {batch_num}: 解析失败，跳过")
            return []
            
    except Exception as e:
        error_msg = str(e)
        
        # Gemini 配额用完，切换到 DeepSeek
        if not use_deepseek and ("429" in error_msg or "quota" in error_msg.lower()):
            if retry_count < MAX_RETRIES:
                wait_time = 10 * (retry_count + 1)
                print(f"  批次 {batch_num}: Gemini 配额限制，等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                return analyze_batch(items, batch_num, retry_count + 1)
            
            # 重试后仍然失败，切换到 DeepSeek
            if DEEPSEEK_API_KEY:
                print(f"  批次 {batch_num}: Gemini 配额用完，切换到 DeepSeek...")
                gemini_exhausted = True
                return analyze_batch(items, batch_num, 0)  # 用 DeepSeek 重试
            else:
                print(f"  批次 {batch_num}: Gemini 配额用完，无 DeepSeek Key，跳过")
                return []
        
        # 其他错误
        print(f"  批次 {batch_num}: 错误 - {error_msg[:80]}，跳过")
        return []


def analyze_posts_batch(items: list) -> list:
    """批量分析所有内容"""
    if not items:
        return []
    
    relevant_items = []
    total_batches = (len(items) + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"\n开始批量分析 {len(items)} 条内容（{total_batches} 批）...")
    print(f"  主模型: Gemini | 备用: DeepSeek")
    print("-" * 50)
    
    for batch_idx in range(0, len(items), BATCH_SIZE):
        batch_items = items[batch_idx:batch_idx + BATCH_SIZE]
        batch_num = batch_idx // BATCH_SIZE + 1
        
        results = analyze_batch(batch_items, batch_num)
        
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
        
        if batch_idx + BATCH_SIZE < len(items):
            time.sleep(REQUEST_DELAY)
    
    print("-" * 50)
    print(f"[分析完成] 相关: {len(relevant_items)}/{len(items)}")
    
    return relevant_items


# 向后兼容
def analyze_item(item: Dict) -> Optional[Dict]:
    results = analyze_batch([item], 1)
    if results and len(results) > 0:
        result = results[0]
        if isinstance(result, dict) and 'is_relevant' in result:
            return result
    return None


def analyze_post(post: Dict) -> Optional[Dict]:
    return analyze_item(post)
