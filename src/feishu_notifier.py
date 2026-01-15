"""
飞书通知模块
发送交互式卡片到飞书群
"""

import os
import json
import requests
from typing import Dict, List

# 从环境变量获取Webhook URL
FEISHU_WEBHOOK_URL = os.environ.get('FEISHU_WEBHOOK_URL', '')


def create_card_message(post: Dict) -> Dict:
    """
    创建飞书卡片消息
    
    Args:
        post: 帖子信息，包含title, content, link, subreddit, analysis等
    
    Returns:
        飞书卡片消息体
    """
    analysis = post.get('analysis', {})
    reason = analysis.get('reason', '未知')
    reply_draft = analysis.get('reply_draft', '')
    
    # 截断内容预览
    content_preview = post.get('content', '')[:300]
    if len(post.get('content', '')) > 300:
        content_preview += '...'
    
    # 构建飞书卡片
    card = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🎯 Reddit潜在客户 - r/{post.get('subreddit', '')}"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**📌 帖子标题**\n{post.get('title', '')}"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**📝 内容预览**\n{content_preview}"
                    }
                },
                {
                    "tag": "hr"
                },
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
                        "content": f"**💬 参考回复**\n```\n{reply_draft}\n```"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**作者**: u/{post.get('author', 'unknown')}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**社区**: r/{post.get('subreddit', '')}"
                            }
                        }
                    ]
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "🔗 查看原帖并回复"
                            },
                            "type": "primary",
                            "url": post.get('link', '')
                        }
                    ]
                }
            ]
        }
    }
    
    return card


def send_to_feishu(post: Dict) -> bool:
    """
    发送单个帖子通知到飞书
    
    Args:
        post: 帖子信息
    
    Returns:
        是否发送成功
    """
    if not FEISHU_WEBHOOK_URL:
        print("[错误] FEISHU_WEBHOOK_URL 环境变量未设置")
        return False
    
    try:
        card_message = create_card_message(post)
        
        response = requests.post(
            FEISHU_WEBHOOK_URL,
            headers={'Content-Type': 'application/json'},
            data=json.dumps(card_message),
            timeout=10
        )
        
        result = response.json()
        
        if result.get('code') == 0 or result.get('StatusCode') == 0:
            print(f"[成功] 已发送: {post.get('title', '')[:50]}...")
            return True
        else:
            print(f"[失败] 飞书返回错误: {result}")
            return False
            
    except Exception as e:
        print(f"[错误] 发送飞书消息失败: {e}")
        return False


def send_batch_to_feishu(posts: List[Dict]) -> int:
    """
    批量发送帖子通知到飞书
    
    Args:
        posts: 帖子列表
    
    Returns:
        成功发送的数量
    """
    success_count = 0
    
    for post in posts:
        if send_to_feishu(post):
            success_count += 1
    
    print(f"\n[汇总] 共 {len(posts)} 条消息，成功发送 {success_count} 条")
    return success_count


def send_summary_to_feishu(total: int, relevant: int, sent: int) -> bool:
    """
    发送运行汇总到飞书（可选）
    
    Args:
        total: 总帖子数
        relevant: 相关帖子数
        sent: 成功发送数
    """
    if not FEISHU_WEBHOOK_URL:
        return False
    
    # 只在有相关帖子时发送汇总
    if relevant == 0:
        return True
    
    try:
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
                            "content": f"• 扫描帖子数: **{total}**\n• 相关帖子数: **{relevant}**\n• 成功推送数: **{sent}**"
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
    # 测试运行
    test_post = {
        'id': 'test123',
        'title': 'I want to make a simple puzzle game but coding is so frustrating',
        'content': 'I have this idea for a match-3 puzzle game but every time I try to code the logic I get stuck. Is there an easier way to prototype game mechanics without writing tons of code? I\'ve tried Unity but the learning curve is steep.',
        'subreddit': 'gamedev',
        'link': 'https://reddit.com/r/gamedev/test123',
        'author': 'testuser',
        'analysis': {
            'is_relevant': True,
            'reason': 'User is frustrated with coding and looking for easier ways to prototype games',
            'reply_draft': 'I totally feel you on the coding frustration! I\'ve been prototyping with wefun.ai recently, it handles game logic via prompts without traditional coding. Might be worth checking out for quick prototypes.'
        }
    }
    
    if FEISHU_WEBHOOK_URL:
        send_to_feishu(test_post)
    else:
        print("请设置 FEISHU_WEBHOOK_URL 环境变量")
        print("\n卡片预览:")
        print(json.dumps(create_card_message(test_post), ensure_ascii=False, indent=2))
