import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api"))
sys.path.insert(0, str(ROOT / "services/marketing-ai"))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("MARKETING_AI_API_KEY", raising=False)
    from app.main import create_app

    with TestClient(create_app("sqlite:///" + str(tmp_path / "test.db"))) as c:
        yield c


def register(c, email="owner@example.com"):
    r = c.post(
        "/api/auth/register",
        json={
            "name": "商家",
            "email": email,
            "password": "correct-password",
            "workspace_name": "真实商家",
        },
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["workspaces"][0]["id"]


def test_photo_poster_preview_revision_and_export(client):
    import base64
    w = register(client)
    _, ca, plan, _ = prepared(client, w)
    poster = post(client, w, f"campaigns/{ca['id']}/assets/generate",
                  {"plan_id": plan['id'], "channel": "公众号", "kind": "poster"})
    post(client, w, f"assets/{poster['id']}/approve", {})
    png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII=')
    image = client.post(f'/api/workspaces/{w}/files', files={'file': ('photo.png', png, 'image/png')}).json()
    payload = {'title': '<实拍>课程', 'body': '真实体验课程，详情见报名入口', 'poster_template': 'warm',
               'poster_image_id': image['id'], 'photo_confirmed': True}
    prefix = f'/api/workspaces/{w}/assets/{poster["id"]}'
    preview = client.post(prefix + '/preview', json=payload)
    assert preview.status_code == 200
    assert 'data:image/png;base64,' in preview.text
    assert '待审核预览' in preview.text and '商家已审核版本' not in preview.text
    assert '&lt;实拍&gt;' in preview.text
    revised = client.post(prefix + '/revise', json=payload).json()
    assert revised['status'] == 'draft'
    assert revised['content']['poster_template'] == 'warm'
    assert client.get(prefix + '/export?format=svg').status_code == 409
    new = f'/api/workspaces/{w}/assets/{revised["id"]}'
    assert client.get(new + '/export?format=svg').status_code == 409
    assert client.post(new + '/approve', json={}).status_code == 200
    exported = client.get(new + '/export?format=svg')
    assert exported.status_code == 200
    assert 'data:image/png;base64,' in exported.text
    assert '商家已审核版本' in exported.text and '#914d35' in exported.text
    removed = client.post(new + '/revise', json={**payload, 'poster_image_id': None}).json()
    assert removed['content']['poster_image_id'] is None
    assert removed['content']['photo_confirmed'] is False


def test_photo_poster_rejects_foreign_nonimage_and_missing_consent(client):
    w = register(client)
    _, ca, plan, _ = prepared(client, w)
    poster = post(client, w, f"campaigns/{ca['id']}/assets/generate",
                  {"plan_id": plan['id'], "channel": "公众号", "kind": "poster"})
    other = client.post('/api/workspaces', json={'name': '另一商家'}).json()['id']
    foreign = client.post(f'/api/workspaces/{other}/files', files={'file': ('photo.png', b'\x89PNG\r\n\x1a\nbytes', 'image/png')}).json()['id']
    text = client.post(f'/api/workspaces/{w}/files', files={'file': ('notes.txt', b'notes', 'text/plain')}).json()['id']
    local = client.post(f'/api/workspaces/{w}/files', files={'file': ('photo.png', b'\x89PNG\r\n\x1a\nbytes', 'image/png')}).json()['id']
    prefix = f'/api/workspaces/{w}/assets/{poster["id"]}'
    for suffix in ('preview', 'revise'):
        for file_id, consent, expected in ((foreign, True, 404), (text, True, 422), (local, False, 422)):
            result = client.post(prefix + '/' + suffix, json={'body': '文案', 'poster_image_id': file_id, 'photo_confirmed': consent})
            assert result.status_code == expected, result.text
        assert client.post(prefix + '/' + suffix, json={'body': '文案', 'poster_template': 'unknown'}).status_code == 422


def post(c, w, path, data):
    r = c.post(f"/api/workspaces/{w}/{path}", json=data)
    assert r.status_code in (200, 201), r.text
    return r.json()


def campaign(c, w):
    return post(
        c,
        w,
        "campaigns",
        {
            "name": "真实课程",
            "objective": "registration",
            "audience": "社区居民",
            "start_date": "2026-11-01",
            "end_date": "2026-11-03",
            "budget": 100,
            "channels": ["公众号"],
            "notes": "",
        },
    )


def prepared(c, w):
    k = post(
        c,
        w,
        "knowledge",
        {
            "title": "技艺来源",
            "content": "商家确认的剪纸体验内容",
            "source": "商家书面介绍",
            "usage_scope": "marketing",
            "confirmed": True,
            "kind": "fact",
        },
    )
    offering = post(
        c,
        w,
        "offerings",
        {
            "kind": "course",
            "name": "剪纸体验",
            "description": "真实体验课程",
            "price": 30,
            "quantity": 10,
            "location": "门店",
            "delivery": "现场",
            "conversion_url": "https://example.com/join",
        },
    )
    ca = post(
        c,
        w,
        "campaigns",
        {
            "name": "真实课程",
            "objective": "registration",
            "audience": "社区居民",
            "start_date": "2026-11-01",
            "end_date": "2026-11-03",
            "budget": 100,
            "channels": ["公众号"],
            "offering_id": offering["id"],
            "notes": "",
        },
    )
    p = post(c, w, f"campaigns/{ca['id']}/plans/generate", {})
    post(c, w, f"plans/{p['id']}/approve", {})
    a = post(
        c,
        w,
        f"campaigns/{ca['id']}/assets/generate",
        {"plan_id": p["id"], "channel": "公众号", "kind": "copy"},
    )
    post(c, w, f"assets/{a['id']}/approve", {})
    return k, ca, p, a


def test_empty_workspace_auth_and_logout(client):
    assert client.get("/api/workspaces").status_code == 401
    w = register(client)
    assert "HttpOnly" in client.cookies.get(
        "heritage_session", ""
    ) or client.cookies.get("heritage_session")
    assert client.get(f"/api/workspaces/{w}/campaigns").json() == []
    assert client.get(f"/api/workspaces/{w}/overview").json()["stats"]["revenue"] == 0
    assert client.post("/api/auth/logout", json={}).status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_channel_accounts_snapshots_and_isolation(client):
    w = register(client)
    root = f'/api/workspaces/{w}/channels'
    payload = {'platform': 'douyin', 'name': '手艺工坊', 'account_id': 'craft-123', 'profile_url': 'https://www.douyin.com/user/craft-123'}
    account = client.post(root, json=payload)
    assert account.status_code == 201, account.text
    id = account.json()['id']
    assert client.patch(root + '/' + id, json={**payload, 'name': '新昵称'}).status_code == 200
    assert client.patch(root + '/' + id, json={**payload, 'account_id': 'different'}).status_code == 422
    assert client.post(root, json=payload).status_code == 409
    assert client.post(root, json={**payload, 'profile_url': 'https://evil.invalid'}).status_code == 422
    snap = {'date': '2026-10-30', 'source': '创作者后台累计口径', 'followers': 100, 'views': 2000, 'posts': 5}
    assert client.post(root + f'/{id}/snapshots', json=snap).status_code == 201
    assert client.post(root + f'/{id}/snapshots', json=snap).status_code == 409
    assert client.post(root + f'/{id}/snapshots', json={**snap, 'date': '2026-10-31', 'followers': 95}).status_code == 201
    account = client.get(root).json()[0]
    assert account['sync_status'] == 'not_connected'
    assert account['follower_change'] == -5
    assert account['latest']['views'] == 2000
    assert account['latest']['likes'] is None
    assert account['latest']['source_type'] == 'manual'
    other = client.post('/api/workspaces', json={'name': '其他商家'}).json()['id']
    assert client.get(f'/api/workspaces/{other}/channels').json() == []
    assert client.post(f'/api/workspaces/{other}/channels/{id}/snapshots', json=snap).status_code == 404


def test_channel_snapshot_validation_and_video_account_without_link(client):
    w = register(client)
    root = f'/api/workspaces/{w}/channels'
    account = client.post(root, json={'platform': 'channels', 'name': '视频号工坊', 'account_id': '视频号名称'}).json()
    endpoint = root + '/' + account['id'] + '/snapshots'
    baseline = {'date': '2026-10-31', 'source': '视频号助手'}
    assert client.post(endpoint, json=baseline).status_code == 422
    for invalid in ({'followers': True}, {'views': -1}, {'likes': 1.5}, {'followers': 5, 'date': '2099-01-01'}, {'followers': 5, 'latest_post_date': '2026-11-01'}):
        assert client.post(endpoint, json={**baseline, **invalid}).status_code == 422
    assert client.post(endpoint, json={**baseline, 'followers': 0}).status_code == 201
    item = client.get(root).json()[0]
    assert item['latest']['followers'] == 0
    assert item['latest']['views'] is None


def test_tenant_isolation_including_files_tasks_and_metrics(client):
    w = register(client)
    _, ca, p, a = prepared(client, w)
    f = client.post(
        f"/api/workspaces/{w}/files",
        files={"file": ("notes.txt", b"private text", "text/plain")},
    ).json()
    task = client.get(f"/api/workspaces/{w}/tasks").json()[0]
    client.post("/api/auth/logout", json={})
    other = register(client, "other@example.com")
    for path in [
        f'/files/{f["id"]}',
        f'/campaigns/{ca["id"]}',
        f'/assets/{a["id"]}/export',
    ]:
        assert client.get(f"/api/workspaces/{other}{path}").status_code == 404
    assert client.get(f"/api/workspaces/{w}/audit").status_code in (403, 404)
    assert (
        client.post(
            f'/api/workspaces/{other}/tasks/{task["id"]}/retry', json={}
        ).status_code
        == 404
    )
    assert (
        client.get(
            f'/api/workspaces/{other}/metrics?campaign_id={ca["id"]}'
        ).status_code
        == 404
    )


def test_review_versions_and_source_invalidation(client):
    w = register(client)
    k, ca, p, a = prepared(client, w)
    assert client.get(f'/api/workspaces/{w}/assets/{a["id"]}/export').status_code == 200
    revised = post(client, w, f'assets/{a["id"]}/revise', {"body": "修订文案"})
    assert revised["id"] != a["id"] and revised["status"] == "draft"
    assert client.get(f'/api/workspaces/{w}/assets/{a["id"]}/export').status_code == 409
    post(client, w, f'assets/{revised["id"]}/approve', {})
    assert (
        client.patch(
            f'/api/workspaces/{w}/knowledge/{k["id"]}', json={"confirmed": False}
        ).status_code
        == 200
    )
    assert (
        client.get(f'/api/workspaces/{w}/assets/{revised["id"]}/export').status_code
        == 409
    )
    assert (
        client.post(
            f"/api/workspaces/{w}/publications",
            json={
                "asset_id": revised["id"],
                "channel": "公众号",
                "url": "https://example.com/work",
                "published_at": "2026-11-01T10:00:00Z",
            },
        ).status_code
        == 409
    )


def test_csv_is_atomic_and_deduped_with_real_analytics(client):
    w = register(client)
    ca = campaign(client, w)
    header = "campaign_id,date,channel,source,external_id,attribution,impressions,orders,revenue,spend\n"
    good = header + f'{ca["id"]},2026-11-01,公众号,人工登记,row1,known,200,2,150,30\n'
    bad = good + f'{ca["id"]},2026-11-02,公众号,人工登记,row2,known,-1,0,0,0\n'
    preview = post(client, w, "metrics/preview", {"csv": bad})
    assert preview["errors"] and preview["valid_rows"] == 1
    assert (
        client.post(
            f"/api/workspaces/{w}/metrics/import", json={"csv": bad}
        ).status_code
        == 422
    )
    assert client.get(f"/api/workspaces/{w}/metrics").json() == []
    assert post(client, w, "metrics/import", {"csv": good}) == {
        "imported": 1,
        "duplicates": 0,
    }
    assert post(client, w, "metrics/import", {"csv": good}) == {
        "imported": 0,
        "duplicates": 1,
    }
    analytics = client.get(f"/api/workspaces/{w}/analytics").json()
    assert (
        analytics["stats"]["revenue"] == 150
        and analytics["stats"]["orders"] == 2
        and analytics["records"] == 1
    )
    review = post(client, w, f'campaigns/{ca["id"]}/reviews/generate', {})
    assert review["content"]["facts"] and review["generation_mode"] == "template"
    assert (
        post(client, w, f'campaigns/{ca["id"]}/next-round', {})["previous_campaign_id"]
        == ca["id"]
    )


def test_roles_origin_and_active_upload(client):
    w = register(client)
    client.post("/api/auth/logout", json={})
    register(client, "review@example.com")
    client.post("/api/auth/logout", json={})
    client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "correct-password"},
    )
    post(client, w, "members", {"email": "review@example.com", "role": "reviewer"})
    assert (
        client.post(
            f"/api/workspaces/{w}/campaigns",
            json={},
            headers={"Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/workspaces/{w}/files",
            files={"file": ("evil.svg", b"<svg/>", "image/svg+xml")},
        ).status_code
        == 422
    )
    client.post("/api/auth/logout", json={})
    client.post(
        "/api/auth/login",
        json={"email": "review@example.com", "password": "correct-password"},
    )
    assert (
        client.post(
            f"/api/workspaces/{w}/knowledge",
            json={
                "title": "x",
                "content": "x",
                "source": "x",
                "usage_scope": "marketing",
                "confirmed": True,
                "kind": "fact",
            },
        ).status_code
        == 403
    )


def test_password_hash_and_restart_persistence(tmp_path, monkeypatch):
    monkeypatch.delenv("MARKETING_AI_API_KEY", raising=False)
    from app.main import create_app
    from app.security import hash_password, verify_password

    one = hash_password("same-password")
    two = hash_password("same-password")
    assert (
        one != two
        and verify_password("same-password", one)
        and not verify_password("wrong", one)
    )
    url = "sqlite:///" + str(tmp_path / "persist.db")
    with TestClient(create_app(url)) as c:
        w = register(c)
        ca = campaign(c, w)
    with TestClient(create_app(url)) as c:
        assert (
            c.post(
                "/api/auth/login",
                json={"email": "owner@example.com", "password": "correct-password"},
            ).status_code
            == 200
        )
        assert c.get(f"/api/workspaces/{w}/campaigns").json()[0]["id"] == ca["id"]


def test_plan_revision_and_offering_invalidates_asset(client):
    w = register(client)
    offering = post(
        client,
        w,
        "offerings",
        {
            "kind": "course",
            "name": "剪纸体验",
            "description": "基础体验",
            "price": 30,
            "quantity": 10,
            "location": "门店",
            "delivery": "现场",
            "conversion_url": "https://example.com/join",
        },
    )
    ca = post(
        client,
        w,
        "campaigns",
        {
            "name": "课程推广",
            "objective": "registration",
            "audience": "社区",
            "start_date": "2026-11-01",
            "end_date": "2026-11-03",
            "budget": 30,
            "channels": ["公众号"],
            "notes": "",
            "offering_id": offering["id"],
        },
    )
    p = post(client, w, f'campaigns/{ca["id"]}/plans/generate', {})
    assert (
        client.post(
            f'/api/workspaces/{w}/campaigns/{ca["id"]}/assets/generate',
            json={"plan_id": p["id"], "channel": "公众号", "kind": "copy"},
        ).status_code
        == 409
    )
    post(client, w, f'plans/{p["id"]}/approve', {})
    a = post(
        client,
        w,
        f'campaigns/{ca["id"]}/assets/generate',
        {"plan_id": p["id"], "channel": "公众号", "kind": "copy"},
    )
    post(client, w, f'assets/{a["id"]}/approve', {})
    client.patch(f'/api/workspaces/{w}/offerings/{offering["id"]}', json={"price": 40})
    assert client.get(f'/api/workspaces/{w}/assets/{a["id"]}/export').status_code == 409
    new = post(client, w, f'plans/{p["id"]}/revise', {"instructions": "新价格"})
    assert new["version"] == 2 and new["status"] == "draft"
    assert (
        client.post(f'/api/workspaces/{w}/plans/{p["id"]}/approve', json={}).status_code
        == 409
    )


def test_metric_validation_and_manual_idempotency(client):
    w = register(client)
    ca = campaign(client, w)
    data = {
        "campaign_id": ca["id"],
        "date": "2026-11-01",
        "channel": "公众号",
        "source": "手工",
        "attribution": "unknown",
        "orders": 1,
        "revenue": 30,
    }
    assert post(client, w, "metrics", data)["revenue"] == 30
    assert client.post(f"/api/workspaces/{w}/metrics", json=data).status_code == 409
    assert (
        client.post(
            f"/api/workspaces/{w}/metrics",
            json={**data, "external_id": "new", "refunds": 40},
        ).status_code
        == 422
    )
    assert (
        client.get(f"/api/workspaces/{w}/analytics").json()["stats"]["unknown_revenue"]
        == 30
    )


def test_failed_jobs_are_visible_bounded_and_do_not_fabricate_drafts(
    client, monkeypatch
):
    w = register(client)
    ca = campaign(client, w)
    import app.workflow as workflow

    def broken(kind, ctx):
        raise RuntimeError("private-provider-detail")

    monkeypatch.setattr(workflow, "ai_call", broken)
    endpoint = f"/api/workspaces/{w}"
    assert (
        client.post(
            endpoint + f'/campaigns/{ca["id"]}/plans/generate', json={}
        ).status_code
        == 502
    )
    jobs = client.get(endpoint + "/tasks").json()
    assert len(jobs) == 1 and jobs[0]["status"] == "failed"
    assert "private-provider-detail" not in str(jobs)
    assert client.get(endpoint + f'/campaigns/{ca["id"]}/plans').json() == []
    retry = endpoint + f'/tasks/{jobs[0]["id"]}/retry'
    assert client.post(retry, json={}).status_code == 502
    assert client.post(retry, json={}).status_code == 502
    assert client.post(retry, json={}).status_code == 409


def test_boolean_metrics_are_not_integer_counts(client):
    w = register(client)
    ca = campaign(client, w)
    data = {
        "campaign_id": ca["id"],
        "date": "2026-11-01",
        "channel": "微信",
        "source": "人工",
        "attribution": "known",
        "orders": True,
    }
    assert client.post(f"/api/workspaces/{w}/metrics", json=data).status_code == 422


def test_exports_escape_active_markup_and_api_fallback(client):
    w = register(client)
    k, ca, p, a = prepared(client, w)
    revised = post(
        client,
        w,
        f'assets/{a["id"]}/revise',
        {"title": "标题<script>", "body": "<script>alert(1)</script>"},
    )
    post(client, w, f'assets/{revised["id"]}/approve', {})
    for fmt in ("html", "svg"):
        response = client.get(
            f'/api/workspaces/{w}/assets/{revised["id"]}/export?format={fmt}'
        )
        assert response.status_code == 200 and b"<script>" not in response.content
        assert "attachment" in response.headers["content-disposition"]
    assert client.get("/api/does-not-exist").status_code == 404
    assert client.get("/api/health").json() == {"ok": True}


def test_sales_registration_require_real_available_offering_before_approval(client):
    w = register(client)
    ca = campaign(client, w)
    p = post(client, w, f'campaigns/{ca["id"]}/plans/generate', {})
    result = client.post(f'/api/workspaces/{w}/plans/{p["id"]}/approve', json={})
    assert result.status_code == 409 and isinstance(result.json()["detail"], str)


def test_pdf_upload_rejected_until_active_content_can_be_verified(client):
    w = register(client)
    result = client.post(
        f"/api/workspaces/{w}/files",
        files={
            "file": (
                "source.pdf",
                b"%PDF-1.7 innocuous-looking compressed objects",
                "application/pdf",
            )
        },
    )
    assert result.status_code == 422


def test_empty_external_id_dedupes_like_omitted_external_id(client):
    w = register(client)
    ca = campaign(client, w)
    payload = {
        "campaign_id": ca["id"],
        "date": "2026-11-01",
        "channel": "微信",
        "source": "手工",
        "attribution": "unknown",
        "revenue": 20,
    }
    post(client, w, "metrics", payload)
    assert (
        client.post(
            f"/api/workspaces/{w}/metrics", json={**payload, "external_id": ""}
        ).status_code
        == 409
    )


def test_conflicting_external_ids_reject_csv_atomically(client):
    w = register(client)
    ca = campaign(client, w)
    header = "campaign_id,date,channel,source,external_id,attribution,revenue\n"
    one = f'{ca["id"]},2026-11-01,微信,手工,same-key,known,10\n'
    two = f'{ca["id"]},2026-11-01,微信,手工,same-key,known,900\n'
    result = post(client, w, "metrics/preview", {"csv": header + one + two})
    assert result["errors"] and result["errors"][0]["row"] == 3
    assert (
        client.post(
            f"/api/workspaces/{w}/metrics/import", json={"csv": header + one + two}
        ).status_code
        == 422
    )
    assert client.get(f"/api/workspaces/{w}/metrics").json() == []
    post(client, w, "metrics/import", {"csv": header + one})
    assert post(client, w, "metrics/preview", {"csv": header + two})["errors"]
    assert (
        client.post(
            f"/api/workspaces/{w}/metrics/import", json={"csv": header + two}
        ).status_code
        == 422
    )
    assert client.get(f"/api/workspaces/{w}/analytics").json()["stats"]["revenue"] == 10


def test_manual_plan_revisions_validate_shapes_and_business_constraints(client):
    import copy

    w = register(client)
    k, ca, p, a = prepared(client, w)
    endpoint = f'/api/workspaces/{w}/plans/{p["id"]}/revise'
    assert (
        client.post(
            endpoint,
            json={"instructions": "", "content": {key: None for key in p["content"]}},
        ).status_code
        == 422
    )
    for mutation in ("budget", "schedule", "channel", "evidence"):
        content = copy.deepcopy(p["content"])
        if mutation == "budget":
            content["budget"][0]["amount"] = 100000
        elif mutation == "schedule":
            content["schedule"][0]["day"] = "2030-01-01"
        elif mutation == "channel":
            content["channels"][0]["channel"] = "未批准渠道"
        else:
            content["evidence"] = [{"id": "foreign", "title": "伪造", "source": "未知"}]
        assert (
            client.post(
                endpoint, json={"instructions": "调整", "content": content}
            ).status_code
            == 422
        ), mutation
    assert (
        client.post(
            endpoint, json={"instructions": "调整", "content": p["content"]}
        ).status_code
        == 201
    )


def test_asset_channel_requires_approved_plan_channel(client):
    w = register(client)
    k, ca, p, a = prepared(client, w)
    assert (
        client.post(
            f'/api/workspaces/{w}/campaigns/{ca["id"]}/assets/generate',
            json={"plan_id": p["id"], "kind": "copy", "channel": "未批准渠道"},
        ).status_code
        == 422
    )


def test_concurrent_final_retry_claims_provider_once(client, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    import app.workflow as workflow
    import app.routes_workflow as routes

    w = register(client)
    ca = campaign(client, w)

    def broken(kind, ctx):
        raise RuntimeError("provider failure")

    monkeypatch.setattr(workflow, "ai_call", broken)
    base = f"/api/workspaces/{w}"
    client.post(base + f'/campaigns/{ca["id"]}/plans/generate', json={})
    job = client.get(base + "/tasks").json()[0]
    endpoint = base + f'/tasks/{job["id"]}/retry'
    client.post(endpoint, json={})
    both_loaded = Barrier(2)
    both_providers = Barrier(2)
    calls = []
    original = routes.run_generation

    def synchronized_claim(*args, **kwargs):
        both_loaded.wait(timeout=5)
        return original(*args, **kwargs)

    def provider_failure(kind, ctx):
        calls.append(True)
        try:
            both_providers.wait(timeout=1)
        except Exception:
            pass
        raise RuntimeError("failure")

    monkeypatch.setattr(routes, "run_generation", synchronized_claim)
    monkeypatch.setattr(workflow, "ai_call", provider_failure)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: client.post(endpoint, json={}), range(2)))
    assert sorted(response.status_code for response in responses) == [409, 502]
    assert len(calls) == 1


def test_trusted_origin_setting_preserves_actual_same_origin(tmp_path, monkeypatch):
    monkeypatch.setenv("TRUSTED_ORIGINS", "https://trusted.example")
    from app.main import create_app

    with TestClient(create_app("sqlite:///" + str(tmp_path / "origins.db"))) as c:
        data = {
            "name": "商家",
            "email": "origins@example.com",
            "password": "correct-password",
            "workspace_name": "商家",
        }
        assert (
            c.post(
                "/api/auth/register", json=data, headers={"Origin": "http://testserver"}
            ).status_code
            == 201
        )
        assert (
            c.post(
                "/api/auth/logout",
                json={},
                headers={"Origin": "https://trusted.example"},
            ).status_code
            == 200
        )
        assert (
            c.post(
                "/api/auth/login",
                json={"email": data["email"], "password": data["password"]},
                headers={"Origin": "https://evil.example"},
            ).status_code
            == 403
        )


def test_campaign_edit_invalidates_approval_preserves_publication(client):
    w = register(client)
    k, ca, p, a = prepared(client, w)
    publication = post(
        client,
        w,
        "publications",
        {
            "asset_id": a["id"],
            "channel": "公众号",
            "url": "https://example.com/original",
            "published_at": "2026-11-01T10:00:00Z",
        },
    )
    result = client.patch(
        f'/api/workspaces/{w}/campaigns/{ca["id"]}',
        json={"budget": 50, "start_date": "2026-12-01", "end_date": "2026-12-03"},
    )
    assert result.status_code == 200
    updated = result.json()
    assert updated["id"] == ca["id"] and updated["budget"] == 50
    assert updated["created_at"] == ca["created_at"]
    assert client.get(f'/api/workspaces/{w}/assets/{a["id"]}/export').status_code == 409
    assert (
        client.get(f"/api/workspaces/{w}/publications").json()[0]["id"]
        == publication["id"]
    )
    assert (
        client.patch(
            f'/api/workspaces/{w}/campaigns/{ca["id"]}', json={"budget": -1}
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f'/api/workspaces/{w}/campaigns/{ca["id"]}',
            json={"start_date": "2027-01-01"},
        ).status_code
        == 422
    )
    next_round = post(client, w, f'campaigns/{ca["id"]}/next-round', {})
    revised = client.patch(
        f'/api/workspaces/{w}/campaigns/{next_round["id"]}', json={"budget": 20}
    )
    assert (
        revised.status_code == 200
        and revised.json()["previous_campaign_id"] == ca["id"]
    )


def test_plan_snapshot_and_audit_preserve_original_business_evidence(client):
    from app.models import Record

    w = register(client)
    k, ca, p, a = prepared(client, w)
    with client.app.state.sessions() as db:
        snapshot = db.get(Record, p["id"]).data["_source_snapshot"]
        assert snapshot["knowledge"][0]["content"] == k["content"]
        assert snapshot["campaign"]["id"] == ca["id"]
        assert snapshot["offering"]["price"] == 30
    response = client.patch(
        f'/api/workspaces/{w}/knowledge/{k["id"]}', json={"content": "修改后的资料"}
    )
    assert response.status_code == 200
    client.delete(f'/api/workspaces/{w}/knowledge/{k["id"]}')
    with client.app.state.sessions() as db:
        assert db.get(Record, p["id"]).data["_source_snapshot"] == snapshot
    updates = [
        x
        for x in client.get(f"/api/workspaces/{w}/audit").json()
        if x["entity_id"] == k["id"] and x["action"] == "update"
    ]
    assert updates[0]["details"]["before"]["content"] == k["content"]
    assert updates[0]["details"]["after"]["content"] == "修改后的资料"
    deletions = [
        x
        for x in client.get(f"/api/workspaces/{w}/audit").json()
        if x["entity_id"] == k["id"] and x["action"] == "delete"
    ]
    assert deletions[0]["details"]["before"]["content"] == "修改后的资料"


def test_invalid_generation_payload_finishes_task_as_failed(client, monkeypatch):
    import app.workflow as workflow

    w = register(client)
    k, ca, p, a = prepared(client, w)
    content = {**p["content"], "budget": [{"item": "超额", "amount": 999999}]}
    monkeypatch.setattr(
        workflow,
        "ai_call",
        lambda kind, ctx: {"generation_mode": "ai", "usage": {}, "content": content},
    )
    response = client.post(
        f'/api/workspaces/{w}/campaigns/{ca["id"]}/plans/generate', json={}
    )
    assert response.status_code == 502
    assert client.get(f"/api/workspaces/{w}/tasks").json()[0]["status"] == "failed"


@pytest.mark.parametrize("inserted_revenue,expected_status", [(10, 200), (900, 409)])
def test_import_rechecks_concurrent_external_id_payload_after_preview(
    client, monkeypatch, inserted_revenue, expected_status
):
    import app.routes_data as routes
    from app.schemas import MetricInput
    from app.workflow import create
    from app.metrics import dedupe

    w = register(client)
    ca = campaign(client, w)
    original_preview = routes.preview

    def preview_then_concurrent_insert(db, workspace_id, text):
        result = original_preview(db, workspace_id, text)
        assert not result["errors"]
        row = MetricInput.model_validate(
            {
                "campaign_id": ca["id"],
                "date": "2026-11-01",
                "channel": "微信",
                "source": "手工",
                "external_id": "concurrent-key",
                "attribution": "known",
                "revenue": inserted_revenue,
            }
        ).model_dump(mode="json")
        with client.app.state.sessions() as concurrent_db:
            create(concurrent_db, workspace_id, "metric", row, dedupe=dedupe(row))
            concurrent_db.commit()
        return result

    monkeypatch.setattr(routes, "preview", preview_then_concurrent_insert)
    csv = (
        "campaign_id,date,channel,source,external_id,attribution,revenue\n"
        f'{ca["id"]},2026-11-01,微信,手工,new-first-key,known,20\n'
        f'{ca["id"]},2026-11-01,微信,手工,concurrent-key,known,10\n'
    )
    response = client.post(f"/api/workspaces/{w}/metrics/import", json={"csv": csv})
    assert response.status_code == expected_status, response.text
    metrics = client.get(f"/api/workspaces/{w}/metrics").json()
    if expected_status == 409:
        assert len(metrics) == 1 and metrics[0]["revenue"] == 900
        assert "external_id" in response.json()["detail"]
    else:
        assert response.json() == {"imported": 1, "duplicates": 1}
        assert len(metrics) == 2
