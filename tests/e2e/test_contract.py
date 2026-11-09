from pathlib import Path
import sys
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'services' / 'api'), str(ROOT / 'services' / 'marketing-ai')]

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv('MARKETING_AI_API_KEY', raising=False)
    from app.main import create_app
    with TestClient(create_app('sqlite:///' + str(tmp_path / 'acceptance.db'), str(tmp_path / 'files'))) as session:
        yield session


def must(response, status=200):
    assert response.status_code == status, response.text
    return response.json()


def register(client, suffix):
    data = must(client.post('/api/auth/register', json={'name':'验收商家', 'email':f'{suffix}@acceptance.example', 'password':'Acceptance-2026-Strong', 'workspace_name':'验收手作工坊'}), 201)
    return data['workspaces'][0]['id']


def test_real_marketing_round_and_unknown_attribution(client):
    workspace = register(client, 'owner')
    base = f'/api/workspaces/{workspace}'
    knowledge = must(client.post(base + '/knowledge', json={'title':'商家确认的产品事实', 'content':'工坊制作蓝染棉布书签，售价29元。', 'source':'商家产品说明2026-10-31', 'usage_scope':'marketing', 'confirmed':True, 'kind':'fact'}), 201)
    offering = must(client.post(base + '/offerings', json={'kind':'product','name':'蓝染书签','description':'棉布手作书签','price':29,'quantity':30,'location':'济南','delivery':'下单后三日发货','conversion_url':'https://shop.example.com/bookmark'}), 201)
    campaign = must(client.post(base + '/campaigns', json={'name':'书签秋日推广','objective':'sales','audience':'喜欢手作的大学生','start_date':'2026-11-01','end_date':'2026-11-07','budget':300,'channels':['小红书','微信'],'offering_id':offering['id'],'notes':'不虚构非遗传承人身份'}), 201)
    cid = campaign['id']
    plan = must(client.post(base + f'/campaigns/{cid}/plans/generate', json={}), 201)
    assert plan['generation_mode'] == 'template'
    assert plan['content']['evidence']
    assert any(item['id'] == knowledge['id'] for item in plan['content']['evidence'])
    unapproved = client.post(base + f'/campaigns/{cid}/assets/generate', json={'plan_id':plan['id'],'kind':'copy','channel':'小红书'})
    assert unapproved.status_code == 409
    must(client.post(base + f"/plans/{plan['id']}/approve", json={}))
    asset = must(client.post(base + f'/campaigns/{cid}/assets/generate', json={'plan_id':plan['id'],'kind':'copy','channel':'小红书'}), 201)
    assert client.get(base + f"/assets/{asset['id']}/export").status_code == 409
    must(client.post(base + f"/assets/{asset['id']}/approve", json={}))
    exported = client.get(base + f"/assets/{asset['id']}/export?format=txt")
    assert exported.status_code == 200
    assert exported.content
    publication = must(client.post(base + '/publications', json={'asset_id':asset['id'],'channel':'小红书','url':'https://www.example.com/real-work','published_at':'2026-11-01T10:00:00+08:00','external_id':'acceptance-work-1'}), 201)
    assert publication['plan_id'] == plan['id']
    csv = f'campaign_id,date,channel,source,external_id,attribution,impressions,orders,revenue,refunds,spend\n{cid},2026-11-01,小红书,经营台账,row-001,unknown,100,2,58,0,12\n'
    preview = must(client.post(base + '/metrics/preview', json={'csv':csv}))
    assert not preview['errors'], preview
    assert preview['valid_rows'] == 1
    imported = must(client.post(base + '/metrics/import', json={'csv':csv}))
    assert imported['imported'] == 1
    repeated = must(client.post(base + '/metrics/import', json={'csv':csv}))
    assert repeated['imported'] == 0
    assert repeated['duplicates'] == 1
    analytics = must(client.get(base + '/analytics', params={'campaign_id':cid}))
    assert analytics['stats']['orders'] == 2
    assert analytics['stats']['net_revenue'] == 58
    assert analytics['stats']['unknown_revenue'] == 58
    review = must(client.post(base + f'/campaigns/{cid}/reviews/generate', json={}), 201)
    assert review['content']['facts']
    assert review['content']['limitations']
    next_round = must(client.post(base + f'/campaigns/{cid}/next-round', json={}), 201)
    assert next_round['id'] != cid
    assert next_round['previous_campaign_id'] == cid
    assert must(client.get(base + f"/campaigns/{next_round['id']}/plans")) == []
    revised = must(client.post(base + f"/assets/{asset['id']}/revise", json={'title':'新标题','body':'商家修改的新版本，需要重新审核。'}), 201)
    assert revised['id'] != asset['id'] and revised['status'] == 'draft'
    assert client.get(base + f"/assets/{revised['id']}/export").status_code == 409
    assert must(client.get(base + '/audit'))
    assert must(client.get(base + '/tasks'))


def test_login_boundary_and_invalid_sources(client):
    first = register(client, 'first')
    base = f'/api/workspaces/{first}'
    record = must(client.post(base + '/knowledge', json={'title':'私有资料','content':'只供内部查阅','source':'内部','usage_scope':'internal','confirmed':True,'kind':'brand'}), 201)
    must(client.post('/api/auth/logout', json={}))
    assert client.get(base + '/knowledge').status_code == 401
    second = register(client, 'second')
    for route in ['/knowledge','/offerings','/campaigns','/metrics','/audit','/tasks','/overview']:
        assert client.get(base + route).status_code in (403,404)
    assert client.patch(base + f"/knowledge/{record['id']}", json={'confirmed':False}).status_code in (403,404)
    assert must(client.get(f'/api/workspaces/{second}/knowledge')) == []
