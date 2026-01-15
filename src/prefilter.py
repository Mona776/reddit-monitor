"""
预过滤模块
在调用 AI 前用关键词快速筛选可能相关的内容，减少 API 调用量
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RELEVANCE_KEYWORDS, EXCLUDE_KEYWORDS


def pre_filter(items: list) -> list:
    """
    预过滤内容，减少 AI 调用量
    
    规则：
    1. 排除包含 EXCLUDE_KEYWORDS 的内容（明显不相关）
    2. 优先保留包含 RELEVANCE_KEYWORDS 的内容
    3. 对于既不包含排除词也不包含相关词的，也保留（让AI判断）
    
    Args:
        items: 原始内容列表
        
    Returns:
        过滤后的内容列表
    """
    if not items:
        return []
    
    filtered = []
    excluded_count = 0
    
    for item in items:
        # 合并标题和内容进行检查
        text = (item.get('title', '') + ' ' + item.get('content', '')).lower()
        
        # 检查是否包含排除关键词
        should_exclude = False
        for kw in EXCLUDE_KEYWORDS:
            if kw.lower() in text:
                should_exclude = True
                break
        
        if should_exclude:
            excluded_count += 1
            continue
        
        # 通过排除检查的内容保留
        filtered.append(item)
    
    # 打印过滤统计
    if excluded_count > 0:
        print(f"  [预过滤] 排除 {excluded_count} 条明显不相关内容")
    print(f"  [预过滤] 保留 {len(filtered)} 条待分析")
    
    return filtered


def has_relevance_keywords(item: dict) -> bool:
    """检查内容是否包含相关关键词"""
    text = (item.get('title', '') + ' ' + item.get('content', '')).lower()
    return any(kw.lower() in text for kw in RELEVANCE_KEYWORDS)


def prioritize_by_relevance(items: list) -> list:
    """
    按相关性排序，包含相关关键词的排在前面
    这样即使后面的批次失败，前面更相关的内容已经被处理
    """
    with_keywords = []
    without_keywords = []
    
    for item in items:
        if has_relevance_keywords(item):
            with_keywords.append(item)
        else:
            without_keywords.append(item)
    
    return with_keywords + without_keywords
