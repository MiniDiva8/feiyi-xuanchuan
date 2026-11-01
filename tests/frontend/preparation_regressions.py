"""Preparation UI checks with mocked API; never writes merchant data."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def run():
    output = Path(__file__).resolve().parents[2] / '.artifacts' / 'preparation'
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1100})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        state = {'fail': False, 'ready': False}

        def api(route):
            url = route.request.url.split('/api', 1)[1]
            data = []
            status = 200
            if url == '/auth/me':
                data = {'user': {'id': 'u', 'name': '测试', 'email': 'qa@example.invalid'},
                        'workspaces': [{'id': 'w', 'name': '验收工坊', 'role': 'owner', 'description': ''}]}
            elif url.endswith('/overview'):
                data = {'stats': {'campaigns': 0, 'publications': 0}, 'trends': [],
                        'recent_campaigns': [], 'activity': [], 'connections': {'ai_configured': False}}
            elif url.endswith('/knowledge'):
                if state['fail']:
                    status, data = 503, {'detail': '测试读取失败'}
                elif state['ready']:
                    data = [{'id': 'k', 'confirmed': True, 'usage_scope': 'marketing'}]
            elif url.endswith('/offerings') and state['ready']:
                data = [{'id': 'o', 'kind': 'course', 'quantity': 8, 'conversion_url': 'https://example.org/book'}]
            route.fulfill(status=status, content_type='application/json', body=json.dumps(data))

        page.route('**/api/**', api)
        page.goto('http://127.0.0.1:8010')
        panel = page.locator('section').filter(has=page.get_by_role('heading', name='开始一次真实的营销活动'))
        expect(panel.get_by_role('button', name='下一步：确认宣传资料')).to_be_visible()
        expect(panel.get_by_text('去准备', exact=True)).to_have_count(4)
        page.screenshot(path=str(output / 'desktop.png'), full_page=True)
        page.set_viewport_size({'width': 375, 'height': 900})
        expect(panel.get_by_role('button', name='下一步：确认宣传资料')).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.screenshot(path=str(output / 'mobile.png'), full_page=True)

        state['fail'] = True
        page.reload()
        expect(page.get_by_text('无法读取准备情况：测试读取失败')).to_be_visible()
        expect(page.get_by_role('button', name='下一步：确认宣传资料')).to_have_count(0)
        state.update(fail=False, ready=True)
        page.get_by_role('button', name='重新检查').click()
        expect(panel.get_by_text('已具备', exact=True)).to_have_count(2)
        expect(panel.get_by_role('button', name='下一步：创建活动并审核内容')).to_be_visible()
        assert not errors, errors
        browser.close()
        print('PASS: empty workspace, desktop/mobile, failed read, retry and refreshed readiness')


if __name__ == '__main__':
    run()
