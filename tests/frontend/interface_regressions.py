"""Interface regressions. All APIs mocked; no merchant database/model calls.
Run against production service or Vite to cover React StrictMode too.
"""
import argparse, json, re
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

def run(base, case):
    out = Path('.artifacts/frontend-refresh-20261101')
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        ctx = browser.new_context(viewport={'width': 1440, 'height': 1000}, locale='zh-CN')
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        workspace = {'id': 'w', 'name': '青山工坊', 'description': '真实工艺与品牌档案', 'role': 'owner', 'created_at': '2026-11-01'}
        campaign = {'id': 'campaign-a', 'name': '周末手艺体验', 'objective': 'awareness', 'audience': '本地家庭', 'start_date': '2026-11-01', 'end_date': '2026-11-07', 'budget': 500, 'channels': ['小红书'], 'status': 'draft', 'created_at': '2026-11-01'}
        asset = {'id': 'asset-a', 'plan_id': 'p', 'kind': 'poster', 'channel': '小红书', 'title': '一堂手作课', 'body': '认识真实的手艺', 'content': {}, 'status': 'draft', 'version': 1, 'generation_mode': 'template', 'checks': []}
        account = {'id': 'ch', 'platform': 'channels', 'name': '青山工坊视频号', 'account_id': 'craft-1', 'profile_url': '', 'snapshots': [], 'latest': None, 'follower_change': None}

        def api(route):
            url = route.request.url.split('/api', 1)[1]
            data = []
            if url == '/auth/me':
                data = {'user': {'id': 'u', 'name': '手艺人', 'email': 'test@qa.invalid'}, 'workspaces': [workspace, {**workspace, 'id': 'w2', 'name': '第二工坊'}]}
            elif url.endswith('/overview'):
                data = {'stats': {'impressions': 0, 'revenue': 0, 'campaigns': 1, 'pending_review': 1, 'orders': 0, 'registrations': 0, 'publications': 0}, 'activity': [], 'recent_campaigns': [campaign], 'connections': {'ai_configured': False}}
            elif '/analytics' in url:
                data = {'stats': {}, 'trends': [], 'channels': [], 'records': 0}
            elif url.endswith('/knowledge'):
                data = [{'id': 'k', 'title': '蓝染工艺', 'content': '真实的工艺步骤', 'source': '商家工艺手册', 'usage_scope': 'marketing', 'confirmed': True, 'kind': 'fact', 'created_at': '2026-11-01'}]
            elif url.endswith('/campaigns'):
                data = [campaign]
            elif url.endswith('/campaigns/campaign-a'):
                data = campaign
            elif url.endswith('/plans'):
                data = [{'id': 'p', 'status': 'approved', 'version': 1, 'content': {'theme': '周末体验', 'budget': []}, 'generation_mode': 'template', 'created_at': '2026-11-01'}]
            elif url.endswith('/assets'):
                data = [asset]
            elif url.endswith('/channels'):
                data = [account]
            elif url.endswith('/files') and route.request.method == 'POST':
                data = {'id': 'photo-1'}
            elif url.endswith('/preview'):
                return route.fulfill(content_type='image/svg+xml', body='<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1440"><rect width="1080" height="1440" fill="#e6ebdc"/></svg>')
            route.fulfill(content_type='application/json', body=json.dumps(data, ensure_ascii=False))
        page.route('**/api/**', api)
        if case == 'navigation':
            page.goto(base + '/#/knowledge')
            expect(page.locator('main h1')).to_have_text('品牌知识库')
            skip = page.get_by_role('link', name='跳至主要内容')
            skip.focus()
            page.keyboard.press('Enter')
            expect(page).to_have_url(re.compile('/#/knowledge$'))
            assert page.evaluate('document.activeElement.id') == 'main-content', 'Skip link must focus main without changing the page'
            page.get_by_role('button', name='渠道账号', exact=True).click()
            page.go_back()
            expect(page.locator('main h1')).to_have_text('品牌知识库')
            page.go_forward()
            expect(page.locator('main h1')).to_have_text('渠道账号与运营记录')
            page.keyboard.press('Control+k')
            dialog = page.get_by_role('dialog', name='快捷导航')
            dialog.get_by_role('textbox').fill('海报')
            expect(dialog.get_by_role('button', name=re.compile('营销活动'))).to_be_visible()
            dialog.get_by_role('button', name=re.compile('营销活动')).click()
            expect(page.locator('main h1')).to_have_text('营销活动')
            page.goto(base + '/#/campaigns/campaign-a')
            expect(page.locator('main h1')).to_have_text(campaign['name'])
            page.reload()
            expect(page.locator('main h1')).to_have_text(campaign['name'])
            for width in [1440, 768, 375]:
                page.set_viewport_size({'width': width, 'height': 960})
                for name in ['overview', 'knowledge', 'offerings', 'campaigns', 'publications', 'channels', 'analytics', 'settings']:
                    page.goto(base + '/#/' + name)
                    page.locator('main h1').wait_for()
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), (width, name)
                page.screenshot(path=str(out / f'workspace-{width}.png'), full_page=True)
                page.goto(base + '/#/overview')
                page.locator('main h1').wait_for()
                page.screenshot(path=str(out / f'overview-{width}.png'), full_page=False)
            page.set_viewport_size({'width': 1440, 'height': 1000})
            page.goto(base + '/#/campaigns/new')
            expect(page.get_by_role('dialog', name='创建营销活动')).to_be_visible()
            page.get_by_role('button', name='取消', exact=True).click()
            expect(page).to_have_url(re.compile('/#/campaigns$'))
            page.goto(base + '/#/knowledge')
            page.get_by_label('切换商家空间').select_option('w2')
            expect(page.locator('main h1')).to_have_text('经营工作台')
            expect(page.locator('main')).to_contain_text('第二工坊')
        elif case == 'form-layout':
            entries = [('knowledge', '新增资料'), ('offerings', '新增产品 / 课程'), ('campaigns', '创建营销活动'), ('channels', '添加渠道账号'), ('channels', '记录运营数据'), ('analytics', '录入指标'), ('analytics', '导入 CSV'), ('settings', '添加成员')]
            for width in [768, 375]:
                page.set_viewport_size({'width': width, 'height': 900})
                for destination, label in entries:
                    page.goto(base + '/#/' + destination)
                    page.get_by_role('button', name=label, exact=True).click()
                    dialog = page.get_by_role('dialog')
                    expect(dialog).to_be_visible()
                    box = dialog.bounding_box()
                    assert box['x'] >= 0 and box['x'] + box['width'] <= width and (box['height'] <= 900), (width, label, box)
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), (width, label)
                    controls = dialog.locator('button:visible')
                    controls.last.scroll_into_view_if_needed()
                    expect(controls.last).to_be_visible()
                    page.keyboard.press('Escape')
                    expect(dialog).to_have_count(0)
        elif case == 'knowledge-search':
            page.goto(base + '/#/knowledge')
            page.get_by_label('搜索资料').fill('不存在的内容')
            expect(page.get_by_text('没有匹配的资料', exact=True)).to_be_visible()
            page.get_by_role('button', name='清空搜索').click()
            expect(page.get_by_role('heading', name='蓝染工艺', exact=True)).to_be_visible()
        elif case == 'channel-edit':
            page.goto(base + '/#/channels')
            page.get_by_role('button', name='编辑昵称与主页').click()
            dialog = page.get_by_role('dialog')
            expect(dialog.locator('[name=platform]')).to_have_count(0)
            expect(dialog.locator('[name=account_id]')).to_have_count(0)
            expect(dialog.get_by_label('账号昵称')).to_be_editable()
        else:
            page.goto(base + '/#/campaigns/campaign-a')
            page.get_by_role('button', name=re.compile('传播素材')).click()
            page.get_by_role('button', name='照片与海报设计').click()
            dialog = page.get_by_role('dialog')
            if case == 'poster-size':
                box = dialog.bounding_box()
                assert box['width'] >= 1000, box
                assert box['y'] >= 0 and box['height'] <= 1000, box
            else:
                dialog.get_by_label('上传海报照片').set_input_files({'name': 'photo.png', 'mimeType': 'image/png', 'buffer': b'test mocked upload'})
                expect(dialog.get_by_text('照片已附加，可重新选择')).to_be_visible(timeout=3500)
                dialog.get_by_role('checkbox').check()
                dialog.get_by_role('button', name='生成预览').click()
                expect(dialog.locator('.poster-preview img')).to_be_visible()
        assert not errors, errors
        browser.close()
        print('PASS', case, base)
if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--base-url', default='http://127.0.0.1:8011')
    a.add_argument('--case', default='navigation', choices=['navigation', 'channel-edit', 'poster-size', 'poster-upload', 'knowledge-search', 'form-layout'])
    args = a.parse_args()
    run(args.base_url, args.case)
