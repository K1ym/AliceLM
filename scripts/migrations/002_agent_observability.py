"""
迁移脚本：Agent 可观测性字段扩展
M1 milestone - AgentRun/AgentStep 新增观测字段

使用方法：
    python scripts/migrations/002_agent_observability.py
    python scripts/migrations/002_agent_observability.py --execute  # 实际执行

注意：
    - 执行前请备份数据库
    - 此脚本为增量变更，向后兼容
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

    # 1. AgentRun 表新增字段
    cursor.execute("PRAGMA table_info(agent_runs)")
    agent_run_columns = {row[1] for row in cursor.fetchall()}

    new_agent_run_columns = [
        ("plan_json", "TEXT"),
        ("safety_level", "VARCHAR(20) DEFAULT 'normal'"),
        ("total_duration_ms", "INTEGER"),
        ("error_code", "VARCHAR(50)"),
    ]

    for col_name, col_type in new_agent_run_columns:
        if col_name in agent_run_columns:
            print(f"✓ agent_runs.{col_name} 已存在，跳过")
        else:
            sqls.append(f"ALTER TABLE agent_runs ADD COLUMN {col_name} {col_type}")

    # 2. AgentStep 表新增字段
    cursor.execute("PRAGMA table_info(agent_steps)")
    agent_step_columns = {row[1] for row in cursor.fetchall()}

    new_agent_step_columns = [
        ("kind", "VARCHAR(20) DEFAULT 'tool'"),
        ("requires_user_confirm", "BOOLEAN DEFAULT 0"),
        ("tool_trace_json", "TEXT"),
        ("duration_ms", "INTEGER"),
    ]

    for col_name, col_type in new_agent_step_columns:
        if col_name in agent_step_columns:
            print(f"✓ agent_steps.{col_name} 已存在，跳过")
        else:
            sqls.append(f"ALTER TABLE agent_steps ADD COLUMN {col_name} {col_type}")

    # 3. 创建索引（可选，提升查询性能）
    cursor.execute("PRAGMA index_list(agent_runs)")
    indexes = {row[1] for row in cursor.fetchall()}

    if "ix_agent_runs_error_code" not in indexes:
        sqls.append("CREATE INDEX IF NOT EXISTS ix_agent_runs_error_code ON agent_runs(error_code)")

    if "ix_agent_runs_safety_level" not in indexes:
        sqls.append("CREATE INDEX IF NOT EXISTS ix_agent_runs_safety_level ON agent_runs(safety_level)")

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

    # 检查 agent_runs 表结构
    cursor.execute("PRAGMA table_info(agent_runs)")
    agent_run_columns = {row[1] for row in cursor.fetchall()}

    # 检查 agent_steps 表结构
    cursor.execute("PRAGMA table_info(agent_steps)")
    agent_step_columns = {row[1] for row in cursor.fetchall()}

    checks = [
        ("agent_runs.plan_json", "plan_json" in agent_run_columns),
        ("agent_runs.safety_level", "safety_level" in agent_run_columns),
        ("agent_runs.total_duration_ms", "total_duration_ms" in agent_run_columns),
        ("agent_runs.error_code", "error_code" in agent_run_columns),
        ("agent_steps.kind", "kind" in agent_step_columns),
        ("agent_steps.requires_user_confirm", "requires_user_confirm" in agent_step_columns),
        ("agent_steps.tool_trace_json", "tool_trace_json" in agent_step_columns),
        ("agent_steps.duration_ms", "duration_ms" in agent_step_columns),
    ]

    for name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"  {status} {name}")

    conn.close()

    return all(passed for _, passed in checks)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agent 可观测性迁移脚本")
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
