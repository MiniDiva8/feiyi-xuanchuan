"""Real UI layout acceptance on an explicitly isolated local QA service.

Creates synthetic 界面验收 data only. No external publishing, provider calls or
external navigation. Run with the project .venv Python and an isolated :8011 API.
"""
import argparse
import base64
from datetime import date, timedelta
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from uuid import uuid4

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".artifacts" / "marketing-workspace"
sys.stdout.reconfigure(encoding="utf-8")


def run(base, focused_previews=False):
    parsed = urlsplit(base)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost") or parsed.port != 8011:
        raise ValueError("Use the explicitly isolated local QA API on port 8011.")
    OUT.mkdir(parents=True, exist_ok=True)
    result_path = OUT / ("result-overview.json" if focused_previews else "result.json")
    report = {"passed": False, "data": "synthetic 界面验收 only; no model calls or actual publishing", "cases": [], "page_errors": [], "external_requests": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="zh-CN", timezone_id="Asia/Shanghai", accept_downloads=True)

        def local_only(route):
            url = urlsplit(route.request.url)
            if url.scheme in ("http", "https") and url.hostname not in ("127.0.0.1", "localhost"):
                report["external_requests"].append(url.hostname)
                return route.abort()
            route.continue_()

        context.route("**/*", local_only)
        page = context.new_page()
        page.set_default_timeout(10000)
        page.on("pageerror", lambda error: report["page_errors"].append(str(error)))

        def post(path, data, multipart=False):
            kwargs = {"multipart" if multipart else "data": data}
            response = context.request.post(base + "/api" + path, **kwargs)
            assert response.ok, (path, response.status, response.text())
            return response.json()

        def case(name, action):
            try:
                action()
                report["cases"].append({"name": name, "passed": True})
                print("PASS " + name, flush=True)
            except Exception as error:
                report["cases"].append({"name": name, "passed": False, "error": str(error)})
                print("FAIL " + name + ": " + str(error), flush=True)
                page.screenshot(path=str(OUT / (re.sub(r"[^a-zA-Z0-9_-]", "-", name) + "-failure.png")), full_page=True, animations="disabled")
            finally:
                result_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        def settled():
            page.wait_for_load_state("networkidle")
            expect(page.locator("main h1")).to_be_visible()
            expect(page.locator(".loading")).to_have_count(0)
            expect(page.get_by_text("正在检查准备情况…", exact=True)).to_have_count(0)

        def open_page(route, tab=None):
            page.goto(base + "/#/workspaces/" + workspace_id + "/" + route)
            settled()
            if tab:
                page.get_by_role("button", name=re.compile("^" + tab)).click()
                settled()
            if page.locator(".sidebar.open").count():
                page.get_by_role("button", name="关闭导航", exact=True).click()
            if page.viewport_size["width"] == 375:
                page.wait_for_function("document.querySelector('.sidebar').getBoundingClientRect().right <= 0")

        def no_overflow():
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Root horizontal overflow"

        def reachable(target):
            expect(target).to_be_visible()
            target.scroll_into_view_if_needed()
            box = target.bounding_box()
            assert box and box["x"] >= -1 and box["x"] + box["width"] <= page.viewport_size["width"] + 1, "Control exceeds viewport width"
            assert box["y"] >= -1 and box["y"] + box["height"] <= page.viewport_size["height"] + 1, "Control cannot scroll into viewport"

        def snapshot(name, full_page=True):
            page.evaluate("window.scrollTo(0,0)")
            page.screenshot(path=str(OUT / (name + ".png")), full_page=full_page, animations="disabled")

        def overview_geometry(fresh=False):
            current = page.locator(".current-panel").bounding_box()
            preparation = page.locator(".preparation-panel").bounding_box()
            recent = page.locator(".recent-panel").bounding_box()
            metrics = page.locator("main .metrics-grid").bounding_box()
            assert current and preparation and recent and metrics
            assert current["y"] + current["height"] <= preparation["y"] + 1
            assert preparation["y"] + preparation["height"] <= recent["y"] + 1
            assert recent["y"] + recent["height"] <= metrics["y"] + 1
            if fresh:
                title = page.get_by_role("heading", name="开始一次真实的营销活动", exact=True).bounding_box()
                assert title and 0 <= title["y"] < page.viewport_size["height"], "Fresh merchant preparation must be visible in the initial mobile viewport"

        try:
            # Login and onboarding are captured before API seed creation.
            for width in (1440, 375):
                page.set_viewport_size({"width": width, "height": 1000})
                page.goto(base)
                expect(page.get_by_role("button", name="注册商家", exact=True)).to_be_visible()
                no_overflow()
                snapshot(f"login-{width}")

            session = post("/auth/register", {"name": "界面验收员", "email": uuid4().hex + "@ui-qa.invalid", "password": "Synthetic-UI-QA-2026!", "workspace_name": "界面验收 · 合成手作工坊"})
            workspace_id = session["workspaces"][0]["id"]
            api = "/workspaces/" + workspace_id
            settings_response = context.request.get(base + "/api" + api + "/settings")
            assert settings_response.ok, ("QA settings read", settings_response.status, settings_response.text())
            settings = settings_response.json()
            assert settings["ai_configured"] is False, "QA must have no real AI provider key before generation."
            # API registration updates the cookie. Reload the already-open login
            # document so its auth effect reads that new session before hash nav.
            page.reload()
            for width in (1440, 375):
                def fresh(width=width):
                    page.set_viewport_size({"width": width, "height": 1000})
                    open_page("overview")
                    no_overflow()
                    if width == 375:
                        overview_geometry(fresh=True)
                    expect(page.get_by_role("button", name="下一步：确认宣传资料", exact=True)).to_be_visible()
                    snapshot(f"empty-overview-{width}")
                case(f"empty-overview-{width}", fresh)

            today = date.today()
            yesterday = today - timedelta(days=1)
            photo = page.evaluate("""() => { const c=document.createElement('canvas'); c.width=900; c.height=600; const x=c.getContext('2d'); x.fillStyle='#eee9f6';x.fillRect(0,0,900,600);x.fillStyle='#5142a0';x.fillRect(220,120,460,360);x.fillStyle='white';x.font='48px sans-serif';x.fillText('UI QA PHOTO',285,320);return c.toDataURL('image/png').split(',')[1]; }""")
            upload = post(api + "/files", {"file": {"name": "synthetic-ui-photo.png", "mimeType": "image/png", "buffer": base64.b64decode(photo)}}, multipart=True)
            post(api + "/knowledge", {"title": "界面验收 · 手作商品与课程说明", "kind": "fact", "content": "仅界面验收合成资料：棉布手作书签售价29元；剪纸体验课程时长90分钟，价格59元。不代表真实商家或文化认证。", "source": "界面验收合成商家台账", "usage_scope": "marketing", "confirmed": True, "file_id": upload["id"]})
            product = post(api + "/offerings", {"kind": "product", "name": "界面验收 · 棉布书签", "description": "用于检查标题、价格、库存和真实链接字段；非在售商品。", "price": 29, "quantity": 20, "location": "合成测试地址", "delivery": "合成测试履约说明", "conversion_url": "https://example.com/ui-qa-product"})
            post(api + "/offerings", {"kind": "course", "name": "界面验收 · 90分钟剪纸体验", "description": "仅测试课程展示，不开放实际报名。", "price": 59, "quantity": 12, "location": "合成测试教室", "delivery": "仅测试，无真实履约", "conversion_url": "https://example.com/ui-qa-course"})
            campaign = post(api + "/campaigns", {"name": "界面验收 · 手作产品推广", "objective": "sales", "offering_id": product["id"], "audience": "喜欢手作的本地青年与大学生（合成测试）", "start_date": today.isoformat(), "end_date": (today + timedelta(days=7)).isoformat(), "budget": 300, "channels": ["小红书", "微信公众号"], "notes": "仅用于界面验收；数据、照片和内容均为合成测试，不代表实际营销效果。"})
            campaign_route = "campaigns/" + campaign["id"]
            plan = post(api + "/campaigns/" + campaign["id"] + "/plans/generate", {})
            assert plan["generation_mode"] == "template"
            post(api + "/plans/" + plan["id"] + "/approve", {})
            assets = {}
            for kind in ("copy", "script", "poster"):
                assets[kind] = post(api + "/campaigns/" + campaign["id"] + "/assets/generate", {"plan_id": plan["id"], "kind": kind, "channel": "小红书"})
                assert assets[kind]["generation_mode"] == "template"
            post(api + "/assets/" + assets["copy"]["id"] + "/approve", {})
            post(api + "/assets/" + assets["poster"]["id"] + "/revise", {"title": "界面验收 · 手作产品海报", "body": assets["poster"]["body"], "poster_template": "minimal", "poster_image_id": upload["id"], "photo_confirmed": True})
            for day, impressions, revenue in ((yesterday, 1200, 87), (today, 950, 58)):
                post(api + "/metrics", {"campaign_id": campaign["id"], "date": day.isoformat(), "channel": "小红书", "source": "界面验收合成台账", "attribution": "unknown", "external_id": "ui-qa-" + day.isoformat(), "impressions": impressions, "interactions": 24, "orders": 2, "revenue": revenue, "spend": 20})
            review = post(api + "/campaigns/" + campaign["id"] + "/reviews/generate", {})
            assert review["generation_mode"] == "template"
            account = post(api + "/channels", {"platform": "channels", "name": "界面验收 · 手作视频号", "account_id": "synthetic-ui-qa", "profile_url": ""})
            for day, followers in ((yesterday, 100), (today, 108)):
                post(api + "/channels/" + account["id"] + "/snapshots", {"date": day.isoformat(), "source": "界面验收合成快照", "followers": followers, "views": 2500})
            print("PASS synthetic seed (template only, no publication)", flush=True)
            # Seed operations are external to React: reload so even an unchanged
            # overview hash reads the new records instead of the fresh empty state.
            page.reload()
            settled()

            views = [("overview", "overview", None), ("knowledge", "knowledge", None), ("offerings", "offerings", None), ("campaigns", "campaigns", None), ("publications", "publications", None), ("channels", "channels", None), ("analytics", "analytics", None), ("settings", "settings", None), ("studio-plan", campaign_route, None), ("studio-assets", campaign_route, "传播素材"), ("studio-review", campaign_route, "复盘与下一轮")]
            if focused_previews:
                views = [view for view in views if view[0] == "overview"]
            for width in (1440, 768, 375):
                page.set_viewport_size({"width": width, "height": 1000})
                for name, route, tab in views:
                    def check(name=name, route=route, tab=tab, width=width):
                        open_page(route, tab)
                        no_overflow()
                        for button in page.locator("main button:visible:enabled").all()[:3]:
                            reachable(button)
                        if name == "overview":
                            expect(page.locator(".current-panel")).to_contain_text(campaign["name"])
                            expect(page.locator(".overview-alert")).to_be_visible()
                            assert int(re.search(r"\d+", page.locator(".overview-alert strong").inner_text()).group()) > 0
                            if width == 375:
                                overview_geometry()
                        snapshot(f"{name}-{width}")
                    case(f"{name}-{width}", check)

            modal_specs = [
                ("knowledge-new", "knowledge", None, "新增资料"),
                ("offering-new", "offerings", None, "新增产品 / 课程"),
                ("campaign-new", "campaigns", None, "创建营销活动"),
                ("campaign-edit", campaign_route, None, "编辑活动简报"),
                ("asset-generate", campaign_route, "传播素材", "生成传播素材"),
                ("asset-edit", campaign_route, "传播素材", "编辑新版本"),
                ("poster", campaign_route, "传播素材", "照片与海报设计"),
                ("channel-new", "channels", None, "添加渠道账号"),
                ("channel-snapshot", "channels", None, "记录运营数据"),
                ("metric-new", "analytics", None, "录入指标"),
                ("metric-csv", "analytics", None, "导入 CSV"),
            ]
            if focused_previews:
                modal_specs = []
            for width in (768, 375):
                page.set_viewport_size({"width": width, "height": 1000})
                for name, route, tab, button_name in modal_specs:
                    def check_modal(name=name, route=route, tab=tab, button_name=button_name, width=width):
                        open_page(route, tab)
                        trigger = page.get_by_role("button", name=button_name, exact=True).first
                        reachable(trigger)
                        trigger.click()
                        dialog = page.get_by_role("dialog")
                        expect(dialog).to_be_visible()
                        box = dialog.bounding_box()
                        assert box and box["x"] >= -1 and box["y"] >= -1
                        assert box["x"] + box["width"] <= width + 1
                        assert box["y"] + box["height"] <= 1001
                        assert dialog.evaluate("el=>el.scrollWidth<=el.clientWidth+1"), "Dialog internal horizontal overflow"
                        unlabelled = dialog.locator("input:visible, textarea:visible, select:visible").evaluate_all("els=>els.filter(el=>!el.labels?.length&&!el.getAttribute('aria-label')&&!el.getAttribute('aria-labelledby')).map(el=>el.name||el.type)")
                        assert not unlabelled, ("Unlabelled controls", unlabelled)
                        if name == "asset-edit":
                            expect(dialog.locator("[name=body]")).to_be_visible()
                        if name == "poster":
                            native = dialog.get_by_role("combobox", name="海报模板", exact=True)
                            before = context.request.get(base + "/api" + api + "/campaigns/" + campaign["id"] + "/assets").json()
                            dialog.get_by_role("button", name="选择暖陶模板", exact=True).click()
                            expect(native).to_have_value("warm")
                            expect(dialog.get_by_role("button", name="选择暖陶模板", exact=True)).to_have_attribute("aria-pressed", "true")
                            native.select_option("minimal")
                            expect(dialog.get_by_role("button", name="选择留白模板", exact=True)).to_have_attribute("aria-pressed", "true")
                            after = context.request.get(base + "/api" + api + "/campaigns/" + campaign["id"] + "/assets").json()
                            assert len(before) == len(after), "Template selection must not save or submit a form"
                            expect(dialog.get_by_role("checkbox", name="我确认照片真实，并有权将其用于本次宣传")).to_be_checked()
                        for button in dialog.locator("button:visible:enabled").all():
                            reachable(button)
                        dialog.evaluate("el=>{el.scrollTop=0;for(const child of el.querySelectorAll('*'))if(child.scrollHeight>child.clientHeight)child.scrollTop=0;}")
                        snapshot(f"modal-{name}-{width}", full_page=False)
                        page.keyboard.press("Escape")
                        expect(page.get_by_role("dialog")).to_have_count(0)
                    case(f"modal-{name}-{width}", check_modal)
            def pending_navigation():
                open_page("overview")
                page.locator(".overview-alert button").click()
                expect(page.locator("main h1")).to_have_text("营销活动")
                expect(page.locator(".campaign-card").filter(has_text=campaign["name"])).to_be_visible()
            case("pending-review-activity-selection", pending_navigation)
            # Stable viewport exports for human inspection and delivery previews.
            page.set_viewport_size({"width": 1440, "height": 1000})
            open_page("overview")
            snapshot("overview-desktop", full_page=False)
            open_page(campaign_route, "传播素材")
            page.locator(".content-review-card").first.scroll_into_view_if_needed()
            page.screenshot(path=str(OUT / "content-desktop.png"), full_page=False, animations="disabled")
            page.get_by_role("button", name="照片与海报设计", exact=True).first.click()
            dialog = page.get_by_role("dialog")
            dialog.get_by_role("button", name="生成预览", exact=True).click()
            expect(dialog.locator(".poster-preview img")).to_be_visible()
            dialog.evaluate("el=>{el.scrollTop=0;for(const child of el.querySelectorAll('*'))if(child.scrollHeight>child.clientHeight)child.scrollTop=0;}")
            page.screenshot(path=str(OUT / "poster-desktop.png"), full_page=False, animations="disabled")
            page.keyboard.press("Escape")
            page.set_viewport_size({"width": 375, "height": 1000})
            open_page("overview")
            snapshot("overview-mobile", full_page=False)
            assert not report["page_errors"], report["page_errors"]
            assert not report["external_requests"], report["external_requests"]
            report["passed"] = all(item["passed"] for item in report["cases"])
        except Exception as error:
            report["fatal_error"] = str(error)
            print("FATAL " + str(error), flush=True)
        finally:
            result_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            browser.close()
    print(json.dumps({"passed": report["passed"], "cases": len(report["cases"]), "failures": [item["name"] for item in report["cases"] if not item["passed"]], "page_errors": report["page_errors"]}, ensure_ascii=False), flush=True)
    return report["passed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8011")
    parser.add_argument("--focused-previews", action="store_true", help="Recheck overview data/geometry and export delivery viewport previews only.")
    args = parser.parse_args()
    raise SystemExit(0 if run(args.base_url.rstrip("/"), args.focused_previews) else 1)
