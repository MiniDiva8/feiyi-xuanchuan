"""Exercise the AI review through persisted, tenant-scoped application routes."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'services' / 'api'), str(ROOT / 'services' / 'marketing-ai')]


@pytest.mark.parametrize('objective,ratio', [
    ('sales', '订单/咨询计数比：50%'),
    ('registration', '到场/报名计数比：75%'),
])
def test_persisted_review_keeps_campaign_and_workspace_boundaries(tmp_path, monkeypatch, objective, ratio):
    monkeypatch.delenv('MARKETING_AI_API_KEY', raising=False)
    from app.main import create_app

    def post(client, path, data):
        response = client.post(path, json=data)
        assert response.status_code in (200, 201), response.text
        return response.json()

    def campaign(client, workspace, suffix):
        return post(client, f'/api/workspaces/{workspace}/campaigns', {
            'name': suffix, 'objective': objective, 'audience': '本地居民',
            'start_date': '2026-11-01', 'end_date': '2026-11-07',
            'budget': 100, 'channels': ['微信'], 'notes': '',
        })['id']

    def metric(client, workspace, cid, inquiries):
        return post(client, f'/api/workspaces/{workspace}/metrics', {
            'campaign_id': cid, 'date': '2026-11-02', 'channel': '微信',
            'source': '测试合成台账', 'attribution': 'unknown', 'inquiries': inquiries,
            'impressions': 100, 'interactions': 10, 'orders': 5, 'registrations': 4,
            'checkins': 3, 'revenue': 100, 'refunds': 20, 'spend': 10,
        })

    app = create_app('sqlite:///' + str(tmp_path / 'review.db'), str(tmp_path / 'files'))
    with TestClient(app) as client:
        owner = post(client, '/api/auth/register', {
            'name': '测试商家', 'email': f'{objective}@review.example',
            'password': 'Synthetic-review-2026', 'workspace_name': '当前工坊',
        })
        workspace = owner['workspaces'][0]['id']
        target = campaign(client, workspace, '本轮活动')
        other_campaign = campaign(client, workspace, '其他活动')
        other_workspace = post(client, '/api/workspaces', {'name': '另一个商家'})['id']
        foreign_campaign = campaign(client, other_workspace, '另一商家活动')
        metric(client, workspace, target, 10)
        metric(client, workspace, other_campaign, 10000)
        metric(client, other_workspace, foreign_campaign, 20000)

        base = f'/api/workspaces/{workspace}/campaigns/{target}'
        review = post(client, base + '/reviews/generate', {})
        assert review['generation_mode'] == 'template'
        statements = [row['statement'] for row in review['content']['facts']]
        assert '本次统计包含1条已录入数据记录。' in statements
        assert '咨询：10。' in statements
        assert ratio + '。' in statements
        assert '收入扣除退款为80元。' in statements
        assert '归因未知收入占录入收入比：100%。' in statements
        assert all('10000' not in line and '20000' not in line for line in statements)
        assert any('去重' in line for line in review['content']['limitations'])

        # A later metric changes a new review, not the persisted historical one.
        metric(client, workspace, target, 30)
        second = post(client, base + '/reviews/generate', {})
        assert second['id'] != review['id']
        history = client.get(base + '/reviews').json()
        assert next(row for row in history if row['id'] == review['id'])['content'] == review['content']
        assert any(row['statement'] == '咨询：40。' for row in second['content']['facts'])
        assert client.get(f'/api/workspaces/{other_workspace}/campaigns/{target}/reviews').status_code == 404
