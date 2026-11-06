"""Real product routes with isolated fictional stores; no network model calls."""
import html
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'services/api'), str(ROOT / 'services/marketing-ai')]
from script_fixtures import script_context, provider_response


def post(client, path, data):
    response = client.post(path, json=data)
    assert response.status_code in (200, 201), response.text
    return response.json()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('MARKETING_AI_API_KEY', '')
    monkeypatch.setenv('MARKETING_AI_MODEL', 'fictional-script-model')
    monkeypatch.setenv('MARKETING_AI_BASE_URL', 'https://provider.example/v1')
    monkeypatch.setenv('MARKETING_AI_THINKING', '')
    from app.main import create_app
    with TestClient(create_app('sqlite:///' + str(tmp_path / 'scripts.db'), str(tmp_path / 'files'))) as session:
        yield session


def prepared(client, kind, incomplete=False):
    fixture = script_context(kind)
    user = post(client, '/api/auth/register', {'name': '虚构测试商家', 'email': 'script-owner@example.org',
                'password': 'Fictional-test-password', 'workspace_name': fixture['workspace']['name']})
    workspace = user['workspaces'][0]['id']
    base = f'/api/workspaces/{workspace}'
    safe = {k: v for k, v in fixture['knowledge'][0].items() if k not in ('id', 'workspace_id')}
    safe['kind'] = 'fact'
    source = post(client, base + '/knowledge', dict(safe, confirmed=not incomplete))
    for fields in ({'confirmed': False}, {'usage_scope': 'internal'}):
        post(client, base + '/knowledge', dict(safe, content='UNCONFIRMED_PRIVATE_SENTINEL', **fields))
    other = post(client, '/api/workspaces', {'name': '虚构测试另一商家'})['id']
    post(client, f'/api/workspaces/{other}/knowledge', dict(safe, content='FOREIGN_PRIVATE_SENTINEL'))
    offering_data = {k: v for k, v in fixture['offering'].items() if k not in ('id', 'workspace_id')}
    if incomplete:
        offering_data.update(location='', delivery='')
    offering = post(client, base + '/offerings', offering_data)
    campaign_data = {k: v for k, v in fixture['campaign'].items() if k not in ('id', 'workspace_id')}
    campaign = post(client, base + '/campaigns', dict(campaign_data, offering_id=offering['id']))
    path = base + f'/campaigns/{campaign["id"]}'
    plan = post(client, path + '/plans/generate', {})
    payload = {'plan_id': plan['id'], 'kind': 'script', 'channel': '抖音'}
    assert client.post(path + '/assets/generate', json=payload).status_code == 409
    post(client, base + f'/plans/{plan["id"]}/approve', {})
    return base, path, payload, source, other, fixture


@pytest.mark.parametrize('kind', ['product', 'course'])
@pytest.mark.parametrize('mode', ['template', 'ai'])
def test_existing_generate_edit_approve_export_and_version_flow(client, monkeypatch, kind, mode):
    base, path, payload, source, other, fixture = prepared(client, kind)
    requests = []
    if mode == 'ai':
        from marketing_ai import engine
        def respond(req, timeout):
            data = json.loads(json.loads(req.data)['messages'][1]['content'])
            requests.append(data)
            return provider_response(data['output_structure'])
        monkeypatch.setenv('MARKETING_AI_API_KEY', 'fictional-test-key')
        monkeypatch.setattr(engine, '_open', respond)
    asset = post(client, path + '/assets/generate', payload)
    assert asset['generation_mode'] == mode
    assert asset['kind'] == 'script' and asset['channel'] == '抖音'
    assert len(asset['content']['storyboard']) == 5
    assert [x['id'] for x in asset['content']['evidence']] == [source['id']]
    assert 'PRIVATE_SENTINEL' not in json.dumps(asset)
    assert 'PRIVATE_SENTINEL' not in json.dumps(requests)
    for value in ('开场吸引点', '画面：', '口播：', '字幕：', '实物与设备', '场景', '素材与来源',
                  '配套发布文案', '话题建议', '结尾行动提示', fixture['offering']['conversion_url']):
        assert value in asset['body']
    # These are precisely the body/title fields displayed by the existing page.
    listed = client.get(path + '/assets').json()
    assert listed[0]['body'] == asset['body']
    route = base + f'/assets/{asset["id"]}'
    assert client.get(route + '/export?format=txt').status_code == 409
    post(client, route + '/approve', {})
    exported = client.get(route + '/export?format=txt')
    assert exported.status_code == 200
    assert exported.text == asset['title'] + '\n\n' + asset['body']
    revised_body = asset['body'] + '\n手工拍摄备注：<仅测试>开拍前检查收音。'
    revised = post(client, route + '/revise', {'title': asset['title'], 'body': revised_body})
    assert revised['status'] == 'draft' and revised['id'] != asset['id']
    assert client.get(route + '/export?format=txt').status_code == 409
    new_route = base + f'/assets/{revised["id"]}'
    assert client.get(new_route + '/export?format=txt').status_code == 409
    post(client, new_route + '/approve', {})
    assert client.get(new_route + '/export?format=txt').text == asset['title'] + '\n\n' + revised_body
    exported_html = client.get(new_route + '/export?format=html')
    assert exported_html.status_code == 200
    assert html.escape(revised_body) in exported_html.text
    history = client.get(path + '/assets').json()
    assert next(x for x in history if x['id'] == asset['id'])['body'] == asset['body']
    assert client.get(f'/api/workspaces/{other}/assets/{revised["id"]}/export?format=txt').status_code == 404
    assert client.patch(base + f'/knowledge/{source["id"]}', json={'confirmed': False}).status_code == 200
    assert client.get(new_route + '/export?format=txt').status_code == 409
    if mode == 'ai':
        assert len(requests) == 1
        tasks = client.get(base + '/tasks').json()
        assert any(t.get('generation_mode') == 'ai' and t['status'] == 'succeeded' for t in tasks)


def test_incomplete_draft_via_existing_route_is_complete_but_warns(client):
    base, path, payload, source, other, fixture = prepared(client, 'course', incomplete=True)
    asset = post(client, path + '/assets/generate', payload)
    assert asset['generation_mode'] == 'template'
    assert len(asset['content']['storyboard']) == 5
    assert '地点：待补充' in asset['body']
    assert '履约说明：待补充' in asset['body']
    assert '补齐并核实后再发布' in asset['content']['cta']
    assert not asset['content']['evidence']
    # Missing transaction fields already have validation at the existing API boundary.
    data = {k: v for k, v in fixture['offering'].items() if k not in ('id', 'workspace_id', 'conversion_url')}
    assert client.post(base + '/offerings', json=data).status_code == 422


@pytest.mark.parametrize('failure', ['timeout', 'invalid_json', 'timeline', 'fabricated_fact'])
def test_model_failure_persists_failed_task_and_no_fake_template_asset(client, monkeypatch, failure):
    base, path, payload, *_ = prepared(client, 'product')
    from marketing_ai import engine
    def respond(req, timeout):
        if failure == 'timeout':
            raise TimeoutError('private error must not escape')
        if failure == 'invalid_json':
            return provider_response('bad json')
        data = json.loads(json.loads(req.data)['messages'][1]['content'])['output_structure']
        if failure == 'timeline':
            data['storyboard'][1]['start_second'] = 2
        else:
            data['storyboard'][3]['voiceover'] = '限时1元全国包邮'
        return provider_response(data)
    monkeypatch.setenv('MARKETING_AI_API_KEY', 'fictional-test-key')
    monkeypatch.setattr(engine, '_open', respond)
    response = client.post(path + '/assets/generate', json=payload)
    assert response.status_code == 502
    assert 'private error' not in response.text and 'fictional-test-key' not in response.text
    assert client.get(path + '/assets').json() == []
    tasks = [t for t in client.get(base + '/tasks').json() if t['kind'] == 'asset']
    assert len(tasks) == 1 and tasks[0]['status'] == 'failed'
    assert not tasks[0].get('generation_mode')
    assert '未替换为虚构结果' in tasks[0]['error']
