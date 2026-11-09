import json, re
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect
out=Path('.artifacts/photo-browser'); out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(channel='msedge',headless=True)
 ctx=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
 base='http://127.0.0.1:8011'
 def post(path,data):
  r=ctx.request.post(base+'/api'+path,data=data)
  assert r.ok, (path,r.status,r.text())
  return r.json()
 session=post('/auth/register',{'name':'海报验收','email':uuid4().hex+'@qa.invalid','password':'Poster-QA-2026!','workspace_name':'实拍海报验收'})
 w=session['workspaces'][0]['id']; api='/workspaces/'+w
 post(api+'/knowledge',{'title':'课程资料','content':'剪纸体验课程，时长90分钟','source':'商家课程表','usage_scope':'marketing','confirmed':True,'kind':'fact'})
 ca=post(api+'/campaigns',{'name':'周末手作体验','objective':'awareness','audience':'本地家庭','start_date':'2026-11-01','end_date':'2026-11-07','budget':100,'channels':['小红书']})
 plan=post(api+'/campaigns/'+ca['id']+'/plans/generate',{})
 post(api+'/plans/'+plan['id']+'/approve',{})
 asset=post(api+'/campaigns/'+ca['id']+'/assets/generate',{'plan_id':plan['id'],'kind':'poster','channel':'小红书'})
 page=ctx.new_page(); errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(base)
 page.get_by_role('button',name='营销活动',exact=True).click()
 page.locator('.campaign-card').filter(has_text='周末手作体验').click()
 page.get_by_role('button',name=re.compile('传播素材')).click()
 page.get_by_role('button',name='照片与海报设计').click()
 dialog=page.get_by_role('dialog',name='实拍照片 · 海报设计')
 photo=page.evaluate('''() => { const c=document.createElement('canvas'); c.width=900;c.height=520; const x=c.getContext('2d');x.fillStyle='#d9b184';x.fillRect(0,0,900,520);x.fillStyle='#a23226';x.beginPath();x.arc(450,260,180,0,Math.PI*2);x.fill();x.fillStyle='white';x.font='48px sans-serif';x.fillText('QA PHOTO',310,280);return c.toDataURL('image/png').split(',')[1]; }''')
 import base64
 dialog.get_by_label('上传海报照片').set_input_files({'name':'real-photo.png','mimeType':'image/png','buffer':base64.b64decode(photo)})
 expect(dialog.get_by_text('照片已附加，可重新选择')).to_be_visible()
 dialog.get_by_role('checkbox').check()
 dialog.locator('select').select_option('warm')
 dialog.get_by_role('textbox',name='标题',exact=True).fill('周末剪纸 · 亲手体验')
 dialog.get_by_role('textbox',name='海报文案').fill('90分钟剪纸体验\n一起认识真实手艺\n详情与报名请联系工坊')
 dialog.get_by_role('button',name='生成预览').click()
 expect(dialog.locator('.poster-preview img')).to_be_visible()
 assert dialog.locator('.poster-preview img').evaluate('(img)=>img.complete && img.naturalWidth===1080')
 page.screenshot(path=str(out/'editor-desktop.png'),full_page=False)
 page.set_viewport_size({'width':375,'height':900})
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 page.screenshot(path=str(out/'editor-mobile.png'),full_page=False)
 dialog.get_by_role('button',name='保存新版本').click()
 expect(page.get_by_role('dialog')).to_have_count(0)
 page.set_viewport_size({'width':1440,'height':1000})
 assets=ctx.request.get(base+'/api'+api+'/campaigns/'+ca['id']+'/assets').json()
 newest=max(assets,key=lambda x:x['version'])
 assert newest['status']=='draft' and newest['content']['poster_image_id']
 post(api+'/assets/'+newest['id']+'/approve',{})
 page.reload();page.get_by_role('button',name='营销活动',exact=True).click();page.locator('.campaign-card').filter(has_text='周末手作体验').click();page.get_by_role('button',name=re.compile('传播素材')).click()
 with page.expect_download() as pending:
  page.get_by_role('button',name='PNG',exact=True).first.click()
 pending.value.save_as(str(out/'approved-photo-poster.png'))
 assert (out/'approved-photo-poster.png').stat().st_size>1000
 assert not errors,errors
 print('PASS real backend: upload, consent, template, preview, mobile, new draft, approval, PNG download; page_errors=[]')
 browser.close()
