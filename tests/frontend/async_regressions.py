"""Focused UI regressions with mocked API: never writes the backend database.
Run after frontend build, with backend/static service already running:
python tests/frontend/async_regressions.py --base-url http://127.0.0.1:8011
"""
import argparse
import json
from playwright.sync_api import sync_playwright, expect, Error

def run(base_url):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            headless=True,
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        state = {"pending_upload": None, "saved": None}
        knowledge = [
            {"id": key, "title": "资料" + key, "content": "有来源的测试资料",
             "source": "浏览器回归测试", "usage_scope": "marketing",
             "confirmed": True, "kind": "fact", "created_at": "2026-10-31"}
            for key in ("A", "B")
        ]
        workspace = {"id": "w", "name": "异步回归测试", "description": "",
                     "role": "owner", "created_at": "2026-10-31"}
        campaigns = [
            {"id": key, "name": "活动" + key, "objective": "awareness",
             "audience": "测试", "start_date": "2026-10-31",
             "end_date": "2026-11-07", "budget": 0, "channels": ["小红书"],
             "notes": "", "status": "draft", "created_at": "2026-10-31"}
            for key in ("A", "B")
        ]
        def fulfill(route, data, status=200):
            route.fulfill(status=status, content_type="application/json",
                          body=json.dumps(data, ensure_ascii=False))
        def api(route):
            url = route.request.url.split("/api", 1)[1]
            if url == "/auth/me":
                return fulfill(route, {"user": {"id": "u", "name": "测试员",
                    "email": "test@example.invalid"}, "workspaces": [workspace]})
            if url.endswith("/overview"):
                return fulfill(route, {"stats": {}, "trends": [],
                    "recent_campaigns": [], "activity": [],
                    "connections": {"ai_configured": False, "publishing": "manual",
                                    "checkout": "external"}})
            if url.endswith("/knowledge"):
                return fulfill(route, knowledge)
            if "/knowledge/" in url and route.request.method == "PATCH":
                state["saved"] = route.request.post_data_json
                return fulfill(route, {**knowledge[1], **state["saved"]})
            if url.endswith("/files") and route.request.method == "POST":
                state["pending_upload"] = route
                return
            if url.endswith("/campaigns"):
                return fulfill(route, campaigns)
            if "/campaigns/B/" in url:
                return fulfill(route, {"detail": "活动B加载失败（回归测试）"}, 500)
            if url.endswith("/campaigns/A/assets"):
                return fulfill(route, [{
                    "id": "assetA", "campaign_id": "A", "plan_id": "planA",
                    "channel": "小红书", "kind": "copy", "version": 1,
                    "status": "approved", "title": "活动A的专属素材",
                    "body": "A", "content": {}, "checks": [],
                    "generation_mode": "template", "created_at": "2026-10-31"
                }])
            if url.endswith("/campaigns/A/plans"):
                return fulfill(route, [{"id": "planA", "version": 1,
                    "status": "approved", "content": {}, "generation_mode": "template"}])
            return fulfill(route, [])
        page.route("**/api/**", api)
        page.goto(base_url)
        page.get_by_role("button", name="品牌知识库", exact=True).click()
        page.get_by_role("button", name="编辑资料A", exact=True).click()
        dialog = page.get_by_role("dialog")
        dialog.locator('input[type="file"]').set_input_files(
            {"name": "record-A.txt", "mimeType": "text/plain", "buffer": b"record A"})
        expect(dialog.get_by_text("正在上传…", exact=True)).to_be_visible()
        assert state["pending_upload"] is not None
        dialog.get_by_role("button", name="取消", exact=True).click()
        page.get_by_role("button", name="编辑资料B", exact=True).click()
        try:
            fulfill(state["pending_upload"], {"id": "file-A", "name": "record-A.txt"})
        except Error:
            pass  # Aborting a canceled upload may already have closed its route.
        page.evaluate("() => new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
        dialog = page.get_by_role("dialog")
        expect(dialog.get_by_text("record-A.txt", exact=True)).to_have_count(0)
        dialog.get_by_role("button", name="保存", exact=True).click()
        expect(dialog).to_have_count(0)
        assert state["saved"] is not None and "file_id" not in state["saved"], state["saved"]
        print("PASS: canceled delayed attachment cannot attach to another edit session")
        page.get_by_role("button", name="审核与发布", exact=True).click()
        register = page.get_by_role("button", name="登记已发布作品", exact=True)
        expect(register).to_be_enabled()
        page.get_by_role("combobox", name="选择发布活动").select_option("B")
        expect(page.get_by_text("活动B加载失败（回归测试）", exact=True)).to_be_visible()
        expect(register).to_be_disabled()
        expect(page.get_by_role("dialog")).to_have_count(0)
        expect(page.get_by_text("活动A的专属素材", exact=True)).to_have_count(0)
        print("PASS: failed campaign switch clears eligibility and prevents stale registration")
        browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8011")
    run(parser.parse_args().base_url)
