"""
Reddit监测工具 - 主入口
监控Reddit帖子、评论和关键词搜索，用Gemini分析相关性，推送到飞书

优化版：增量处理模式
- 预过滤减少AI调用
- 每批成功后立即保存和发送
- 即使后续批次失败，前面的结果不会丢失
"""

import os
import sys
import time
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.reddit_fetcher import fetch_all_new_posts, load_processed_posts, save_processed_posts
from src.gemini_analyzer import analyze_batch, BATCH_SIZE, REQUEST_DELAY
from src.prefilter import pre_filter, prioritize_by_relevance
from src.feishu_notifier import send_batch_to_feishu, send_summary_to_feishu


def count_by_type(items: list) -> dict:
    """统计各类型内容数量"""
    counts = {'post': 0, 'comment': 0, 'search': 0}
    for item in items:
        t = item.get('type', 'post')
        counts[t] = counts.get(t, 0) + 1
    return counts


def chunk_list(items: list, chunk_size: int) -> list:
    """将列表分成固定大小的块"""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def main():
    """主函数 - 增量处理模式"""
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
    print(f"\n[获取完成] 共 {len(new_items)} 条新内容")
    
    # 步骤2: 预过滤
    print("\n🔍 步骤2: 预过滤...")
    filtered_items = pre_filter(new_items)
    
    if not filtered_items:
        print("\n✅ 预过滤后无内容需要分析，退出")
        return
    
    # 按相关性排序，让更可能相关的内容先被处理
    filtered_items = prioritize_by_relevance(filtered_items)
    
    # 步骤3: 增量式AI分析
    print("\n🤖 步骤3: AI分析相关性（增量模式）...")
    
    # 加载已处理记录
    processed_ids = load_processed_posts()
    
    # 分批处理
    batches = chunk_list(filtered_items, BATCH_SIZE)
    total_batches = len(batches)
    
    print(f"  共 {len(filtered_items)} 条待分析，分 {total_batches} 批处理")
    print(f"  批次大小: {BATCH_SIZE}，批次间隔: {REQUEST_DELAY}秒")
    print("-" * 50)
    
    # 统计
    total_relevant = 0
    total_sent = 0
    relevant_stats = {'post': 0, 'comment': 0, 'search': 0}
    
    for batch_idx, batch_items in enumerate(batches):
        batch_num = batch_idx + 1
        
        # 分析当前批次
        results = analyze_batch(batch_items, batch_num)
        
        # 处理分析结果
        relevant_in_batch = []
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
                relevant_in_batch.append(item)
                
                # 更新统计
                content_type = item.get('type', 'post')
                relevant_stats[content_type] = relevant_stats.get(content_type, 0) + 1
        
        # 立即发送飞书通知（如果有相关内容）
        if relevant_in_batch:
            sent = send_batch_to_feishu(relevant_in_batch)
            total_sent += sent
            total_relevant += len(relevant_in_batch)
            print(f"  批次 {batch_num}: 发现 {len(relevant_in_batch)} 条相关，已发送飞书")
        
        # 无论成功失败，都标记这批内容为已处理
        for item in batch_items:
            item_id = item.get('id', item.get('link', ''))
            if item_id:
                processed_ids.add(item_id)
        
        # 立即保存已处理记录（增量保存的关键）
        save_processed_posts(processed_ids)
        
        # 如果不是最后一批，等待后再处理下一批
        if batch_num < total_batches:
            print(f"  等待 {REQUEST_DELAY} 秒后处理下一批...")
            time.sleep(REQUEST_DELAY)
    
    print("-" * 50)
    
    # 发送汇总通知
    if total_relevant > 0:
        print("\n📤 发送汇总通知...")
        send_summary_to_feishu({
            'total': len(new_items),
            'filtered': len(filtered_items),
            'relevant': total_relevant,
            'sent': total_sent,
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
    print(f"   预过滤后: {len(filtered_items)} 条")
    print(f"   相关内容: {total_relevant} 条")
    print(f"   成功推送: {total_sent} 条")
    print("=" * 60)


if __name__ == "__main__":
    main()
