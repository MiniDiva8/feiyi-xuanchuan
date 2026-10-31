import copy
import importlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'services' / 'marketing-ai'))


def context():
    return {
        'workspace': {'id': 'w1', 'name': '竹艺工坊'},
        'campaign': {'id': 'c1', 'workspace_id': 'w1', 'name': '周末竹编体验', 'objective': 'registration',
                     'audience': '本地亲子家庭', 'start_date': '2026-11-01', 'end_date': '2026-11-07',
                     'budget': 180, 'channels': ['小红书', '微信'], 'notes': ''},
        'offering': {'id': 'o1', 'workspace_id': 'w1', 'kind': 'course', 'name': '竹编入门课',
                     'description': '制作竹杯垫', 'price': 68, 'quantity': 8, 'location': '工坊',
                     'delivery': '现场体验', 'conversion_url': 'https://example.org/book'},
        'knowledge': [{'id': 'k1', 'workspace_id': 'w1', 'title': '课程资料', 'content': '课程时长90分钟',
                       'source': '商家课程表', 'usage_scope': 'marketing', 'confirmed': True}],
    }


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict('os.environ', {'MARKETING_AI_API_KEY': '', 'MARKETING_AI_MODEL': '',
                                           'MARKETING_AI_BASE_URL': 'https://provider.example/v1'}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)

    def engine(self):
        try:
            return importlib.import_module('marketing_ai.engine')
        except ModuleNotFoundError:
            self.fail('marketing_ai.engine must implement the contracted generation interface')

    def test_plan_template_grounded_budget_schedule_and_evidence(self):
        result = self.engine().generate_plan(context())
        self.assertEqual(result['generation_mode'], 'template')
        content = result['content']
        self.assertLessEqual(sum(row['amount'] for row in content['budget']), 180)
        self.assertEqual([x['id'] for x in content['evidence']], ['k1'])
        self.assertTrue(all('2026-11-01' <= x['day'] <= '2026-11-07' for x in content['schedule']))
        self.assertIn('竹编入门课', json.dumps(content, ensure_ascii=False))
        self.assertIn('https://example.org/book', json.dumps(content, ensure_ascii=False))
        self.assertEqual(result['usage']['total_tokens'], 0)

    def test_missing_information_is_a_visible_draft_warning(self):
        ctx = context()
        ctx['knowledge'] = []
        ctx['offering'] = None
        result = self.engine().generate_plan(ctx)
        self.assertTrue(any('资料' in warning for warning in result['content']['warnings']))
        self.assertTrue(any('商品' in warning or '课程' in warning for warning in result['content']['warnings']))
        self.assertNotIn('国家级', json.dumps(result, ensure_ascii=False))

    def test_foreign_unconfirmed_and_internal_material_never_used(self):
        ctx = context()
        for fields in ({'workspace_id': 'w2'}, {'confirmed': False}, {'usage_scope': 'internal'}):
            item = dict(ctx['knowledge'][0], id='private', content='FOREIGN_PRIVATE_SECRET', **fields)
            ctx['knowledge'].append(item)
        result = self.engine().generate_plan(ctx)
        self.assertEqual([x['id'] for x in result['content']['evidence']], ['k1'])
        self.assertNotIn('FOREIGN_PRIVATE_SECRET', json.dumps(result))

    def test_cross_workspace_offering_and_plan_are_rejected(self):
        ctx = context()
        ctx['offering']['workspace_id'] = 'w2'
        with self.assertRaises(ValueError):
            self.engine().generate_plan(ctx)
        ctx = context()
        ctx['plan'] = {'workspace_id': 'w2', 'content': {}}
        with self.assertRaises(ValueError):
            self.engine().generate_asset(ctx)

    def test_asset_variants_include_real_conversion_and_safety_checks(self):
        eng = self.engine()
        for kind in ('copy', 'poster', 'script'):
            ctx = dict(context(), kind=kind, channel='微信')
            result = eng.generate_asset(ctx)
            self.assertEqual(result['generation_mode'], 'template')
            self.assertIn('竹编入门课', result['body'])
            self.assertIn('https://example.org/book', result['body'])
            self.assertTrue(result['content'])
            self.assertIsInstance(result['checks'], list)
        with self.assertRaises(ValueError):
            eng.generate_asset(dict(context(), kind='executable'))

    def test_absolute_guarantees_and_unsubstantiated_identities_are_flagged(self):
        checks = self.engine().check_content('国家级非遗传承人亲授，保证100%赚钱，全网第一。', context())
        self.assertTrue(any(x['level'] == 'error' for x in checks))
        self.assertTrue(any('身份' in x['message'] or '资质' in x['message'] for x in checks))

    def test_review_facts_use_real_values_and_unknown_attribution_is_separate(self):
        ctx = dict(context(), analytics={'stats': {'impressions': 1000, 'interactions': 80, 'orders': 3,
                   'revenue': 204, 'refunds': 68, 'net_revenue': 136, 'registrations': 3,
                   'checkins': 2, 'spend': 30, 'unknown_revenue': 68}, 'records': 2,
                   'trends': [], 'channels': []})
        result = self.engine().build_review(ctx)
        facts = json.dumps(result['content']['facts'], ensure_ascii=False)
        self.assertIn('1000', facts)
        self.assertIn('136', facts)
        self.assertIn('68', facts)
        self.assertNotIn('136元利润', facts)
        self.assertTrue(result['content']['limitations'])
        self.assertTrue(result['content']['hypotheses'])
        self.assertTrue(all('validation' in x for x in result['content']['hypotheses']))

    def test_confirmed_heritage_identity_can_be_used_without_false_missing_source_warning(self):
        ctx = context()
        ctx['knowledge'][0]['content'] = '已核验资质：国家级非遗传承人张老师；仅供本活动宣传使用。'
        checks = self.engine().check_content('国家级非遗传承人张老师', ctx)
        self.assertFalse(any(x['level'] == 'error' for x in checks))
        asset = self.engine().generate_asset(dict(ctx, kind='copy'))
        self.assertFalse(any('尚无已确认营销资料' in x['message'] for x in asset['checks']))

    def test_confirmed_credential_does_not_authorize_different_named_person(self):
        ctx = context()
        ctx['knowledge'][0]['content'] = '国家级非遗传承人张老师，资料已核验。'
        checks = self.engine().check_content('国家级非遗传承人李老师亲授。', ctx)
        self.assertTrue(any(x['level'] == 'error' for x in checks))

    def test_offering_must_match_campaign_binding(self):
        ctx = context()
        ctx['campaign']['offering_id'] = 'different-offering'
        with self.assertRaises(ValueError):
            self.engine().generate_plan(ctx)

    def test_invalid_asset_from_provider_never_succeeds(self):
        eng = self.engine()
        self.configure()
        for body in ('保证100%赚钱', '国家级非遗传承人亲授'):
            payload = {'title': '体验课', 'body': body, 'content': {'headline': body}}
            with patch.object(eng, '_open', return_value=self.provider(json.dumps(payload))):
                with self.assertRaises(RuntimeError):
                    eng.generate_asset(dict(context(), kind='copy'))

    def test_review_with_no_records_does_not_invent_performance(self):
        result = self.engine().build_review(context())
        self.assertTrue(any('数据' in s for s in result['content']['limitations']))
        self.assertNotIn('提升', json.dumps(result['content']['facts'], ensure_ascii=False))

    def configure(self):
        import os
        os.environ['MARKETING_AI_API_KEY'] = 'secret-never-log'
        os.environ['MARKETING_AI_MODEL'] = 'test-model'

    def provider(self, payload, usage=None):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, limit=-1):
                return json.dumps({'choices': [{'message': {'content': payload}}],
                                   'usage': usage or {'prompt_tokens': 40, 'completion_tokens': 20,
                                                     'total_tokens': 60}}).encode()
        return Response()

    def test_configured_failure_is_sanitized_and_never_template_success(self):
        eng = self.engine()
        self.configure()
        with patch.object(eng, '_open', side_effect=OSError('secret-never-log internal credentials')):
            with self.assertRaises(RuntimeError) as raised:
                eng.generate_plan(context())
        self.assertNotIn('secret-never-log', str(raised.exception))
        self.assertNotIn('credentials', str(raised.exception))

    def test_configured_endpoint_requires_https(self):
        self.configure()
        with patch.dict('os.environ', {'MARKETING_AI_BASE_URL': 'http://provider.example/v1'}):
            with self.assertRaises(RuntimeError):
                self.engine().generate_plan(context())

    def test_provider_malformed_json_and_invalid_schema_fail_closed(self):
        eng = self.engine()
        self.configure()
        for data in ('not JSON', '{"theme":"x"}', '{"theme":NaN}'):
            with patch.object(eng, '_open', return_value=self.provider(data)):
                with self.assertRaises(RuntimeError):
                    eng.generate_plan(context())

    def test_provider_plan_retains_real_evidence_and_rejects_overspend(self):
        eng = self.engine()
        draft = eng.generate_plan(context())['content']
        self.configure()
        draft['evidence'] = [{'id': 'foreign', 'title': 'secret', 'source': 'invented'}]
        with patch.object(eng, '_open', return_value=self.provider('```json\n' + json.dumps(draft) + '\n```')):
            result = eng.generate_plan(context())
        self.assertEqual(result['generation_mode'], 'ai')
        self.assertEqual(result['content']['evidence'][0]['id'], 'k1')
        self.assertEqual(result['usage']['total_tokens'], 60)
        draft['budget'] = [{'item': '广告', 'amount': 10000}]
        with patch.object(eng, '_open', return_value=self.provider(json.dumps(draft))):
            with self.assertRaises(RuntimeError):
                eng.generate_plan(context())

    def test_provider_input_excludes_foreign_data_and_sets_bounded_generation(self):
        eng = self.engine()
        draft = eng.generate_plan(context())['content']
        ctx = context()
        ctx['knowledge'].append(dict(ctx['knowledge'][0], workspace_id='w2', content='DO_NOT_LEAK'))
        self.configure()
        seen = []
        def transport(req, timeout):
            seen.append((req, timeout))
            return self.provider(json.dumps(draft))
        with patch.dict('os.environ', {'MARKETING_AI_TIMEOUT_SECONDS': '99999', 'MARKETING_AI_MAX_OUTPUT_TOKENS': '99999'}):
            with patch.object(eng, '_open', side_effect=transport):
                eng.generate_plan(ctx)
        body = json.loads(seen[0][0].data)
        self.assertNotIn('DO_NOT_LEAK', str(body))
        self.assertNotIn('tools', body)
        self.assertLessEqual(body['max_tokens'], 4000)
        self.assertLessEqual(seen[0][1], 60)

    def test_ai_review_cannot_override_observed_facts(self):
        eng = self.engine()
        ctx = dict(context(), analytics={'stats': {'revenue': 100, 'refunds': 20, 'orders': 2}, 'records': 1})
        baseline = eng.build_review(ctx)['content']['facts']
        self.configure()
        model = {'facts': [{'statement': '赚取999999元利润', 'evidence': 'invented'}],
                 'hypotheses': [{'statement': '入口位置可能影响咨询', 'validation': '对照观察入口点击'}],
                 'suggestions': [{'action': '测试报名入口位置', 'metric': '咨询数'}], 'limitations': []}
        with patch.object(eng, '_open', return_value=self.provider(json.dumps(model))):
            result = eng.build_review(ctx)
        self.assertEqual(result['content']['facts'], baseline)
        self.assertNotIn('999999', json.dumps(result, ensure_ascii=False))

    def test_negative_or_nonfinite_analytics_rejected(self):
        eng = self.engine()
        for value in (-1, float('nan'), 'fabricated'):
            with self.assertRaises(ValueError):
                eng.build_review(dict(context(), analytics={'stats': {'revenue': value}, 'records': 1}))


if __name__ == '__main__':
    unittest.main()
