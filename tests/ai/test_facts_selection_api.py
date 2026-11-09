"""Actual tenant-scoped generation/revision/review routes with fictional inputs."""
import copy
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'services/api'), str(ROOT / 'services/marketing-ai')]
from script_fixtures import script_context, provider_response


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('MARKETING_AI_API_KEY', '')
    monkeypatch.setenv('MARKETING_AI_MODEL', 'fictional-facts-model')
    monkeypatch.setenv('MARKETING_AI_BASE_URL', 'https://provider.example/v1')
    monkeypatch.setenv('MARKETING_AI_THINKING', '')
    from app.main import create_app
    with TestClient(create_app('sqlite:///' + str(tmp_path / 'facts.db'), str(tmp_path / 'files'))) as session:
        yield session


def post(client, path, data):
    response = client.post(path, json=data)
    assert response.status_code in (200, 201), response.text
    return response.json()


def prepared(client, kind='product', many=False):
    data = script_context(kind)
    workspace = post(client, '/api/auth/register', {'name': '虚构事实测试', 'email': 'facts@example.org',
                     'password': 'Fictional-password-2026', 'workspace_name': '虚构工坊'})['workspaces'][0]['id']
    base = '/api/workspaces/' + workspace
    offering = {k: v for k, v in data['offering'].items() if k not in ('id', 'workspace_id')}
    offering.update(price=128, quantity=10, location='南京市测试路1号', delivery='仅支持到店自提' if kind == 'product' else '仅限到店参加课程')
    item = post(client, base + '/offerings', offering)
    knowledge = {'title': '虚构确认说明', 'content': data['knowledge'][0]['content'], 'source': '虚构测试来源',
                 'confirmed': True, 'usage_scope': 'marketing', 'kind': 'fact'}
    if many:
        for i in range(45):
            post(client, base + '/knowledge', dict(knowledge, title=f'归档记录{i}', content=f'无关仓储单据归档编号{i}。'))
    selected = post(client, base + '/knowledge', dict(knowledge, title=offering['name'] + '资料', content=offering['name'] + '保留交织纹路，请使用干布清洁。'))
    foreign = post(client, '/api/workspaces', {'name': '虚构其他商家'})['id']
    post(client, f'/api/workspaces/{foreign}/knowledge', dict(knowledge, content='PRIVATE_FOREIGN_SENTINEL'))
    for fields in ({'confirmed': False}, {'usage_scope': 'internal'}):
        post(client, base + '/knowledge', dict(knowledge, content='PRIVATE_UNCONFIRMED_SENTINEL', **fields))
    campaign = {k: v for k, v in data['campaign'].items() if k not in ('id', 'workspace_id')}
    campaign['offering_id'] = item['id']
    c = post(client, base + '/campaigns', campaign)
    path = base + f'/campaigns/{c["id"]}'
    plan = post(client, path + '/plans/generate', {})
    post(client, base + f'/plans/{plan["id"]}/approve', {})
    return base, path, plan, selected


@pytest.mark.parametrize('kind', ['product', 'course'])
def test_manual_revision_surfaces_conflicts_and_blocks_approval_until_corrected(client, kind):
    base, path, plan, _ = prepared(client, kind)
    payload = {'kind': 'copy', 'channel': '抖音', 'plan_id': plan['id']}
    asset = post(client, path + '/assets/generate', payload)
    assert not [x for x in asset['checks'] if x['level'] == 'error']
    post(client, base + f'/assets/{asset["id"]}/approve', {})
    bad = '售价9.9元，' + ('库存100件，全国包邮。' if kind == 'product' else '名额100人。')
    revised = post(client, base + f'/assets/{asset["id"]}/revise', {'body': bad + '\n正确详情：售价128元。'})
    problems = [x for x in revised['checks'] if x['level'] == 'error']
    assert any('价格' in x['message'] and '128' in x['message'] for x in problems)
    assert any(('库存' if kind == 'product' else '名额') in x['message'] for x in problems)
    route = base + f'/assets/{revised["id"]}'
    assert client.post(route + '/approve', json={}).status_code == 409
    assert client.get(route + '/export?format=txt').status_code == 409
    good = '售价128元，' + ('库存10件，仅支持到店自提。' if kind == 'product' else '名额10人。')
    fixed = post(client, route + '/revise', {'body': good + '\n引用：“历史售价9.9元”。'})
    assert not [x for x in fixed['checks'] if x['level'] == 'error']
    assert any(x['level'] == 'warning' for x in fixed['checks'])
    post(client, base + f'/assets/{fixed["id"]}/approve', {})
    assert client.get(base + f'/assets/{fixed["id"]}/export?format=txt').status_code == 200
    history = client.get(path + '/assets').json()
    assert next(x for x in history if x['id'] == asset['id'])['body'] == asset['body']


def test_existing_plan_json_revision_checks_real_text_not_serialization_quotes(client):
    base, _, plan, _ = prepared(client)
    content = copy.deepcopy(plan['content'])
    content['summary'] = '售价9.9元，库存100件，全国包邮。'
    response = client.post(base + f'/plans/{plan["id"]}/revise', json={'content': content, 'instructions': ''})
    assert response.status_code == 422


def test_late_related_source_reaches_template_and_citations_through_existing_api(client):
    _, path, plan, selected = prepared(client, many=True)
    asset = post(client, path + '/assets/generate', {'plan_id': plan['id'], 'kind': 'copy', 'channel': '抖音'})
    assert '使用干布清洁' in asset['body']
    assert selected['id'] in [x['id'] for x in asset['content']['evidence']]
    assert 'PRIVATE_' not in json.dumps(asset)
    assert any('相关' in x['message'] or '选择' in x['message'] for x in asset['checks'])


@pytest.mark.parametrize('body', ['售价9.9元，库存100件，全国包邮。', '售价128元，库存10件，仅支持到店自提。'])
def test_simulated_model_uses_filtered_sources_and_fails_instead_of_appending_over_conflicts(client, monkeypatch, body):
    base, path, plan, selected = prepared(client, many=True)
    from marketing_ai import engine
    requests = []
    def respond(req, timeout):
        requests.append(json.loads(json.loads(req.data)['messages'][1]['content'])['data'])
        return provider_response({'title': '竹编杯垫', 'body': body, 'content': {'paragraphs': [body]}})
    monkeypatch.setenv('MARKETING_AI_API_KEY', 'fictional-key')
    monkeypatch.setattr(engine, '_open', respond)
    response = client.post(path + '/assets/generate', json={'plan_id': plan['id'], 'kind': 'copy', 'channel': '抖音'})
    assert selected['id'] in [x['id'] for x in requests[0]['knowledge'][:3]]
    assert 'PRIVATE_' not in json.dumps(requests)
    if '9.9' in body:
        assert response.status_code == 502
        assert client.get(path + '/assets').json() == []
        tasks = [x for x in client.get(base + '/tasks').json() if x['kind'] == 'asset']
        assert len(tasks) == 1 and tasks[0]['status'] == 'failed'
        assert not tasks[0].get('generation_mode')
    else:
        assert response.status_code == 201, response.text
        assert response.json()['generation_mode'] == 'ai'
        assert not [x for x in response.json()['checks'] if x['level'] == 'error']
