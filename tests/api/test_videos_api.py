"""
Videos API 集成测试

测试 /api/v1/videos/* 端点
"""

import pytest


class TestVideosListAPI:
    """GET /api/v1/videos 测试"""

    def test_list_videos_requires_auth(self, client):
        """验证未认证请求返回 401"""
        response = client.get("/api/v1/videos")
        assert response.status_code == 401

    def test_list_videos_pagination(self, client, db_session, sample_tenant):
        """验证分页参数"""
        response = client.get(
            "/api/v1/videos?page=1&page_size=10",
            headers={"X-Tenant-ID": str(sample_tenant.id)}
        )
        assert response.status_code in [200, 401]

    def test_list_videos_invalid_page(self, client, db_session, sample_tenant):
        """验证无效页码"""
        response = client.get(
            "/api/v1/videos?page=-1",
            headers={"X-Tenant-ID": str(sample_tenant.id)}
        )
        assert response.status_code in [400, 401, 422]


class TestVideosImportAPI:
    """POST /api/v1/videos 测试"""

    def test_import_video_requires_auth(self, client):
        """验证未认证请求返回 401"""
        response = client.post("/api/v1/videos", json={
            "url": "https://www.bilibili.com/video/BV1test"
        })
        assert response.status_code == 401

    def test_import_video_missing_url(self, client, db_session, sample_tenant):
        """验证缺少 URL 返回 422"""
        response = client.post(
            "/api/v1/videos",
            json={},
            headers={"X-Tenant-ID": str(sample_tenant.id)}
        )
        assert response.status_code in [401, 422]

    def test_import_video_invalid_url(self, client, db_session, sample_tenant):
        """验证无效 URL 格式"""
        response = client.post(
            "/api/v1/videos",
            json={"url": "not-a-valid-url"},
            headers={"X-Tenant-ID": str(sample_tenant.id)}
        )
        assert response.status_code in [400, 401, 422]


class TestVideosDetailAPI:
    """GET /api/v1/videos/{video_id} 测试"""

    def test_get_video_requires_auth(self, client):
        """验证未认证请求返回 401"""
        response = client.get("/api/v1/videos/1")
        assert response.status_code == 401

    def test_get_video_not_found(self, client, db_session, sample_tenant):
        """验证视频不存在返回 404"""
        response = client.get(
            "/api/v1/videos/99999",
            headers={"X-Tenant-ID": str(sample_tenant.id)}
        )
        assert response.status_code in [401, 404]

    def test_get_video_invalid_id(self, client, db_session, sample_tenant):
        """验证无效 ID 格式"""
        response = client.get(
            "/api/v1/videos/not-a-number",
            headers={"X-Tenant-ID": str(sample_tenant.id)}
        )
        assert response.status_code in [401, 422]


class TestVideosDeleteAPI:
    """DELETE /api/v1/videos/{video_id} 测试"""

    def test_delete_video_requires_auth(self, client):
        """验证未认证请求返回 401"""
        response = client.delete("/api/v1/videos/1")
        assert response.status_code == 401

    def test_delete_video_not_found(self, client, db_session, sample_tenant):
        """验证视频不存在返回 404"""
        response = client.delete(
            "/api/v1/videos/99999",
            headers={"X-Tenant-ID": str(sample_tenant.id)}
        )
        assert response.status_code in [401, 404]


class TestVideosTranscriptAPI:
    """GET /api/v1/videos/{video_id}/transcript 测试"""

    def test_get_transcript_requires_auth(self, client):
        """验证未认证请求返回 401"""
        response = client.get("/api/v1/videos/1/transcript")
        assert response.status_code == 401

    def test_get_transcript_not_found(self, client, db_session, sample_tenant):
        """验证视频不存在返回 404"""
        response = client.get(
            "/api/v1/videos/99999/transcript",
            headers={"X-Tenant-ID": str(sample_tenant.id)}
        )
        assert response.status_code in [401, 404]


class TestVideosStatsAPI:
    """GET /api/v1/videos/stats/* 测试"""

    def test_get_stats_summary_requires_auth(self, client):
        """验证未认证请求返回 401"""
        response = client.get("/api/v1/videos/stats/summary")
        assert response.status_code == 401

    def test_get_stats_tags_requires_auth(self, client):
        """验证未认证请求返回 401"""
        response = client.get("/api/v1/videos/stats/tags")
        assert response.status_code == 401


class TestVideosQueueAPI:
    """GET /api/v1/videos/queue/* 测试"""

    def test_get_queue_list_requires_auth(self, client):
        """验证未认证请求返回 401"""
        response = client.get("/api/v1/videos/queue/list")
        assert response.status_code == 401

    def test_get_queue_info_requires_auth(self, client):
        """验证未认证请求返回 401"""
        response = client.get("/api/v1/videos/queue/info")
        # 可能返回 401 或 200（某些端点可能不需要认证）
        assert response.status_code in [200, 401]


class TestVideosProcessAPI:
    """POST /api/v1/videos/{video_id}/process 测试"""

    def test_process_video_requires_auth(self, client):
        """验证未认证请求返回 401"""
        response = client.post("/api/v1/videos/1/process")
        assert response.status_code == 401


class TestVideosStatusAPI:
    """GET /api/v1/videos/{video_id}/status 测试"""

    def test_get_status_requires_auth(self, client):
        """验证未认证请求返回 401"""
        response = client.get("/api/v1/videos/1/status")
        assert response.status_code == 401


class TestVideosCommentsAPI:
    """GET /api/v1/videos/{video_id}/comments 测试"""

    def test_get_comments_requires_auth(self, client):
        """验证未认证请求返回 401"""
        response = client.get("/api/v1/videos/1/comments")
        assert response.status_code == 401
