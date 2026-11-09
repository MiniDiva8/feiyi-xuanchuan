"""Fictional facts and synthetic provider responses; no paid network requests."""
import copy
import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'services/marketing-ai'))
from marketing_ai import engine
from script_fixtures import script_context, provider_response


def context():
    ctx = script_context()
    ctx['kind'] = 'copy'
    ctx['offering'].update(price=128, quantity=10, location='南京市测试路1号', delivery='仅支持到店自提')
    return ctx


def errors(text, ctx=None):
    return [x['message'] for x in engine.check_content(text, ctx or context()) if x['level'] == 'error']


@pytest.fixture(autouse=True)
def no_live_model(monkeypatch):
    monkeypatch.setenv('MARKETING_AI_API_KEY', '')
    monkeypatch.setenv('MARKETING_AI_MODEL', 'fictional-facts-model')
    monkeypatch.setenv('MARKETING_AI_BASE_URL', 'https://provider.example/v1')
    monkeypatch.setenv('MARKETING_AI_THINKING', '')


def test_reproduced_price_stock_delivery_conflicts_have_actionable_evidence():
    result = errors('售价9.9元，库存100件，全国包邮。')
    assert any('价格' in x and '9.9' in x and '128' in x for x in result)
    assert any('库存' in x and '100' in x and '10' in x for x in result)
    assert any('包邮' in x and '自提' in x for x in result)


def test_reproduced_model_cannot_mask_bad_copy_by_appending_correct_details(monkeypatch):
    monkeypatch.setenv('MARKETING_AI_API_KEY', 'fictional-key')
    payload = {'title': '竹编杯垫', 'body': '售价9.9元，库存100件，全国包邮。', 'content': {'headline': '竹编杯垫'}}
    monkeypatch.setattr(engine, '_open', lambda *a, **k: provider_response(payload))
    with pytest.raises(RuntimeError, match='未回退'):
        engine.generate_asset(context())


def many_sources(count=60):
    ctx = context()
    source = ctx['knowledge'][0]
    ctx['knowledge'] = [dict(source, id=f'unrelated-{i:03}', title='虚构仓储记录', content=f'仓库文件归档编号{i}。') for i in range(count)]
    ctx['knowledge'].insert(45, dict(source, id='relevant-after-40', title='竹编杯垫使用说明',
                                    content='竹编杯垫保留交织纹路，用于桌面放置茶杯。'))
    return ctx


def test_reproduced_source_after_40_is_selected_cited_and_used_in_copy():
    result = engine.generate_asset(many_sources())
    assert '保留交织纹路' in result['body']
    assert 'relevant-after-40' in [x['id'] for x in result['content']['evidence']]


@pytest.mark.parametrize('text', ['售价128元，库存10件。', '售价一百二十八元，库存十件。',
                                  '价格：￥128.00；名额：10人。', '售价１２８元，库存１０件。',
                                  '竹编杯垫售价128元，仅支持到店自提，不支持邮寄。',
                                  '价格128，库存10；地点：南京市测试路1号。'])
def test_correct_explicit_current_facts(text):
    assert not errors(text)


@pytest.mark.parametrize('text', ['售价129元', '价格：￥9.90', '售价九块九', '库存一百件',
                                  '仅剩两件', '名额：20人', '地点：上海市测试路1号',
                                  '取货地址：南京市测试路99号', '支持快递发货', '免费配送上门'])
def test_wrong_current_facts_are_detected(text):
    assert errors(text)


@pytest.mark.parametrize('price,text', [(0, '售价0元'), (0, '报名费零元'), (0, '本课程免费报名'),
                                      (9.9, '售价九块九'), (9.9, '价格9元9角'),
                                      (1280.5, '售价人民币1,280.50元'), (1280.5, '售价一千二百八十点五元')])
def test_decimal_zero_and_common_amount_notation(price, text):
    ctx = context()
    if '课程' in text or '报名' in text:
        ctx['campaign']['objective'] = 'registration'
        ctx['offering']['kind'] = 'course'
    ctx['offering']['price'] = price
    assert not errors(text, ctx)
    assert errors(text, dict(ctx, offering=dict(ctx['offering'], price=price + 1)))


def test_number_roles_are_not_all_prices_or_inventory():
    text = '11月8日开课，时长90分钟，电话13800138000。预算100元，运费9.9元，收入1000元。已售100件，制作过程10分钟。'
    assert not errors(text)


def test_duration_dates_discounts_and_measurements_are_not_commerce_amounts():
    assert not errors('仅需30分钟。只要2小时。剩余10秒。现货2026年上架。价格打9折。仅需9折。剩余2米。')


@pytest.mark.parametrize('text', ['原价199元，现价128元。', '去年售价9.9元，现价128元。',
                                  '引用：“售价9.9元，库存100件，全国包邮。”',
                                  '纸扇售价9.9元，库存100件。竹编杯垫售价128元。',
                                  '其他商品价格9.9元，库存100件。', '两款商品分别售价9.9元和128元。',
                                  '套餐价格256元，含两件商品。', '售价约100元起，需确认规格。',
                                  '售价100—128元，按规格确认。', '售价九元起。',
                                  '以前售价9.9元，库存100件。现价128元。',
                                  '商品：纸扇\n售价9.9元，库存100件。',
                                  '如果售价改为9.9元，需要重新确认。', '地点：体验室（具体地址待确认）。'])
def test_ambiguous_historical_other_items_and_quotes_warn_not_error(text):
    checks = engine.check_content(text, context())
    assert not [x for x in checks if x['level'] == 'error']
    assert any(x['level'] == 'warning' and '核验' in x['message'] for x in checks)


def test_history_does_not_hide_current_conflict_and_correct_append_does_not_cancel_it():
    assert errors('原价199元，现价9.9元。商品资料：售价128元。')
    assert errors('售价9.9元。\n正确详情：售价128元，库存10件。')
    assert errors('口播：“售价9.9元。”')


@pytest.mark.parametrize('explicit_null', [False, True])
def test_missing_facts_warn_without_inventing_zero_or_delivery(explicit_null):
    ctx = context()
    for field in ('price', 'quantity', 'location', 'delivery'):
        ctx['offering'].pop(field)
        if explicit_null:
            ctx['offering'][field] = None
    checks = engine.check_content('售价0元，库存10件；地点：南京市测试路1号；全国包邮。', ctx)
    assert not [x for x in checks if x['level'] == 'error']
    assert len([x for x in checks if x['level'] == 'warning']) >= 4
    result = engine.generate_asset(ctx)
    assert '价格：待补充' in result['body'] and '库存：待补充' in result['body']
    assert '价格：0元' not in result['body']
    ctx['kind'] = 'script'
    script = engine.generate_asset(ctx)
    assert '价格：待补充' in script['body']
    assert '库存：待补充' in script['body']


def test_unknown_shipping_promise_and_location_alias_need_review():
    ctx = context()
    ctx['offering'].update(delivery='履约方式待确认', location='商家工坊')
    checks = engine.check_content('全国包邮；地点：体验室。', ctx)
    assert not [x for x in checks if x['level'] == 'error']
    assert len([x for x in checks if x['level'] == 'warning']) >= 2


def test_provider_content_fields_are_checked_not_only_visible_body(monkeypatch):
    monkeypatch.setenv('MARKETING_AI_API_KEY', 'fictional-key')
    payload = {'title': '竹编杯垫', 'body': '售价128元，库存10件，仅自提。', 'content': {'paragraphs': ['售价9.9元']}}
    monkeypatch.setattr(engine, '_open', lambda *a, **k: provider_response(payload))
    with pytest.raises(RuntimeError):
        engine.generate_asset(context())


def test_full_filtered_sources_support_checking_even_when_generation_budget_excludes_them():
    ctx = many_sources()
    long_source = dict(ctx['knowledge'][0], id='long-authority', content='背景记录。' * 1500 + '国家级非遗传承人张老师，身份已核实，仅供本商品宣传。')
    ctx['knowledge'].append(long_source)
    assert not errors('国家级非遗传承人张老师', ctx)
    for changes in ({'workspace_id': 'foreign'}, {'confirmed': False}, {'usage_scope': 'internal'}):
        other = copy.deepcopy(ctx)
        other['knowledge'][-1].update(changes)
        assert errors('国家级非遗传承人张老师', other)


def test_selection_is_stable_across_input_order_and_preserves_sources():
    ctx = many_sources(120)
    first = engine.generate_asset(ctx)
    random.Random(19).shuffle(ctx['knowledge'])
    second = engine.generate_asset(ctx)
    assert first['body'] == second['body']
    assert first['content']['evidence'] == second['content']['evidence']
    originals = {x['id']: x for x in ctx['knowledge']}
    for item in second['content']['evidence']:
        assert item == {k: originals[item['id']][k] for k in ('id', 'title', 'source')}


def test_query_uses_instructions_and_approved_plan_but_filters_before_ranking(monkeypatch):
    ctx = many_sources()
    special = dict(ctx['knowledge'][0], id='requested', title='保养说明', content='只用干布清洁，不可浸泡。')
    ctx['knowledge'].append(special)
    ctx['instructions'] = '优先说明干布清洁和不可浸泡的保养要求'
    ctx['plan']['content']['channels'][0]['content_ideas'] = ['保养要求']
    for change in ({'workspace_id': 'foreign'}, {'confirmed': False}, {'usage_scope': 'internal'}):
        ctx['knowledge'].append(dict(special, id='secret', content='竹编杯垫干布清洁 PRIVATE_SENTINEL', **change))
    seen = []
    def respond(req, timeout):
        data = json.loads(json.loads(req.data)['messages'][1]['content'])['data']
        seen.append(data)
        return provider_response({'title': '竹编杯垫', 'body': '售价128元，仅支持自提。', 'content': {'headline': '竹编杯垫'}})
    monkeypatch.setenv('MARKETING_AI_API_KEY', 'fictional-key')
    monkeypatch.setattr(engine, '_open', respond)
    result = engine.generate_asset(ctx)
    selected = seen[0]['knowledge']
    assert 'requested' in [x['id'] for x in selected[:3]]
    assert 'PRIVATE_SENTINEL' not in json.dumps(seen)
    assert 'secret' not in [x['id'] for x in result['content']['evidence']]
    assert next(x for x in selected if x['id'] == 'requested')['selection_reason']


def test_length_budget_keeps_whole_records_not_a_claim_without_its_qualifier():
    ctx = many_sources()
    content = '竹编杯垫支持特定使用方式。' + '测试背景。' * 1600 + '但未经确认不可用于食品接触。'
    ctx['knowledge'].insert(0, dict(ctx['knowledge'][0], id='too-long', content=content))
    selected = engine._context(ctx)['knowledge']
    assert len(selected) <= 40
    assert len(json.dumps(selected, ensure_ascii=False)) <= 14000
    for item in selected:
        original = next(x for x in ctx['knowledge'] if x['id'] == item['id'])
        assert item['content'] == original['content']
    assert 'too-long' not in [x['id'] for x in selected]
    assert 'relevant-after-40' in [x['id'] for x in selected]


def test_script_does_not_extract_claim_without_following_qualifier():
    ctx = context()
    ctx['kind'] = 'script'
    qualified = '可以水洗。仅限可拆卸的布套，竹编部分不能水洗，必须取下布套单独清洁。'
    ctx['knowledge'][0]['content'] = qualified
    ctx['offering']['description'] = qualified
    result = engine.generate_asset(ctx)
    assert qualified in result['body']
    for shot in result['content']['storyboard']:
        assert '可以水洗' not in shot['voiceover']
        assert '可以水洗' not in shot['subtitle']


def test_model_validation_uses_full_sources_outside_generation_budget(monkeypatch):
    ctx = many_sources()
    ctx['knowledge'].append(dict(ctx['knowledge'][0], id='long-identity',
                                 content='虚构背景记录。' * 1000 + '国家级非遗传承人张老师，身份已确认。'))
    seen = []
    def respond(req, timeout):
        seen.append(json.loads(json.loads(req.data)['messages'][1]['content'])['data'])
        return provider_response({'title': '竹编杯垫', 'body': '国家级非遗传承人张老师。售价128元。', 'content': {}})
    monkeypatch.setenv('MARKETING_AI_API_KEY', 'fictional-key')
    monkeypatch.setattr(engine, '_open', respond)
    result = engine.generate_asset(ctx)
    assert result['generation_mode'] == 'ai'
    assert 'long-identity' not in [x['id'] for x in seen[0]['knowledge']]
    ctx['knowledge'][-1]['confirmed'] = False
    with pytest.raises(RuntimeError):
        engine.generate_asset(ctx)


def test_approved_plan_and_untruncated_instructions_can_rank_late_sources():
    ctx = many_sources()
    ctx['knowledge'].extend([
        dict(ctx['knowledge'][0], id='care', title='保养说明', content='干布清洁，不可浸泡。'),
        dict(ctx['knowledge'][0], id='packaging', title='包装说明', content='展示纸盒包装。'),
    ])
    ctx['instructions'] = 'a' * 2100 + '干布清洁，不可浸泡'
    ctx['plan']['content']['theme'] = '展示纸盒包装'
    selected = engine._context(ctx)['knowledge']
    assert {'care', 'packaging'} <= {x['id'] for x in selected[:3]}
    assert '已批准方案' in next(x for x in selected if x['id'] == 'packaging')['selection_reason']['matched_fields']
    ctx['plan']['status'] = 'draft'
    selected = engine._context(ctx)['knowledge']
    assert all('已批准方案' not in x['selection_reason']['matched_fields'] for x in selected)
