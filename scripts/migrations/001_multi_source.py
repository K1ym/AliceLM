"""
迁移脚本：多内容源支持
bvid → source_id，新增 UserPlatformBinding 表

使用方法：
    python scripts/migrations/001_multi_source.py

注意：
    - 执行前请备份数据库
    - 此脚本为破坏性变更，不可逆
"""

import sqlite3
import sys
from pathlib import Path

# 添加项目根目录到 path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def migrate(db_path: str, dry_run: bool = True):
    """
    执行迁移

    Args:
        db_path: 数据库文件路径
        dry_run: 如果为 True，只打印 SQL 不执行
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"数据库: {db_path}")
    print(f"模式: {'DRY RUN（不执行）' if dry_run else '实际执行'}")
    print("-" * 50)

    sqls = []

    # 1. 检查 videos 表是否已有 source_id 字段
    cursor.execute("PRAGMA table_info(videos)")
    columns = {row[1] for row in cursor.fetchall()}

    if "source_id" in columns:
        print("✓ videos.source_id 已存在，跳过")
    else:
        # 添加 source_id 字段
        sqls.append("ALTER TABLE videos ADD COLUMN source_id VARCHAR(100)")

        # 迁移数据：source_id = bvid
        sqls.append("UPDATE videos SET source_id = bvid WHERE source_id IS NULL")

        # 创建索引
        sqls.append("CREATE INDEX IF NOT EXISTS ix_videos_source_id ON videos(source_id)")
        sqls.append("CREATE INDEX IF NOT EXISTS ix_tenant_source_type ON videos(tenant_id, source_type)")

    # 2. 检查 source_type 索引
    cursor.execute("PRAGMA index_list(videos)")
    indexes = {row[1] for row in cursor.fetchall()}

    if "ix_videos_source_type" not in indexes and "ix_tenant_source_type" not in indexes:
        sqls.append("CREATE INDEX IF NOT EXISTS ix_videos_source_type ON videos(source_type)")

    # 3. 创建 user_platform_bindings 表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_platform_bindings'")
    if cursor.fetchone():
        print("✓ user_platform_bindings 表已存在，跳过")
    else:
        sqls.append("""
            CREATE TABLE user_platform_bindings (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                platform VARCHAR(20) NOT NULL,
                platform_uid VARCHAR(100) NOT NULL,
                credentials TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE (user_id, platform)
            )
        """)
        sqls.append("CREATE INDEX IF NOT EXISTS ix_user_platform_bindings_user_id ON user_platform_bindings(user_id)")

    # 4. 迁移 users 表的 bilibili 凭证到 user_platform_bindings
    cursor.execute("PRAGMA table_info(users)")
    user_columns = {row[1] for row in cursor.fetchall()}

    if "bilibili_uid" in user_columns:
        sqls.append("""
            INSERT OR IGNORE INTO user_platform_bindings (user_id, platform, platform_uid, credentials)
            SELECT id, 'bilibili', bilibili_uid, json_object('sessdata', bilibili_sessdata)
            FROM users WHERE bilibili_uid IS NOT NULL AND bilibili_uid != ''
        """)
        # SQLite 不支持 DROP COLUMN（3.35.0 之前），需要重建表
        # 这里先不删除旧字段，标记为 deprecated
        print("⚠ users.bilibili_uid/bilibili_sessdata 保留（SQLite 不便删除列），代码层面已不再使用")

    # 5. 处理唯一约束（SQLite 需要重建表）
    # 检查是否需要更新约束
    cursor.execute("PRAGMA index_info(uq_tenant_video)")
    old_constraint = cursor.fetchall()

    if old_constraint:
        print("⚠ 旧约束 uq_tenant_video 存在，需要重建表来更新约束")
        print("  建议：在应用层确保 (tenant_id, source_type, source_id) 唯一性")
        print("  或使用 PostgreSQL 等支持 ALTER CONSTRAINT 的数据库")

    # 执行 SQL
    print("\n待执行的 SQL:")
    for sql in sqls:
        print(f"  {sql.strip()[:80]}...")

    if not dry_run and sqls:
        print("\n执行中...")
        for sql in sqls:
            try:
                cursor.execute(sql)
                print(f"  ✓ {sql.strip()[:50]}...")
            except Exception as e:
                print(f"  ✗ {sql.strip()[:50]}... 错误: {e}")

        conn.commit()
        print("\n✓ 迁移完成")
    elif not sqls:
        print("\n✓ 无需迁移")
    else:
        print("\n（DRY RUN 模式，未执行任何变更）")

    conn.close()


def verify(db_path: str):
    """验证迁移结果"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n验证迁移结果:")
    print("-" * 50)

    # 检查 videos 表结构
    cursor.execute("PRAGMA table_info(videos)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}

    checks = [
        ("videos.source_type", "source_type" in columns),
        ("videos.source_id", "source_id" in columns),
    ]

    # 检查 user_platform_bindings 表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_platform_bindings'")
    checks.append(("user_platform_bindings 表", cursor.fetchone() is not None))

    # 检查数据迁移
    cursor.execute("SELECT COUNT(*) FROM videos WHERE source_id IS NULL OR source_id = ''")
    null_count = cursor.fetchone()[0]
    checks.append(("videos.source_id 无空值", null_count == 0))

    for name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"  {status} {name}")

    conn.close()

    return all(passed for _, passed in checks)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="多内容源迁移脚本")
    parser.add_argument("--db", default="data/bili_learner.db", help="数据库路径")
    parser.add_argument("--execute", action="store_true", help="实际执行（默认 dry-run）")
    parser.add_argument("--verify", action="store_true", help="仅验证迁移结果")

    args = parser.parse_args()

    db_path = Path(project_root) / args.db

    if not db_path.exists():
        print(f"错误: 数据库不存在: {db_path}")
        sys.exit(1)

    if args.verify:
        success = verify(str(db_path))
        sys.exit(0 if success else 1)
    else:
        migrate(str(db_path), dry_run=not args.execute)
        if args.execute:
            verify(str(db_path))
