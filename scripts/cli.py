#!/usr/bin/env python
"""
AliceLM CLI工具
"""

import argparse
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.config import get_config
from packages.db import init_db, get_db_context, Tenant, User, WatchedFolder, Video, VideoStatus
from packages.logging import setup_logging, get_logger
from services.watcher import BilibiliClient, FolderScanner
from services.processor import VideoPipeline
from services.scheduler import TaskScheduler

logger = get_logger(__name__)


def cmd_init(args):
    """初始化数据库和默认租户"""
    init_db()
    
    with get_db_context() as db:
        # 创建默认租户
        tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
        if not tenant:
            tenant = Tenant(name="Default", slug="default")
            db.add(tenant)
            db.commit()
            print(f"[OK] 创建默认租户: {tenant.name} (ID: {tenant.id})")
        else:
            print(f"[INFO] 默认租户已存在: {tenant.name} (ID: {tenant.id})")
        
        # 创建默认用户
        user = db.query(User).filter(User.email == "admin@local").first()
        if not user:
            user = User(
                email="admin@local",
                username="admin",
                tenant_id=tenant.id,
            )
            db.add(user)
            db.commit()
            print(f"[OK] 创建默认用户: {user.username}")
        else:
            print(f"[INFO] 默认用户已存在: {user.username}")
    
    print("\n[OK] 初始化完成")


def cmd_scan(args):
    """扫描收藏夹"""
    config = get_config()
    sessdata = args.cookie or config.bilibili.sessdata
    
    if not sessdata:
        print("[ERROR] 请提供SESSDATA cookie (--cookie 或环境变量 ALICE_BILI_SESSDATA)")
        return
    
    with get_db_context() as db:
        tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
        if not tenant:
            print("[ERROR] 请先运行 'cli.py init' 初始化数据库")
            return
        
        scanner = FolderScanner(tenant.id, sessdata)
        
        if args.once:
            # 扫描一次
            new_videos = scanner.scan_all_folders(db)
            print(f"\n[OK] 扫描完成，发现 {len(new_videos)} 个新视频")
            for v in new_videos[:10]:
                print(f"  • [{v.bvid}] {v.title[:40]}")
            if len(new_videos) > 10:
                print(f"  ... 还有 {len(new_videos) - 10} 个")
        else:
            print("[INFO] 持续扫描模式暂未实现，请使用 --once")


def cmd_add_folder(args):
    """添加监控收藏夹"""
    config = get_config()
    sessdata = args.cookie or config.bilibili.sessdata
    
    with get_db_context() as db:
        tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
        if not tenant:
            print("[ERROR] 请先运行 'cli.py init' 初始化数据库")
            return
        
        client = BilibiliClient(sessdata)
        
        folder_id = args.folder_id
        folder_type = args.type
        
        # 获取收藏夹名称
        if folder_type == "season":
            info, _ = client.fetch_season(folder_id)
            name = info.title
        else:
            info, _ = client.fetch_favlist(folder_id)
            name = info.title
        
        # 添加到数据库
        scanner = FolderScanner(tenant.id, sessdata)
        folder = scanner.add_folder(folder_id, folder_type, name, db)
        
        print(f"[OK] 已添加收藏夹: {folder.name} (ID: {folder.folder_id})")


def cmd_list_folders(args):
    """列出监控的收藏夹"""
    with get_db_context() as db:
        tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
        if not tenant:
            print("[ERROR] 请先运行 'cli.py init' 初始化数据库")
            return
        
        folders = db.query(WatchedFolder).filter(
            WatchedFolder.tenant_id == tenant.id
        ).all()
        
        if not folders:
            print("[INFO] 暂无监控的收藏夹")
            return
        
        print(f"\n监控的收藏夹 ({len(folders)}个):")
        print("-" * 60)
        for f in folders:
            status = "[ON]" if f.is_active else "[OFF]"
            last_scan = f.last_scan_at.strftime("%Y-%m-%d %H:%M") if f.last_scan_at else "从未"
            print(f"{status} [{f.folder_id}] {f.name:<30} ({f.folder_type}) 最后扫描: {last_scan}")


def cmd_list_videos(args):
    """列出视频"""
    with get_db_context() as db:
        tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
        if not tenant:
            print("[ERROR] 请先运行 'cli.py init' 初始化数据库")
            return
        
        query = db.query(Video).filter(Video.tenant_id == tenant.id)
        
        if args.status:
            query = query.filter(Video.status == VideoStatus(args.status))
        
        videos = query.order_by(Video.created_at.desc()).limit(args.limit).all()
        
        if not videos:
            print("[INFO] 暂无视频")
            return
        
        print(f"\n视频列表 (显示最新{args.limit}个):")
        print("-" * 80)
        for v in videos:
            status_icon = {
                VideoStatus.PENDING: "[PEND]",
                VideoStatus.DOWNLOADING: "[DOWN]",
                VideoStatus.TRANSCRIBING: "[ASR]",
                VideoStatus.ANALYZING: "[AI]",
                VideoStatus.DONE: "[DONE]",
                VideoStatus.FAILED: "[FAIL]",
            }.get(v.status, "[?]")
            print(f"{status_icon} [{v.bvid}] {v.title[:50]:<50} {v.status.value}")


def cmd_process(args):
    """处理待处理的视频"""
    config = get_config()
    sessdata = args.cookie or config.bilibili.sessdata
    
    with get_db_context() as db:
        tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
        if not tenant:
            print("[ERROR] 请先运行 'cli.py init' 初始化数据库")
            return
        
        # 检查待处理视频数量
        pending_count = db.query(Video).filter(
            Video.tenant_id == tenant.id,
            Video.status == VideoStatus.PENDING,
        ).count()
        
        if pending_count == 0:
            print("[INFO] 没有待处理的视频")
            return
        
        print(f"[INFO] 发现 {pending_count} 个待处理视频")
        
        if args.bvid:
            # 处理指定视频
            video = db.query(Video).filter(
                Video.tenant_id == tenant.id,
                Video.bvid == args.bvid,
            ).first()
            
            if not video:
                print(f"[ERROR] 视频不存在: {args.bvid}")
                return
            
            print(f"开始处理: [{video.bvid}] {video.title[:40]}")
            pipeline = VideoPipeline(sessdata=sessdata)
            
            try:
                pipeline.process(video, db)
                print(f"[OK] 处理完成")
                print(f"   转写文件: {video.transcript_path}")
            except Exception as e:
                print(f"[ERROR] 处理失败: {e}")
        else:
            # 批量处理
            limit = args.limit or 5
            print(f"开始批量处理 (最多 {limit} 个)...")
            
            pipeline = VideoPipeline(sessdata=sessdata)
            processed = pipeline.process_pending(db, tenant.id, limit=limit)
            
            print(f"\n[OK] 处理完成: {len(processed)} 个视频")
            for v in processed:
                print(f"   [{v.bvid}] {v.title[:40]}")


def cmd_bilibili(args):
    """B站API直接调用（兼容旧脚本）"""
    config = get_config()
    sessdata = args.cookie or config.bilibili.sessdata
    
    client = BilibiliClient(sessdata)
    
    if args.action == "favlist":
        folder_id = BilibiliClient.extract_media_id(args.target)
        info, videos = client.fetch_favlist(folder_id)
        print(f"\n收藏夹: {info.title} ({info.media_count}个视频)")
        print("-" * 60)
        for v in videos[:20]:
            print(f"  [{v.bvid}] {v.title[:40]}")
        if len(videos) > 20:
            print(f"  ... 还有 {len(videos) - 20} 个")
    
    elif args.action == "list":
        user_id = BilibiliClient.extract_user_id(args.target)
        folders = client.fetch_user_favlists(user_id)
        print(f"\n用户 {user_id} 的收藏夹:")
        print("-" * 60)
        for f in folders:
            print(f"  [{f.id}] {f.title:<30} ({f.media_count}个视频)")
        
        if sessdata:
            sub_folders, seasons = client.fetch_collected_favlists(user_id)
            print(f"\n订阅的收藏夹 ({len(sub_folders)}个):")
            for f in sub_folders:
                print(f"  [{f.id}] {f.title:<30} by {f.owner}")
            print(f"\n订阅的合集 ({len(seasons)}个):")
            for s in seasons:
                print(f"  [{s.id}] {s.title:<30} by {s.owner}")
    
    elif args.action == "season":
        info, videos = client.fetch_season(args.target)
        print(f"\n合集: {info.title} ({info.media_count}个视频)")
        print("-" * 60)
        for v in videos[:20]:
            print(f"  [{v.bvid}] {v.title[:40]}")
        if len(videos) > 20:
            print(f"  ... 还有 {len(videos) - 20} 个")
    
    if args.output:
        # 导出JSON
        output_data = {
            "info": info.__dict__ if hasattr(info, '__dict__') else info,
            "videos": [v.__dict__ for v in videos] if 'videos' in dir() else [],
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n已导出到: {args.output}")


def cmd_worker(args):
    """启动后台Worker"""
    import signal
    
    config = get_config()
    sessdata = args.cookie or config.bilibili.sessdata
    
    print("启动 AliceLM Worker")
    print(f"   扫描间隔: {args.scan_interval}分钟")
    print(f"   处理间隔: {args.process_interval}分钟")
    print(f"   每次处理: {args.batch_size}个视频")
    print("-" * 50)
    
    scheduler = TaskScheduler(blocking=True)
    
    # 添加任务
    scheduler.add_scan_job(
        interval_minutes=args.scan_interval,
        sessdata=sessdata,
    )
    scheduler.add_process_job(
        interval_minutes=args.process_interval,
        limit=args.batch_size,
        sessdata=sessdata,
    )
    scheduler.add_retry_job(cron_hour=3)
    
    # 显示任务列表
    print("\n已注册任务:")
    for job in scheduler.list_jobs():
        print(f"   [{job['id']}] {job['name']}")
        print(f"      下次执行: {job['next_run']}")
    
    # 信号处理
    def shutdown(signum, frame):
        print("\n正在停止...")
        scheduler.shutdown(wait=True)
        print("Worker已停止")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    print("\nWorker运行中... (Ctrl+C停止)")
    
    # 立即执行一次扫描
    if args.run_now:
        print("\n立即执行扫描...")
        from services.scheduler import job_scan_folders
        job_scan_folders(sessdata=sessdata)
    
    scheduler.start()


def cmd_models(args):
    """获取LLM模型列表"""
    from services.ai.llm import OpenAIProvider
    
    config = get_config()
    
    # 使用参数或配置
    base_url = args.base_url or config.llm.base_url or "https://api.openai.com/v1"
    api_key = args.api_key or config.llm.api_key
    
    if not api_key and "localhost" not in base_url:
        print("[ERROR] 需要API Key，请设置 --api-key 或环境变量 ALICE_LLM__API_KEY")
        return
    
    print(f"[INFO] 获取模型列表: {base_url}")
    
    provider = OpenAIProvider(
        base_url=base_url,
        api_key=api_key or "ollama",
    )
    
    models = provider.list_models()
    
    if not models:
        print("[ERROR] 未获取到模型列表")
        return
    
    print(f"\n可用模型 ({len(models)} 个):\n")
    for m in models:
        print(f"   • {m}")
    
    # 保存到文件
    if args.save:
        output = args.output or "data/models.json"
        provider.save_models(output)
        print(f"\n[OK] 已保存到: {output}")


def main():
    parser = argparse.ArgumentParser(description="AliceLM CLI工具")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # init
    init_parser = subparsers.add_parser("init", help="初始化数据库")
    init_parser.set_defaults(func=cmd_init)

    # scan
    scan_parser = subparsers.add_parser("scan", help="扫描收藏夹")
    scan_parser.add_argument("--cookie", help="SESSDATA cookie")
    scan_parser.add_argument("--once", action="store_true", help="只扫描一次")
    scan_parser.set_defaults(func=cmd_scan)

    # add-folder
    add_parser = subparsers.add_parser("add-folder", help="添加监控收藏夹")
    add_parser.add_argument("folder_id", help="收藏夹ID")
    add_parser.add_argument("--type", default="favlist", choices=["favlist", "season"], help="类型")
    add_parser.add_argument("--cookie", help="SESSDATA cookie")
    add_parser.set_defaults(func=cmd_add_folder)

    # list-folders
    list_folders_parser = subparsers.add_parser("list-folders", help="列出监控的收藏夹")
    list_folders_parser.set_defaults(func=cmd_list_folders)

    # list-videos
    list_videos_parser = subparsers.add_parser("list-videos", help="列出视频")
    list_videos_parser.add_argument("--status", help="状态过滤")
    list_videos_parser.add_argument("--limit", type=int, default=20, help="数量限制")
    list_videos_parser.set_defaults(func=cmd_list_videos)

    # process
    process_parser = subparsers.add_parser("process", help="处理视频（下载→转写）")
    process_parser.add_argument("--bvid", help="指定处理的视频BV号")
    process_parser.add_argument("--limit", type=int, default=5, help="批量处理数量")
    process_parser.add_argument("--cookie", help="SESSDATA cookie")
    process_parser.set_defaults(func=cmd_process)

    # bilibili (兼容旧命令)
    bili_parser = subparsers.add_parser("bilibili", help="B站API直接调用")
    bili_parser.add_argument("action", choices=["favlist", "list", "season"], help="操作")
    bili_parser.add_argument("target", help="目标ID或URL")
    bili_parser.add_argument("--cookie", help="SESSDATA cookie")
    bili_parser.add_argument("--output", "-o", help="输出JSON文件")
    bili_parser.set_defaults(func=cmd_bilibili)

    # worker
    worker_parser = subparsers.add_parser("worker", help="启动后台Worker")
    worker_parser.add_argument("--scan-interval", type=int, default=5, help="扫描间隔(分钟)")
    worker_parser.add_argument("--process-interval", type=int, default=10, help="处理间隔(分钟)")
    worker_parser.add_argument("--batch-size", type=int, default=3, help="每次处理数量")
    worker_parser.add_argument("--cookie", help="SESSDATA cookie")
    worker_parser.add_argument("--run-now", action="store_true", help="立即执行一次扫描")
    worker_parser.set_defaults(func=cmd_worker)

    # models
    models_parser = subparsers.add_parser("models", help="获取LLM可用模型列表")
    models_parser.add_argument("--base-url", help="API端点URL")
    models_parser.add_argument("--api-key", help="API密钥")
    models_parser.add_argument("--save", action="store_true", help="保存到文件")
    models_parser.add_argument("--output", "-o", help="输出文件路径")
    models_parser.set_defaults(func=cmd_models)

    args = parser.parse_args()
    
    # 设置日志
    setup_logging(debug=args.debug)

    if args.command is None:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
