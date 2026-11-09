"""A workspace-wide reminder must let the merchant select the correct activity."""
import argparse
import json
from playwright.sync_api import sync_playwright, expect


def run(base_url):
    newer = dict(id="new", name="最新活动 · 没有待审内容", objective="awareness",
                 audience="本地顾客", channels=["小红书"], start_date="2026-11-08",
                 end_date="2026-11-15", budget=0, status="draft", notes="")
    older = {**newer, "id": "old", "name": "另一活动 · 策划等待审核"}
    draft = dict(id="p", version=1, status="draft", generation_mode="template",
                 created_at="2026-11-08", content=dict(
                     theme="另一活动的待审策划", summary="真实资料形成的待审草稿",
                     audience="本地顾客", channels=[], schedule=[], budget=[],
                     warnings=[], evidence=[]))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page()
        page.set_default_timeout(5000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def api(route):
            url = route.request.url.split("/api", 1)[1]
            data = []
            if url == "/auth/me":
                data = {"user": {"id": "u", "name": "测试", "email": "qa@example.invalid"},
                        "workspaces": [{"id": "w", "name": "待审入口验收", "role": "owner"}]}
            elif url.endswith("/overview"):
                data = {"stats": {"campaigns": 2, "pending_review": 1},
                        "recent_campaigns": [newer, older], "activity": [],
                        "trends": [], "connections": {"ai_configured": False}}
            elif url.endswith("/campaigns"):
                data = [newer, older]
            elif url.endswith("/campaigns/old"):
                data = older
            elif url.endswith("/campaigns/old/plans"):
                data = [draft]
            route.fulfill(content_type="application/json",
                          body=json.dumps(data, ensure_ascii=False))

        page.route("**/api/**", api)
        page.goto(base_url)
        expect(page.locator(".overview-alert")).to_contain_text("1 个版本")
        page.locator(".overview-alert button").click()
        expect(page.locator(".campaign-card")).to_have_count(2)
        page.locator(".campaign-card").filter(has_text=older["name"]).click()
        expect(page.get_by_role("heading", name=draft["content"]["theme"])).to_be_visible()
        expect(page.get_by_role("button", name="批准此版本", exact=True)).to_be_enabled()
        assert not errors, errors
        browser.close()
    print("PASS workspace reminder opens activity selection and reaches another activity's pending plan")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8011")
    run(parser.parse_args().base_url)
