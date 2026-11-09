"""Run against isolated QA service on 8011, never the normal merchant database."""
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect


def run():
    output = Path('.artifacts/channels-browser')
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        base = 'http://127.0.0.1:8011'
        response = context.request.post(base + '/api/auth/register', data={
            'name': '验收员', 'email': uuid4().hex + '@qa.invalid',
            'password': 'Channels-QA-2026!', 'workspace_name': '渠道账号验收'})
        assert response.ok, response.text()
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(base)
        page.get_by_role('button', name='渠道账号', exact=True).click()
        expect(page.get_by_text('添加第一个商家账号', exact=True)).to_be_visible()
        page.get_by_role('button', name='添加渠道账号').click()
        dialog = page.get_by_role('dialog')
        dialog.locator('[name=platform]').select_option('channels')
        dialog.locator('[name=name]').fill('手艺体验视频号')
        dialog.locator('[name=account_id]').fill('craft-test')
        dialog.get_by_role('button', name='保存账号', exact=True).click()
        expect(page.get_by_role('heading', name='手艺体验视频号')).to_be_visible()
        for day, followers in [('2026-10-30', '100'), ('2026-10-31', '110')]:
            page.get_by_role('button', name='记录运营数据', exact=True).click()
            dialog = page.get_by_role('dialog')
            dialog.locator('[name=date]').fill(day)
            dialog.locator('[name=source]').fill('验收模拟后台数据')
            dialog.locator('[name=followers]').fill(followers)
            dialog.locator('[name=views]').fill('2500')
            dialog.get_by_role('button', name='保存数据快照', exact=True).click()
            expect(page.get_by_role('dialog')).to_have_count(0)
            history = page.locator('details.channel-history')
            expect(history.locator('summary')).to_be_visible()
            if not history.evaluate('(element) => element.open'):
                history.locator('summary').click()
            expect(page.get_by_role('cell', name=day, exact=True)).to_be_visible()
        expect(page.get_by_text('粉丝变化：+10', exact=False)).to_be_visible()
        expect(page.get_by_text('手动记录 · 未自动同步', exact=True)).to_be_visible()
        expect(page.get_by_role('cell', name='未提供', exact=True)).to_have_count(8)
        page.screenshot(path=str(output / 'desktop.png'), full_page=True)
        page.set_viewport_size({'width': 375, 'height': 900})
        page.wait_for_timeout(350)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(output / 'mobile.png'), full_page=True, animations='disabled')
        assert not errors, errors
        browser.close()
        print('PASS channel creation, two snapshots, missing values, follower delta, mobile, no page errors')


if __name__ == '__main__':
    run()
