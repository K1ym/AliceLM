"""
B站收藏夹/追番扫描脚本
用法: 
  扫描收藏夹: python scan_favlist.py favlist <收藏夹URL或ID> [--cookie SESSDATA]
  扫描追番:   python scan_favlist.py bangumi <用户ID> --cookie SESSDATA
"""

import argparse
import json
import os
import re
import requests
from typing import Optional

API_FAVLIST = "https://api.bilibili.com/x/v3/fav/resource/list"
API_FAVLIST_ALL = "https://api.bilibili.com/x/v3/fav/folder/created/list-all"
API_FAVLIST_COLLECTED = "https://api.bilibili.com/x/v3/fav/folder/collected/list"
API_BANGUMI = "https://api.bilibili.com/x/space/bangumi/follow/list"
API_SEASON = "https://api.bilibili.com/x/polymer/web-space/seasons_archives_list"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def extract_media_id(url_or_id: str) -> str:
    """从URL或直接ID中提取media_id"""
    # 尝试从URL提取
    match = re.search(r'fid=(\d+)', url_or_id)
    if match:
        return match.group(1)
    # 直接返回数字ID
    if url_or_id.isdigit():
        return url_or_id
    raise ValueError(f"无法解析收藏夹ID: {url_or_id}")


def extract_user_id(url_or_id: str) -> str:
    """从URL或直接ID中提取用户ID"""
    match = re.search(r'space\.bilibili\.com/(\d+)', url_or_id)
    if match:
        return match.group(1)
    if url_or_id.isdigit():
        return url_or_id
    raise ValueError(f"无法解析用户ID: {url_or_id}")


def get_sessdata() -> Optional[str]:
    """从环境变量获取SESSDATA"""
    return os.environ.get("ALICE_BILI_SESSDATA")


def fetch_favlist(media_id: str, sessdata: Optional[str] = None) -> dict:
    """获取收藏夹信息和视频列表"""
    cookies = {"SESSDATA": sessdata} if sessdata else {}
    all_medias = []
    page = 1
    page_size = 20
    
    # 首次请求获取基本信息
    params = {"media_id": media_id, "pn": page, "ps": page_size}
    resp = requests.get(API_FAVLIST, params=params, headers=HEADERS, cookies=cookies)
    data = resp.json()
    
    if data["code"] != 0:
        raise Exception(f"API错误: {data['message']}")
    
    info = data["data"]["info"]
    total_count = info["media_count"]
    
    # 分页获取所有视频
    while True:
        params = {"media_id": media_id, "pn": page, "ps": page_size}
        resp = requests.get(API_FAVLIST, params=params, headers=HEADERS, cookies=cookies)
        data = resp.json()
        
        medias = data["data"]["medias"]
        if not medias:
            break
        all_medias.extend(medias)
        
        if not data["data"]["has_more"]:
            break
        page += 1
    
    return {
        "info": {
            "id": info["id"],
            "title": info["title"],
            "owner": info["upper"]["name"],
            "owner_mid": info["upper"]["mid"],
            "count": total_count,
        },
        "videos": [
            {
                "bvid": m["bvid"],
                "title": m["title"],
                "duration": m["duration"],
                "upper": m["upper"]["name"],
                "play_count": m["cnt_info"]["play"],
            }
            for m in all_medias
        ]
    }


def fetch_user_favlists(user_id: str, sessdata: Optional[str] = None) -> dict:
    """获取用户创建的所有收藏夹列表"""
    cookies = {"SESSDATA": sessdata} if sessdata else {}
    params = {"up_mid": user_id}
    resp = requests.get(API_FAVLIST_ALL, params=params, headers=HEADERS, cookies=cookies)
    data = resp.json()
    
    if data["code"] != 0:
        raise Exception(f"API错误: {data['message']}")
    
    folders = data["data"].get("list", []) or []
    return {
        "info": {
            "user_id": user_id,
            "count": len(folders),
        },
        "folders": [
            {
                "id": f["id"],
                "title": f["title"],
                "media_count": f["media_count"],
            }
            for f in folders
        ]
    }


def fetch_collected_favlists(user_id: str, sessdata: Optional[str] = None) -> dict:
    """获取用户订阅的收藏夹和合集"""
    cookies = {"SESSDATA": sessdata} if sessdata else {}
    all_items = []
    page = 1
    
    while True:
        params = {"up_mid": user_id, "pn": page, "ps": 20, "platform": "web"}
        resp = requests.get(API_FAVLIST_COLLECTED, params=params, headers=HEADERS, cookies=cookies)
        data = resp.json()
        
        if data["code"] != 0:
            raise Exception(f"API错误: {data['message']}")
        
        items = data["data"].get("list", []) or []
        if not items:
            break
        all_items.extend(items)
        
        if not data["data"].get("has_more", False):
            break
        page += 1
    
    # 分离收藏夹(type=11)和合集(type=21)
    folders = [f for f in all_items if f.get("type") == 11]
    seasons = [f for f in all_items if f.get("type") == 21]
    
    return {
        "info": {
            "user_id": user_id,
            "folder_count": len(folders),
            "season_count": len(seasons),
        },
        "folders": [
            {
                "id": f["id"],
                "title": f["title"],
                "media_count": f["media_count"],
                "upper": f["upper"]["name"],
                "type": "收藏夹",
            }
            for f in folders
        ],
        "seasons": [
            {
                "id": s["id"],
                "title": s["title"],
                "media_count": s["media_count"],
                "upper": s["upper"]["name"],
                "intro": s.get("intro", ""),
                "link": s.get("link", ""),
                "type": "合集",
            }
            for s in seasons
        ]
    }


def fetch_season(season_id: str, mid: str = "", sessdata: Optional[str] = None) -> dict:
    """获取合集内的视频列表"""
    cookies = {"SESSDATA": sessdata} if sessdata else {}
    headers = {**HEADERS, "Referer": "https://space.bilibili.com"}
    all_videos = []
    page = 1
    page_size = 100
    
    while True:
        params = {"season_id": season_id, "page_num": page, "page_size": page_size}
        if mid:
            params["mid"] = mid
        resp = requests.get(API_SEASON, params=params, headers=headers, cookies=cookies)
        data = resp.json()
        
        if data["code"] != 0:
            raise Exception(f"API错误: {data['message']}")
        
        archives = data["data"].get("archives", []) or []
        if not archives:
            break
        all_videos.extend(archives)
        
        # 检查是否还有更多
        total = len(data["data"].get("aids", []))
        if len(all_videos) >= total:
            break
        page += 1
    
    return {
        "info": {
            "season_id": season_id,
            "count": len(all_videos),
        },
        "videos": [
            {
                "bvid": v["bvid"],
                "aid": v["aid"],
                "title": v["title"],
                "duration": v["duration"],
                "view": v["stat"]["view"],
            }
            for v in all_videos
        ]
    }


def fetch_all_bvids(user_id: str, sessdata: Optional[str] = None) -> dict:
    """获取用户所有收藏夹的BV号，按收藏夹分类"""
    folders = fetch_user_favlists(user_id, sessdata)
    result = {
        "user_id": user_id,
        "folders": []
    }
    
    for folder in folders["folders"]:
        if folder["media_count"] == 0:
            continue
        print(f"  扫描收藏夹: {folder['title']} ({folder['media_count']}个视频)")
        try:
            fav_data = fetch_favlist(str(folder["id"]), sessdata)
            result["folders"].append({
                "id": folder["id"],
                "title": folder["title"],
                "bvids": [v["bvid"] for v in fav_data["videos"]]
            })
        except Exception as e:
            print(f"    跳过 {folder['title']}: {e}")
    
    return result


def fetch_bangumi(user_id: str, bangumi_type: int = 1, sessdata: Optional[str] = None) -> dict:
    """
    获取用户追番/追剧列表
    type: 1=追番, 2=追剧
    """
    cookies = {"SESSDATA": sessdata} if sessdata else {}
    all_bangumis = []
    page = 1
    page_size = 20
    
    while True:
        params = {"vmid": user_id, "type": bangumi_type, "pn": page, "ps": page_size}
        resp = requests.get(API_BANGUMI, params=params, headers=HEADERS, cookies=cookies)
        data = resp.json()
        
        if data["code"] != 0:
            raise Exception(f"API错误: {data['message']}")
        
        items = data["data"].get("list", [])
        if not items:
            break
        all_bangumis.extend(items)
        
        total = data["data"]["total"]
        if page * page_size >= total:
            break
        page += 1
    
    type_name = "追番" if bangumi_type == 1 else "追剧"
    return {
        "info": {
            "user_id": user_id,
            "type": type_name,
            "count": len(all_bangumis),
        },
        "bangumis": [
            {
                "season_id": b["season_id"],
                "title": b["title"],
                "evaluate": b.get("evaluate", "")[:50],
                "total_count": b.get("total_count", 0),
                "url": b.get("url", ""),
                "follow_status": b.get("follow_status", 0),
                "progress": b.get("progress", ""),
            }
            for b in all_bangumis
        ]
    }


def cmd_favlist(args):
    """扫描收藏夹"""
    sessdata = args.cookie or get_sessdata()
    try:
        media_id = extract_media_id(args.target)
        print(f"正在扫描收藏夹 ID: {media_id}")
        
        result = fetch_favlist(media_id, sessdata)
        
        print(f"\n{'='*50}")
        print(f"收藏夹: {result['info']['title']}")
        print(f"UP主: {result['info']['owner']}")
        print(f"视频数: {result['info']['count']}")
        print(f"{'='*50}\n")
        
        if result["videos"]:
            for i, v in enumerate(result["videos"], 1):
                duration_str = f"{v['duration']//60}:{v['duration']%60:02d}"
                print(f"{i:3}. [{v['bvid']}] {v['title'][:40]:<40} ({duration_str})")
        else:
            print("收藏夹为空")
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n已保存到: {args.output}")
        
        return result
    except Exception as e:
        print(f"错误: {e}")
        return None


def cmd_bangumi(args):
    """扫描追番/追剧"""
    sessdata = args.cookie or get_sessdata()
    if not sessdata:
        print("错误: 扫描追番需要提供 --cookie 或设置 ALICE_BILI_SESSDATA 环境变量")
        return None
    
    try:
        user_id = extract_user_id(args.target)
        bangumi_type = 2 if args.drama else 1
        type_name = "追剧" if args.drama else "追番"
        print(f"正在扫描用户 {user_id} 的{type_name}列表...")
        
        result = fetch_bangumi(user_id, bangumi_type, sessdata)
        
        print(f"\n{'='*50}")
        print(f"用户ID: {result['info']['user_id']}")
        print(f"类型: {result['info']['type']}")
        print(f"数量: {result['info']['count']}")
        print(f"{'='*50}\n")
        
        if result["bangumis"]:
            for i, b in enumerate(result["bangumis"], 1):
                status = "在看" if b["follow_status"] == 2 else "想看"
                print(f"{i:3}. [{status}] {b['title'][:35]:<35} {b['progress']}")
        else:
            print(f"没有{type_name}")
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n已保存到: {args.output}")
        
        return result
    except Exception as e:
        print(f"错误: {e}")
        return None


def cmd_list(args):
    """列出用户的所有收藏夹"""
    sessdata = args.cookie or get_sessdata()
    
    try:
        user_id = extract_user_id(args.target)
        
        # 用户创建的收藏夹
        print(f"正在获取用户 {user_id} 的收藏夹...")
        created = fetch_user_favlists(user_id, sessdata)
        
        print(f"\n{'='*50}")
        print(f"用户创建的收藏夹 ({created['info']['count']}个)")
        print(f"{'='*50}")
        for f in created["folders"]:
            print(f"  [{f['id']}] {f['title']:<20} ({f['media_count']}个视频)")
        
        # 用户订阅的收藏夹和合集
        if sessdata:
            collected = fetch_collected_favlists(user_id, sessdata)
            
            # 订阅的收藏夹
            print(f"\n{'='*50}")
            print(f"订阅的收藏夹 ({collected['info']['folder_count']}个)")
            print(f"{'='*50}")
            if collected["folders"]:
                for f in collected["folders"]:
                    print(f"  [{f['id']}] {f['title']:<20} by {f['upper']} ({f['media_count']}个视频)")
            else:
                print("  (无)")
            
            # 订阅的合集
            print(f"\n{'='*50}")
            print(f"订阅的合集 ({collected['info']['season_count']}个)")
            print(f"{'='*50}")
            if collected["seasons"]:
                for s in collected["seasons"]:
                    print(f"  [{s['id']}] {s['title']:<25} by {s['upper']:<15} ({s['media_count']}个视频)")
            else:
                print("  (无)")
        
        if args.output:
            result = {"created": created, "collected": collected if sessdata else None}
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n已保存到: {args.output}")
        
    except Exception as e:
        print(f"错误: {e}")


def cmd_bvids(args):
    """获取用户所有收藏夹的BV号（分类输出）"""
    sessdata = args.cookie or get_sessdata()
    
    try:
        user_id = extract_user_id(args.target)
        print(f"正在扫描用户 {user_id} 的所有收藏夹BV号...")
        
        result = fetch_all_bvids(user_id, sessdata)
        
        print(f"\n{'='*50}")
        print("BV号汇总（按收藏夹分类）")
        print(f"{'='*50}")
        
        total = 0
        for folder in result["folders"]:
            count = len(folder["bvids"])
            total += count
            print(f"\n[{folder['title']}] ({count}个)")
            if args.verbose:
                for bv in folder["bvids"]:
                    print(f"  {bv}")
            else:
                # 只显示前5个
                for bv in folder["bvids"][:5]:
                    print(f"  {bv}")
                if count > 5:
                    print(f"  ... 还有 {count - 5} 个")
        
        print(f"\n总计: {total} 个视频")
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"已保存到: {args.output}")
        
    except Exception as e:
        print(f"错误: {e}")


def cmd_season(args):
    """扫描合集内的视频"""
    sessdata = args.cookie or get_sessdata()
    
    try:
        season_id = args.target
        # 尝试从URL提取season_id
        match = re.search(r'season_id=(\d+)', season_id)
        if match:
            season_id = match.group(1)
        elif not season_id.isdigit():
            # 尝试从collected list的link格式提取
            match = re.search(r'/(\d+)\?', season_id)
            if match:
                season_id = match.group(1)
        
        print(f"正在扫描合集 ID: {season_id}")
        
        result = fetch_season(season_id, args.mid or "", sessdata)
        
        print(f"\n{'='*50}")
        print(f"合集视频列表 ({result['info']['count']}个)")
        print(f"{'='*50}\n")
        
        for i, v in enumerate(result["videos"], 1):
            duration_str = f"{v['duration']//60}:{v['duration']%60:02d}"
            view_str = f"{v['view']//10000}万" if v['view'] >= 10000 else str(v['view'])
            if args.verbose:
                print(f"{i:3}. [{v['bvid']}] {v['title'][:40]:<40} ({duration_str}) {view_str}播放")
            else:
                print(f"{i:3}. [{v['bvid']}] {v['title'][:50]}")
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n已保存到: {args.output}")
        
        # 仅输出BV号列表
        if args.bvonly:
            print(f"\n{'='*50}")
            print("BV号列表:")
            print(f"{'='*50}")
            for v in result["videos"]:
                print(v["bvid"])
        
        return result
        
    except Exception as e:
        print(f"错误: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="B站收藏夹/追番扫描工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # 收藏夹子命令
    fav_parser = subparsers.add_parser("favlist", help="扫描收藏夹")
    fav_parser.add_argument("target", help="收藏夹URL或ID")
    fav_parser.add_argument("--cookie", help="SESSDATA cookie")
    fav_parser.add_argument("--output", "-o", help="输出JSON文件路径")
    fav_parser.set_defaults(func=cmd_favlist)
    
    # 追番子命令
    bangumi_parser = subparsers.add_parser("bangumi", help="扫描追番/追剧")
    bangumi_parser.add_argument("target", help="用户空间URL或ID")
    bangumi_parser.add_argument("--cookie", help="SESSDATA cookie")
    bangumi_parser.add_argument("--drama", action="store_true", help="扫描追剧(默认追番)")
    bangumi_parser.add_argument("--output", "-o", help="输出JSON文件路径")
    bangumi_parser.set_defaults(func=cmd_bangumi)
    
    # 列出收藏夹子命令
    list_parser = subparsers.add_parser("list", help="列出用户所有收藏夹")
    list_parser.add_argument("target", help="用户空间URL或ID")
    list_parser.add_argument("--cookie", help="SESSDATA cookie")
    list_parser.add_argument("--output", "-o", help="输出JSON文件路径")
    list_parser.set_defaults(func=cmd_list)
    
    # 获取所有BV号子命令
    bvids_parser = subparsers.add_parser("bvids", help="获取用户所有收藏夹的BV号")
    bvids_parser.add_argument("target", help="用户空间URL或ID")
    bvids_parser.add_argument("--cookie", help="SESSDATA cookie")
    bvids_parser.add_argument("--verbose", "-v", action="store_true", help="显示所有BV号")
    bvids_parser.add_argument("--output", "-o", help="输出JSON文件路径")
    bvids_parser.set_defaults(func=cmd_bvids)
    
    # 扫描合集子命令
    season_parser = subparsers.add_parser("season", help="扫描合集内的视频")
    season_parser.add_argument("target", help="合集ID")
    season_parser.add_argument("--mid", help="UP主ID (可选)")
    season_parser.add_argument("--cookie", help="SESSDATA cookie")
    season_parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")
    season_parser.add_argument("--bvonly", action="store_true", help="仅输出BV号列表")
    season_parser.add_argument("--output", "-o", help="输出JSON文件路径")
    season_parser.set_defaults(func=cmd_season)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == "__main__":
    main()
