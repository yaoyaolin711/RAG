"""
微信消息分流 + RAG Agent 模拟测试

用法:
  python scripts/wechat_simulate.py --tag B --message "锦丞 Pro 无线耳机多少钱？"
  python scripts/wechat_simulate.py --tag C --message "今天天气不错"
  python scripts/wechat_simulate.py --tag B --message "想跟你们谈合作，佣金怎么算？"
  python scripts/wechat_simulate.py --tag A --message "之前说的合作方案呢？"
"""
import argparse
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.wechat_handler import WeChatMessageHandler
from vectorstore import check_chroma_connection

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main():
    parser = argparse.ArgumentParser(description="微信分流 + RAG Agent 模拟")
    parser.add_argument("--user-id", default="wx_test_user_001", help="微信用户 ID")
    parser.add_argument("--tag", choices=["A", "B", "C"], default="B", help="用户标签")
    parser.add_argument("--message", required=True, help="用户消息")
    args = parser.parse_args()

    check_chroma_connection()
    handler = WeChatMessageHandler()
    response = handler.handle_message(args.user_id, args.tag, args.message)

    print("\n=== 处理结果 ===")
    print(f"用户: {response.user_id}")
    print(f"标签: {response.user_tag.value}")
    print(f"分流: {response.route.value}")
    print(f"回复模式: {response.reply_mode.value}")
    if response.tag_upgrade:
        u = response.tag_upgrade
        print(f"标签升级: {u.from_tag.value} → {u.to_tag.value}")
        print(f"  触发词: {u.trigger_keywords}")
        print(f"  已写库: {u.applied}")
    if response.sources:
        print(f"检索命中: {len(response.sources)} 条")
        for s in response.sources:
            print(f"  - [{s.score:.2f}] {s.source}: {s.content[:60]}...")
    else:
        print("检索命中: 0 条（闲聊模式）")
    print(f"\n回复:\n{response.answer}")


if __name__ == "__main__":
    main()
