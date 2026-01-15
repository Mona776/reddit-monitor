"""
飞书通知模块
发送交互式卡片到飞书群
支持帖子、评论和搜索结果
"""

import os
import json
import re
import requests
from typing import Dict, List
from urllib.parse import quote

# 从环境变量获取Webhook URL
FEISHU_WEBHOOK_URL = os.environ.get('FEISHU_WEBHOOK_URL', '')

# 内容类型配置
TYPE_CONFIG = {
    'post': {
        'icon': '📝',
        'label': '帖子',
        'header_color': 'blue',
        'title_label': '帖子标题',
        'button_text': 'Go to Reply (via Google)'
    },
    'comment': {
        'icon': '💬',
        'label': '评论',
        'header_color': 'purple',
        'title_label': '评论上下文',
        'button_text': 'Go to Reply (via Google)'
    },
    'search': {
        'icon': '🔍',
        'label': '搜索结果',
        'header_color': 'orange',
        'title_label': '帖子标题',
        'button_text': 'Go to Reply (via Google)'
    }
}


def extract_subreddit_from_link(link: str) -> str:
    """
    从 Reddit 链接中提取真实的 subreddit 名称
    
    Args:
        link: Reddit 帖子链接，如 https://reddit.com/r/gameideas/comments/xxx/
    
    Returns:
        subreddit 名称，如 "gameideas"
    """
    if not link:
        return ''
    match = re.search(r'/r/([^/]+)/', link)
    return match.group(1) if match else ''


def create_google_search_url(title: str, subreddit: str = '', link: str = '') -> str:
    """
    创建通过Google搜索Reddit帖子的链接
    使用 site:reddit.com/r/{subreddit} 限定搜索范围 + 引号精确匹配标题
    避免直接访问Reddit触发429限制
    
    Args:
        title: 帖子标题
        subreddit: 子版块名称（备用）
        link: 帖子链接（优先从这里提取真实 subreddit）
    
    Returns:
        Google搜索URL
    """
    if not title:
        return "https://www.google.com/search?q=site:reddit.com"
    
    # 优先从链接中提取真实的 subreddit（避免 cross-post 导致的错误）
    real_subreddit = extract_subreddit_from_link(link) or subreddit
    
    # 构建搜索查询: site:reddit.com/r/{subreddit} + "标题"（精确匹配）
    if real_subreddit:
        search_query = f'site:reddit.com/r/{real_subreddit} "{title}"'
    else:
        search_query = f'site:reddit.com "{title}"'
    
    # URL编码查询字符串（处理空格、特殊字符、emoji等）
    encoded_query = quote(search_query, safe='')
    
    return f"https://www.google.com/search?q={encoded_query}"


def create_card_message(item: Dict) -> Dict:
    """
    创建飞书卡片消息
    
    Args:
        item: 内容信息，包含type, title, content, link, subreddit, analysis等
    
    Returns:
        飞书卡片消息体
    """
    analysis = item.get('analysis', {})
    reason = analysis.get('reason', '未知')
    reply_draft = analysis.get('reply_draft', '')
    
    # 获取内容类型配置
    content_type = item.get('type', 'post')
    config = TYPE_CONFIG.get(content_type, TYPE_CONFIG['post'])
    
    # 截断内容预览
    content_preview = item.get('content', '')[:300]
    if len(item.get('content', '')) > 300:
        content_preview += '...'
    
    # 构建卡片元素
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**{config['icon']} {config['title_label']}**\n{item.get('title', '')}"
            }
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**📄 内容预览**\n{content_preview}"
            }
        },
        {"tag": "hr"},
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**🤖 AI判断理由**\n{reason}"
            }
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**💡 参考回复**\n```\n{reply_draft}\n```"
            }
        },
        {"tag": "hr"},
    ]
    
    # 添加额外信息字段
    fields = [
        {
            "is_short": True,
            "text": {
                "tag": "lark_md",
                "content": f"**作者**: u/{item.get('author', 'unknown')}"
            }
        },
        {
            "is_short": True,
            "text": {
                "tag": "lark_md",
                "content": f"**社区**: r/{item.get('subreddit', '')}"
            }
        }
    ]
    
    # 如果是搜索结果，显示搜索关键词
    if item.get('search_keyword'):
        fields.append({
            "is_short": True,
            "text": {
                "tag": "lark_md",
                "content": f"**关键词**: {item['search_keyword']}"
            }
        })
    
    elements.append({
        "tag": "div",
        "fields": fields
    })
    
    # 添加操作按钮 - 使用Google搜索链接避免Reddit 429限制
    # 优先从 link 中提取真实 subreddit，避免 cross-post 导致的错误
    google_search_url = create_google_search_url(
        title=item.get('title', ''),
        subreddit=item.get('subreddit', ''),
        link=item.get('link', '')
    )
    elements.append({
        "tag": "action",
        "actions": [
            {
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": f"🔥 {config['button_text']}"
                },
                "type": "primary",
                "url": google_search_url
            }
        ]
    })
    
    # 构建完整卡片
    card = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🎯 Reddit潜在客户 [{config['label']}] - r/{item.get('subreddit', '')}"
                },
                "template": config['header_color']
            },
            "elements": elements
        }
    }
    
    return card


def send_to_feishu(item: Dict) -> bool:
    """
    发送单个内容通知到飞书
    """
    if not FEISHU_WEBHOOK_URL:
        print("[错误] FEISHU_WEBHOOK_URL 环境变量未设置")
        return False
    
    try:
        card_message = create_card_message(item)
        
        response = requests.post(
            FEISHU_WEBHOOK_URL,
            headers={'Content-Type': 'application/json'},
            data=json.dumps(card_message),
            timeout=10
        )
        
        result = response.json()
        
        if result.get('code') == 0 or result.get('StatusCode') == 0:
            type_icon = TYPE_CONFIG.get(item.get('type', 'post'), {}).get('icon', '📄')
            print(f"  {type_icon} 已发送: {item.get('title', '')[:40]}...")
            return True
        else:
            print(f"  [失败] 飞书返回: {result}")
            return False
            
    except Exception as e:
        print(f"  [错误] 发送失败: {e}")
        return False


def send_batch_to_feishu(items: List[Dict]) -> int:
    """
    批量发送通知到飞书
    """
    if not items:
        return 0
    
    print(f"\n发送 {len(items)} 条通知到飞书...")
    print("-" * 40)
    
    success_count = 0
    for item in items:
        if send_to_feishu(item):
            success_count += 1
    
    print("-" * 40)
    print(f"[完成] {success_count}/{len(items)} 条发送成功")
    return success_count


def send_summary_to_feishu(stats: Dict) -> bool:
    """
    发送运行汇总到飞书
    
    Args:
        stats: 统计信息字典
    """
    if not FEISHU_WEBHOOK_URL:
        return False
    
    total = stats.get('total', 0)
    relevant = stats.get('relevant', 0)
    sent = stats.get('sent', 0)
    
    # 没有相关内容时不发送汇总
    if relevant == 0:
        return True
    
    try:
        # 构建统计文本
        stats_text = f"• 扫描内容: **{total}** 条\n• 相关内容: **{relevant}** 条\n• 成功推送: **{sent}** 条"
        
        # 如果有详细统计，添加分类信息
        if 'posts' in stats or 'comments' in stats or 'search' in stats:
            stats_text += f"\n\n📊 分类统计:\n"
            if stats.get('posts', 0) > 0:
                stats_text += f"• 帖子: {stats.get('relevant_posts', 0)}/{stats.get('posts', 0)}\n"
            if stats.get('comments', 0) > 0:
                stats_text += f"• 评论: {stats.get('relevant_comments', 0)}/{stats.get('comments', 0)}\n"
            if stats.get('search', 0) > 0:
                stats_text += f"• 搜索: {stats.get('relevant_search', 0)}/{stats.get('search', 0)}"
        
        message = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "📊 Reddit监测运行汇总"
                    },
                    "template": "green"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": stats_text
                        }
                    }
                ]
            }
        }
        
        response = requests.post(
            FEISHU_WEBHOOK_URL,
            headers={'Content-Type': 'application/json'},
            data=json.dumps(message),
            timeout=10
        )
        
        return response.json().get('code', -1) == 0
        
    except Exception as e:
        print(f"[错误] 发送汇总失败: {e}")
        return False


if __name__ == "__main__":
    # 测试不同类型的卡片
    test_items = [
        {
            'id': 'test1',
            'type': 'post',
            'title': 'I want to make a simple puzzle game but coding is so frustrating',
            'content': 'I have this idea for a match-3 puzzle game but every time I try to code the logic I get stuck.',
            'subreddit': 'gamedev',
            'link': 'https://reddit.com/r/gamedev/test1',
            'author': 'testuser1',
            'analysis': {
                'is_relevant': True,
                'reason': 'User frustrated with coding, looking for easier solutions',
                'reply_draft': 'I feel you! Coding game logic can be tough. I\'ve been using wefun.ai lately - it lets you build game mechanics with prompts. Might help!'
            }
        },
        {
            'id': 'test2',
            'type': 'comment',
            'title': 'Re: Best tools for indie devs?',
            'content': 'Unity is way too complex for what I want to do. I just want to make simple interactive stories.',
            'subreddit': 'IndieDev',
            'link': 'https://reddit.com/r/IndieDev/test2',
            'author': 'testuser2',
            'analysis': {
                'is_relevant': True,
                'reason': 'User finding Unity too complex, wants simpler tools',
                'reply_draft': 'Totally get that! For interactive stories, you might like wefun.ai - way simpler than Unity for that kind of thing.'
            }
        },
        {
            'id': 'test3',
            'type': 'search',
            'title': 'Looking for no-code game development tools',
            'content': 'Are there any good tools where I can make games without programming?',
            'subreddit': 'gamedesign',
            'link': 'https://reddit.com/r/gamedesign/test3',
            'author': 'testuser3',
            'search_keyword': 'no code game',
            'analysis': {
                'is_relevant': True,
                'reason': 'Direct request for no-code game tools',
                'reply_draft': 'Yes! Check out wefun.ai - you can build game logic using prompts, no coding needed. Great for prototyping ideas quickly.'
            }
        }
    ]
    
    if FEISHU_WEBHOOK_URL:
        send_batch_to_feishu(test_items)
    else:
        print("请设置 FEISHU_WEBHOOK_URL 环境变量")
        print("\n卡片预览:")
        for item in test_items:
            print(f"\n--- {item['type'].upper()} ---")
            card = create_card_message(item)
            print(json.dumps(card, ensure_ascii=False, indent=2)[:500] + "...")
