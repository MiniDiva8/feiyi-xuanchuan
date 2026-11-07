"""Review comparisons use only fictional aggregate data."""
import copy
from unittest.mock import patch

from test_review import review_context
from marketing_ai import engine


def context():
    ctx = review_context('sales', {'impressions': 150, 'interactions': 15, 'orders': 5,
                                   'inquiries': 10, 'revenue': 200, 'refunds': 0, 'spend': 30})
    ctx['analytics']['trends'] = [
        {'date': '2026-11-01', 'impressions': 100, 'revenue': 80, 'spend': 10},
        {'date': '2026-11-02', 'impressions': 50, 'revenue': 120, 'spend': 20},
    ]
    ctx['analytics']['channels'] = [
        {'channel': '抖音', 'impressions': 100, 'interactions': 10, 'orders': 3, 'revenue': 120, 'spend': 20},
        {'channel': '微信', 'impressions': 50, 'interactions': 5, 'orders': 2, 'revenue': 80, 'spend': 10},
    ]
    return ctx


def rendered(result):
    return '\n'.join(str(item) for group in result['content'].values() for item in group)


def test_two_days_have_actual_comparison_and_specific_action():
    result = engine.build_review(context())
    text = rendered(result)
    assert all(x in text for x in ('2026-11-01', '2026-11-02', '100', '50', '50%'))
    assert '曝光' in text and ('下降' in text or '减少' in text)
    assert any('曝光' in row['action'] for row in result['content']['suggestions'])
    assert '累计' in text and '渠道' in text and '补零' in text


def test_same_day_is_not_invented_as_a_time_trend():
    ctx = context()
    ctx['analytics']['trends'] = ctx['analytics']['trends'][:1]
    text = rendered(engine.build_review(ctx))
    assert '不同日期' in text and '无法' in text
    assert '抖音' in text and '微信' in text


def test_zero_baseline_and_missing_field_are_not_made_up():
    ctx = context()
    ctx['analytics']['trends'][0].update(impressions=0)
    del ctx['analytics']['trends'][0]['revenue']
    text = rendered(engine.build_review(ctx))
    assert '基数为0' in text and '不计算' in text
    assert '收入' in text and '缺' in text


def test_no_trends_are_explicit_and_aggregate_still_available():
    ctx = context()
    ctx['analytics'].pop('trends')
    text = rendered(engine.build_review(ctx))
    assert '无法' in text and '日期' in text
    assert '曝光：150' in text


def test_ai_cannot_erase_trend_facts_or_specific_suggestions():
    ctx = context()
    baseline = engine.build_review(ctx)
    response = {'facts': [], 'hypotheses': [], 'suggestions': [], 'limitations': []}
    with patch.object(engine, '_model', return_value=(response, {})):
        result = engine.build_review(copy.deepcopy(ctx))
    assert result['content']['facts'] == baseline['content']['facts']
    assert result['content']['suggestions'] == baseline['content']['suggestions']
    assert result['content']['limitations'] == baseline['content']['limitations']


def test_malformed_and_duplicate_dates_do_not_create_fake_trends():
    ctx = context()
    ctx['analytics']['trends'] = [{'date': 'invalid', 'impressions': 10},
                                  {'date': '2026-11-01', 'impressions': 20},
                                  {'date': '2026-11-01', 'impressions': 30}]
    text = rendered(engine.build_review(ctx))
    assert '无法' in text and '日期' in text


def test_three_dates_use_the_latest_two_and_increase_suggests_checking_exposure():
    ctx = context()
    ctx['analytics']['trends'].append({'date': '2026-11-03', 'impressions': 100, 'revenue': 120, 'spend': 20})
    result = engine.build_review(ctx)
    text = rendered(result)
    assert '2026-11-02' in text and '2026-11-03' in text and '增加50' in text
    assert '2026-11-01' not in text
    assert any('曝光' in row['action'] for row in result['content']['suggestions'])
    assert '2026-11-02' in result['content']['facts'][1]['statement']


def test_channel_names_are_not_sent_to_model_but_remain_in_local_review():
    ctx = context()
    ctx['analytics']['channels'][0]['channel'] = '虚构隐私渠道名'
    response = {'facts': [], 'hypotheses': [], 'suggestions': [], 'limitations': []}
    with patch.object(engine, '_model', return_value=(response, {})) as provider:
        result = engine.build_review(ctx)
    assert '虚构隐私渠道名' in rendered(result)
    assert '虚构隐私渠道名' not in str(provider.call_args)
