"""Browser acceptance against a disposable QA database, never the normal user database.
Run an isolated API on 8011 with DATABASE_URL under .artifacts before invoking.
"""
import argparse
import json
import re
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '.artifacts' / 'platform-20261031'


def fill(container, values):
    for key, value in values.items():
        target = container.locator(f'[name="{key}"]')
        tag = target.evaluate('(e)=>e.tagName.toLowerCase()')
        if tag == 'select':
            target.select_option(str(value))
        elif isinstance(value, bool):
            target.set_checked(value)
        else:
            target.fill(str(value))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:8011')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    errors, steps = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', headless=True)
        context = browser.new_context(viewport={'width':1440,'height':1000}, device_scale_factor=1, accept_downloads=True, locale='zh-CN', timezone_id='Asia/Shanghai')
        page = context.new_page()
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.goto(args.base_url)
        page.get_by_role('button', name='注册商家', exact=True).wait_for()
        page.screenshot(path=str(OUT/'01-login-desktop.png'), full_page=True, animations="disabled")
        page.get_by_role('button', name='注册商家', exact=True).click()
        fill(page, {'name':'验收测试员', 'workspace_name':'验收测试 · 蓝染工坊', 'email':uuid4().hex+'@acceptance.invalid', 'password':'BrowserAcceptance-2026!'})
        page.get_by_role('button', name='创建商家空间', exact=True).click()
        page.get_by_role('button', name='品牌知识库', exact=True).wait_for()
        expect(page.get_by_role('combobox', name='切换商家空间')).to_contain_text('验收测试 · 蓝染工坊')
        steps.append('UI registration and empty real workspace')
        session = context.request.get(args.base_url+'/api/auth/me').json()
        workspace_id = session['workspaces'][0]['id']
        api = args.base_url+'/api/workspaces/'+workspace_id
        page.get_by_role('button', name='品牌知识库', exact=True).click()
        page.get_by_role('button', name='新增资料', exact=True).click()
        dialog = page.get_by_role('dialog')
        fill(dialog, {'title':'验收用商家产品说明','kind':'fact','content':'蓝染棉布书签，售价29元，采用棉布手工制作。这是界面验收用模拟资料。','source':'验收测试资料，非真实商家业绩','usage_scope':'marketing','confirmed':True})
        dialog.get_by_role('button', name='保存', exact=True).click()
        expect(page.get_by_role('heading', name='验收用商家产品说明')).to_be_visible()
        steps.append('Knowledge UI creation, source and marketing confirmation')
        page.get_by_role('button', name='产品与课程', exact=True).click()
        page.get_by_role('button', name='新增产品 / 课程', exact=True).click()
        dialog = page.get_by_role('dialog')
        fill(dialog, {'kind':'product','name':'验收用蓝染书签','description':'验收用手作产品，非实际在售商品','price':29,'quantity':20,'location':'济南','delivery':'三个工作日发货','conversion_url':'https://example.com/qa-bookmark'})
        dialog.get_by_role('button', name='保存', exact=True).click()
        expect(page.get_by_role('heading', name='验收用蓝染书签')).to_be_visible()
        offering_id = context.request.get(api+'/offerings').json()[0]['id']
        steps.append('Product catalog UI with price, stock and external conversion entry')
        page.get_by_role('button', name='营销活动', exact=True).click()
        page.get_by_role('button', name='创建营销活动', exact=True).click()
        dialog = page.get_by_role('dialog')
        fill(dialog, {'name':'验收测试 · 秋日蓝染推广','objective':'sales','offering_id':offering_id,'audience':'喜欢手作的大学生','start_date':'2026-10-31','end_date':'2026-11-07','budget':300,'channels':'小红书，微信公众号','notes':'全程为模拟验收，不代表真实商家或经营效果。'})
        dialog.get_by_role('button', name='创建并进入工作室', exact=True).click()
        page.get_by_role('button', name='生成策划草稿', exact=True).click()
        dialog = page.get_by_role('dialog')
        dialog.get_by_role('button', name='生成草稿', exact=True).click()
        page.get_by_role('button', name='批准此版本', exact=True).wait_for()
        expect(page.get_by_text('模板草稿', exact=True).first).to_be_visible()
        page.get_by_role('button', name='批准此版本', exact=True).click()
        expect(page.get_by_role('button', name='批准此版本', exact=True)).to_be_disabled()
        steps.append('Plan generation is explicitly template mode; concrete-version merchant approval')
        page.screenshot(path=str(OUT/'02-plan-desktop.png'), full_page=True, animations="disabled")
        page.get_by_role('button', name=re.compile('^传播素材')).click()
        page.get_by_role('button', name='生成传播素材', exact=True).click()
        dialog = page.get_by_role('dialog')
        fill(dialog, {'channel':'小红书','kind':'poster','instructions':'简洁清楚，保留购买入口。'})
        dialog.get_by_role('button', name='生成草稿', exact=True).click()
        page.get_by_role('button', name='批准', exact=True).wait_for()
        expect(page.get_by_role('button', name='PNG', exact=True)).to_be_disabled()
        page.get_by_role('button', name='批准', exact=True).click()
        expect(page.get_by_role('button', name='PNG', exact=True)).to_be_enabled()
        with page.expect_download() as download_info:
            page.get_by_role('button', name='PNG', exact=True).click()
        download = download_info.value
        download.save_as(str(OUT/'approved-poster.png'))
        assert (OUT/'approved-poster.png').stat().st_size > 1000
        page.screenshot(path=str(OUT/'03-assets-desktop.png'), full_page=True, animations="disabled")
        steps.append('Poster review gate and real PNG download')
        campaign_id = context.request.get(api+'/campaigns').json()[0]['id']
        page.get_by_role('button', name='审核与发布', exact=True).click()
        page.get_by_role('button', name=re.compile('登记')).first.click()
        dialog = page.get_by_role('dialog')
        fill(dialog, {'channel':'小红书','url':'https://example.com/qa-work','published_at':'2026-10-31T18:30','external_id':'qa-work-1'})
        dialog.get_by_role('button', name='保存发布档案', exact=True).click()
        expect(page.locator('a[href="https://example.com/qa-work"]')).to_be_visible()
        steps.append('Manual publication record tied to approved versions')
        page.get_by_role('button', name='数据与复盘', exact=True).click()
        page.get_by_role('button', name='录入指标', exact=True).click()
        dialog = page.get_by_role('dialog')
        fill(dialog, {'date':'2026-10-31','channel':'小红书','source':'模拟验收台账','attribution':'unknown','external_id':'qa-manual-1','impressions':1000,'interactions':28,'orders':3,'revenue':87,'spend':10})
        dialog.get_by_role('button', name='保存', exact=True).click()
        expect(page.get_by_role('cell', name=re.compile('模拟验收台账'))).to_be_visible()
        page.get_by_role('button', name='导入 CSV', exact=True).click()
        dialog = page.get_by_role('dialog')
        csv = f'campaign_id,date,channel,source,external_id,attribution,impressions,orders,revenue,spend\n{campaign_id},2026-11-01,小红书,模拟CSV台账,qa-csv-1,known,1200,2,58,10\n'
        dialog.get_by_role('textbox', name='CSV 内容').fill(csv)
        dialog.get_by_role('button', name='运行导入预检', exact=True).click()
        expect(dialog.get_by_text('0 个错误', exact=True)).to_be_visible()
        dialog.get_by_role('button', name='确认导入', exact=True).click()
        expect(page.get_by_role('cell', name=re.compile('模拟CSV台账'))).to_be_visible()
        steps.append('Manual metrics and previewed transactional CSV import with unknown attribution shown')
        page.screenshot(path=str(OUT/'04-analytics-desktop.png'), full_page=True, animations="disabled")
        page.get_by_role('button', name='营销活动', exact=True).click()
        page.locator('.campaign-card').filter(has_text='验收测试 · 秋日蓝染推广').click()
        page.get_by_role('button', name='复盘与下一轮', exact=True).click()
        page.get_by_role('button', name='生成复盘', exact=True).click()
        expect(page.get_by_text('观察事实', exact=True)).to_be_visible()
        expect(page.get_by_text('原因假设', exact=True)).to_be_visible()
        page.screenshot(path=str(OUT/'05-review-desktop.png'), full_page=True, animations="disabled")
        page.get_by_role('button', name='创建下一轮活动', exact=True).click()
        expect(page.get_by_role('button', name='生成策划草稿', exact=True)).to_be_visible()
        steps.append('Evidence-separated review and new round without inherited approval')
        page.get_by_role('button', name='经营概览', exact=True).click()
        page.screenshot(path=str(OUT/'06-overview-desktop.png'), full_page=True, animations="disabled")
        for width in (375,768):
            page.set_viewport_size({'width':width,'height':900})
            if width <= 760:
                page.get_by_role('button', name='打开导航', exact=True).wait_for()
            if width <= 760:
                page.wait_for_function("document.querySelector('.sidebar').getBoundingClientRect().right <= 0")
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), f'horizontal overflow {width}'
            page.screenshot(path=str(OUT/f'07-overview-{width}.png'), full_page=True, animations="disabled")
        page.set_viewport_size({'width':375,'height':900})
        page.get_by_role('button', name='打开导航', exact=True).click()
        page.get_by_role('button', name='商家设置', exact=True).click()
        expect(page.locator('main h1')).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        steps.append('375px and 768px responsive layout; mobile navigation and settings')
        page.set_viewport_size({'width':1440,'height':1000})
        page.reload()
        page.get_by_role('button', name='经营概览', exact=True).wait_for()
        steps.append('Reload preserves server session and business data')
        assert not errors, errors
        browser.close()
    report = {'passed':True,'steps':steps,'page_errors':errors,'test_data':'Disposable QA database, synthetic acceptance data only. No real publishing, revenue or model call.'}
    (OUT/'browser-acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    main()
