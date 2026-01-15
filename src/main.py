"""
Reddit监测工具 - 主入口
监控Reddit帖子、评论和关键词搜索，用Gemini分析相关性，推送到飞书
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.reddit_fetcher import fetch_all_new_posts
from src.gemini_analyzer import analyze_posts_batch
from src.feishu_notifier import send_batch_to_feishu, send_summary_to_feishu


def count_by_type(items: list) -> dict:
    """统计各类型内容数量"""
    counts = {'post': 0, 'comment': 0, 'search': 0}
    for item in items:
        t = item.get('type', 'post')
        counts[t] = counts.get(t, 0) + 1
    return counts


def main():
    """主函数"""
    print("=" * 60)
    print(f"Reddit监测工具启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 检查环境变量
    if not os.environ.get('GEMINI_API_KEY'):
        print("[错误] 请设置 GEMINI_API_KEY 环境变量")
        sys.exit(1)
    
    if not os.environ.get('FEISHU_WEBHOOK_URL'):
        print("[错误] 请设置 FEISHU_WEBHOOK_URL 环境变量")
        sys.exit(1)
    
    # 步骤1: 获取新内容（帖子、评论、搜索结果）
    print("\n📡 步骤1: 获取Reddit新内容...")
    new_items = fetch_all_new_posts()
    
    if not new_items:
        print("\n✅ 没有新内容需要处理，退出")
        return
    
    # 统计获取到的内容
    fetch_stats = count_by_type(new_items)
    
    # 步骤2: 用Gemini分析相关性
    print("\n🤖 步骤2: AI分析相关性...")
    relevant_items = analyze_posts_batch(new_items)
    
    if not relevant_items:
        print("\n✅ 没有相关内容，退出")
        return
    
    # 统计相关内容
    relevant_stats = count_by_type(relevant_items)
    
    # 步骤3: 发送到飞书
    print("\n📤 步骤3: 发送飞书通知...")
    sent_count = send_batch_to_feishu(relevant_items)
    
    # 发送汇总（带详细统计）
    send_summary_to_feishu({
        'total': len(new_items),
        'relevant': len(relevant_items),
        'sent': sent_count,
        'posts': fetch_stats.get('post', 0),
        'comments': fetch_stats.get('comment', 0),
        'search': fetch_stats.get('search', 0),
        'relevant_posts': relevant_stats.get('post', 0),
        'relevant_comments': relevant_stats.get('comment', 0),
        'relevant_search': relevant_stats.get('search', 0),
    })
    
    # 完成
    print("\n" + "=" * 60)
    print("✅ 运行完成!")
    print(f"   扫描内容: {len(new_items)} 条")
    print(f"     - 帖子: {fetch_stats.get('post', 0)}")
    print(f"     - 评论: {fetch_stats.get('comment', 0)}")
    print(f"     - 搜索: {fetch_stats.get('search', 0)}")
    print(f"   相关内容: {len(relevant_items)} 条")
    print(f"   成功推送: {sent_count} 条")
    print("=" * 60)


if __name__ == "__main__":
    main()
