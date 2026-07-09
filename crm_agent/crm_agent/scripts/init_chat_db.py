"""初始化本地微信历史对话 SQLite 库并写入示例数据。

用法（在 crm_agent/crm_agent 目录下）:
    python scripts/init_chat_db.py
    python scripts/init_chat_db.py --reset
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.chat_history import (  # noqa: E402
    EXPORT_DB_PATH,
    _insert_message,
    ensure_db,
)

# 与 API.md 示例一致
DEMO_SELF = "wx_demo_user_001"
DEMO_CONTACT = "wx_contact_001"

SEED_TURNS: list[tuple[str, str]] = [
    ("你好，想了解一下合作", "可以的，我们这边主要是室内运动用品，指压板弹力带这类"),
    ("佣金能给到多少？", "定向佣金大概 30-40%，具体看类目，我帮你查一下"),
    ("能否寄样？", "可以寄样的，你留个地址和尺码，我让同事安排"),
]


def _reset_db(path: Path) -> None:
    if path.is_file():
        path.unlink()


def seed_demo_data() -> int:
    ensure_db()
    conn = sqlite3.connect(str(EXPORT_DB_PATH))
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE username = ?",
            (DEMO_CONTACT,),
        ).fetchone()[0]
        if count:
            return int(count)

        for i, (incoming, outgoing) in enumerate(SEED_TURNS):
            day = f"2026-07-0{6 - i}"
            _insert_message(
                conn,
                contact_username=DEMO_CONTACT,
                sender_username=DEMO_CONTACT,
                content=incoming,
                dt=f"{day} 10:{10 + i * 2:02d}:00",
            )
            _insert_message(
                conn,
                contact_username=DEMO_CONTACT,
                sender_username=DEMO_SELF,
                content=outgoing,
                dt=f"{day} 10:{11 + i * 2:02d}:00",
            )
        conn.commit()
        return len(SEED_TURNS) * 2
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化 exported_chats.db")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="删除已有库后重新创建",
    )
    args = parser.parse_args()

    if args.reset:
        _reset_db(EXPORT_DB_PATH)

    ensure_db()
    inserted = seed_demo_data()
    print(f"数据库路径: {EXPORT_DB_PATH}")
    print(f"示例联系人: {DEMO_CONTACT}（我方 ID: {DEMO_SELF}）")
    print(f"示例消息条数: {inserted}")


if __name__ == "__main__":
    main()
