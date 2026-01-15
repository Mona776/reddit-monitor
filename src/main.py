"""
Reddit监测工具 - 主入口
监控Reddit帖子，用Gemini分析相关性，推送到飞书
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.reddit_fetcher import fetch_all_new_posts
from src.gemini_analyzer import analyze_posts_batch
from src.feishu_notifier import send_batch_to_feishu, send_summary_to_feishu


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
    
    # 步骤1: 获取新帖子
    print("\n📡 步骤1: 获取Reddit新帖子...")
    print("-" * 40)
    new_posts = fetch_all_new_posts()
    
    if not new_posts:
        print("\n✅ 没有新帖子需要处理，退出")
        return
    
    # 步骤2: 用Gemini分析相关性
    print("\n🤖 步骤2: 分析帖子相关性...")
    print("-" * 40)
    relevant_posts = analyze_posts_batch(new_posts)
    
    if not relevant_posts:
        print("\n✅ 没有相关帖子，退出")
        return
    
    # 步骤3: 发送到飞书
    print("\n📤 步骤3: 发送飞书通知...")
    print("-" * 40)
    sent_count = send_batch_to_feishu(relevant_posts)
    
    # 发送汇总
    send_summary_to_feishu(
        total=len(new_posts),
        relevant=len(relevant_posts),
        sent=sent_count
    )
    
    # 完成
    print("\n" + "=" * 60)
    print("✅ 运行完成!")
    print(f"   扫描帖子: {len(new_posts)}")
    print(f"   相关帖子: {len(relevant_posts)}")
    print(f"   成功推送: {sent_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
