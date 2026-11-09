"""Shooting output and provider validation through the public generate_asset API."""
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'services/marketing-ai'))
from marketing_ai import engine
from marketing_ai.shooting_script import speech_units
from script_fixtures import script_context, provider_response


class ShootingScriptTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict('os.environ', {'MARKETING_AI_API_KEY': '', 'MARKETING_AI_MODEL': 'mock-script-model',
                                           'MARKETING_AI_BASE_URL': 'https://provider.example/v1', 'MARKETING_AI_THINKING': ''})
        self.env.start()
        self.addCleanup(self.env.stop)

    def model(self, context, transform=lambda value, request: value):
        def respond(req, timeout):
            data = json.loads(req.data)
            user = json.loads(data['messages'][1]['content'])
            self.request = user
            return provider_response(transform(copy.deepcopy(user['output_structure']), user))
        with patch.dict('os.environ', {'MARKETING_AI_API_KEY': 'synthetic-test-key'}):
            with patch.object(engine, '_open', side_effect=respond) as transport:
                result = engine.generate_asset(context)
        self.assertEqual(transport.call_count, 1)
        return result

    def test_product_and_course_templates_are_complete_and_materially_different(self):
        results = []
        for kind in ('product', 'course'):
            with self.subTest(kind=kind), patch.object(engine, '_open') as transport:
                ctx = script_context(kind)
                result = engine.generate_asset(ctx)
                transport.assert_not_called()
                results.append(result)
                self.assertEqual(result['generation_mode'], 'template')
                self.assertIn('【模板脚本｜未调用模型】', result['body'])
                self.assertEqual(result['content']['duration_seconds'], 30)
                self.assertEqual(len(result['content']['shots']), 5)
                self.assertTrue(all(isinstance(s, str) for s in result['content']['shots']))
                self.assertEqual(result['content']['evidence'][0]['id'], 'fictional-source')
                self.assertIn(ctx['offering']['description'], result['body'])
                self.assertIn(ctx['offering']['delivery'], result['body'])
                self.assertIn(ctx['plan']['content']['theme'], result['body'])
                self.assertIn(ctx['offering']['conversion_url'], result['body'])
                self.assertIn(ctx['offering']['conversion_url'], result['content']['storyboard'][-1]['subtitle'])
                self.assertIn('不是课程场次', result['body'])
                self.assertIn('未验证抖音挂链能力', result['body'])
                for key in ('title', 'hook', 'details', 'caption', 'cta'):
                    self.assertIn(result['content'][key], result['body'])
                for group in result['content']['preparation'].values():
                    for item in group:
                        self.assertIn(item, result['body'])
                for shot in result['content']['storyboard']:
                    for key in ('visual', 'voiceover', 'subtitle'):
                        self.assertIn(shot[key], result['body'])
                    self.assertLessEqual(speech_units(shot['voiceover']), 4 * (shot['end_second'] - shot['start_second']))
                self.assertFalse(any(c['level'] == 'error' for c in result['checks']))
        self.assertIn('购买', results[0]['content']['cta'])
        self.assertIn('报名', results[1]['content']['cta'])
        self.assertNotEqual(results[0]['content']['storyboard'][1]['voiceover'], results[1]['content']['storyboard'][1]['voiceover'])

    def test_missing_facts_never_become_zero_price_seats_or_invented_link(self):
        ctx = script_context('course')
        for field in ('price', 'quantity', 'location', 'delivery', 'conversion_url'):
            ctx['offering'].pop(field)
        ctx['knowledge'] = []
        result = engine.generate_asset(ctx)
        self.assertIn('价格：待补充', result['body'])
        self.assertIn('名额：待补充', result['body'])
        self.assertIn('报名入口：待补充', result['body'])
        self.assertIn('补齐', result['content']['cta'])
        self.assertNotIn('0元', result['body'])
        self.assertNotIn('https://', result['body'])
        self.assertEqual(len(result['content']['storyboard']), 5)
        ctx['offering'] = None
        self.assertIn('项目名称待补充', engine.generate_asset(ctx)['body'])

    def test_template_selects_confirmed_fact_matching_approved_channel_direction(self):
        ctx = script_context('course')
        ctx['knowledge'].insert(0, dict(ctx['knowledge'][0], id='unrelated', content='工坊周一整理库房。'))
        result = engine.generate_asset(ctx)
        self.assertIn('绑扎', result['content']['storyboard'][2]['voiceover'])
        self.assertNotIn('库房', result['content']['storyboard'][2]['voiceover'])

    def test_zero_price_is_real_but_zero_stock_stops_purchase_cta(self):
        ctx = script_context()
        ctx['offering'].update(price=0, quantity=0)
        result = engine.generate_asset(ctx)
        self.assertIn('价格：0元', result['body'])
        self.assertIn('库存为0，暂停购买引导', result['body'])
        self.assertIn('核实后再发布', result['content']['cta'])

    def test_price_and_stock_are_not_rounded_to_six_significant_digits(self):
        ctx = script_context()
        ctx['offering'].update(price=123456.78, quantity=1234567)
        result = engine.generate_asset(ctx)
        self.assertIn('价格：123456.78元', result['body'])
        self.assertIn('库存：1234567', result['body'])
        self.assertNotIn('123457元', result['body'])

    def test_unsafe_urls_are_rejected_instead_of_used_as_entrypoints(self):
        for url in ('javascript:alert(1)', 'https://person:secret@example.org', 'not-a-url'):
            with self.subTest(url=url):
                ctx = script_context()
                ctx['offering']['conversion_url'] = url
                with self.assertRaises(ValueError):
                    engine.generate_asset(ctx)

    def test_long_factual_sentence_is_not_cut_into_a_new_claim_or_overlong_speech(self):
        ctx = script_context()
        ctx['offering']['name'] = '虚构测试长项目名称' * 20
        ctx['offering']['description'] = '此商品只适用于明确约定的使用场景' * 30 + '，其他条件下不可使用。'
        result = engine.generate_asset(ctx)
        self.assertIn(ctx['offering']['description'], result['content']['details'])
        self.assertNotIn(ctx['offering']['description'][:32], result['content']['storyboard'][1]['voiceover'])

    def test_foreign_unconfirmed_internal_knowledge_never_reaches_output_or_provider(self):
        ctx = script_context()
        for fields in ({'workspace_id': 'other'}, {'confirmed': False}, {'usage_scope': 'internal'}):
            ctx['knowledge'].append(dict(ctx['knowledge'][0], id='secret', content='PRIVATE_SENTINEL', **fields))
        for result in (engine.generate_asset(ctx), self.model(ctx)):
            self.assertNotIn('PRIVATE_SENTINEL', json.dumps(result))
            self.assertEqual([x['id'] for x in result['content']['evidence']], ['fictional-source'])
        self.assertNotIn('PRIVATE_SENTINEL', json.dumps(self.request))

    def test_foreign_entities_wrong_bindings_and_unapproved_plan_fail_before_model(self):
        cases = []
        for entity in ('campaign', 'offering', 'plan'):
            ctx = script_context()
            ctx[entity]['workspace_id'] = 'other'
            cases.append(ctx)
        for entity, field, value in [('plan', 'campaign_id', 'other'), ('plan', 'status', 'draft'), ('plan', 'status', None),
                                     ('offering', 'id', 'wrong-offer'), ('offering', 'kind', 'course')]:
            ctx = script_context()
            ctx[entity][field] = value
            cases.append(ctx)
        ctx = script_context()
        ctx['plan']['content']['channels'][0]['channel'] = '微信'
        cases.append(ctx)
        for ctx in cases:
            with self.subTest(ctx=ctx), patch.object(engine, '_open') as transport:
                with self.assertRaises(ValueError):
                    self.model(ctx)
                transport.assert_not_called()

    def test_model_can_select_grounded_hook_and_reorder_middle_shots(self):
        def edit(value, request):
            option = next(c for c in request['data']['script_candidates'] if c['candidate_id'] == 'hook-2')
            value['storyboard'][0].update({k: v for k, v in option.items() if k != 'role'})
            left, right = value['storyboard'][1:3]
            for field in ('candidate_id', 'visual', 'voiceover', 'subtitle'):
                left[field], right[field] = right[field], left[field]
            return value
        result = self.model(script_context(), edit)
        self.assertEqual(result['generation_mode'], 'ai')
        self.assertEqual(result['usage']['total_tokens'], 400)
        self.assertEqual(result['content']['storyboard'][0]['candidate_id'], 'hook-2')
        self.assertTrue(result['content']['storyboard'][1]['candidate_id'].startswith('evidence'))
        self.assertIn('【AI编排脚本', result['body'])
        self.assertNotIn('【模板脚本', result['body'])

    def test_model_cannot_invent_facts_in_any_shot_field(self):
        claims = ['只要1元', '位于虚构以外的新地址', '仅剩999个名额', '国家级非遗传承人亲授',
                  '付款后全国包邮', '点小黄车立即买', 'https://invented.example/pay', '保证爆款']
        for field in ('visual', 'voiceover', 'subtitle'):
            for claim in claims:
                def edit(value, request):
                    value['storyboard'][1][field] = claim
                    return value
                with self.subTest(field=field, claim=claim), self.assertRaisesRegex(RuntimeError, '未回退'):
                    self.model(script_context(), edit)

    def test_malformed_shots_and_timeline_fail_explicitly(self):
        mutations = [lambda v: v.update(duration_seconds=31),
                     lambda v: v.update(storyboard=[]),
                     lambda v: v['storyboard'][0].pop('voiceover'),
                     lambda v: v['storyboard'][0].update(voiceover=''),
                     lambda v: v['storyboard'][0].update(candidate_id='invented'),
                     lambda v: v['storyboard'][1].update(start_second=2),
                     lambda v: v['storyboard'][1].update(start_second=4),
                     lambda v: v['storyboard'][0].update(start_second=-1),
                     lambda v: v['storyboard'][-1].update(end_second=31),
                     lambda v: v['storyboard'][-1].update(end_second=29),
                     lambda v: v['storyboard'][0].update(end_second=0),
                     lambda v: v['storyboard'][0].update(end_second=True),
                     lambda v: v['storyboard'][0].update(end_second='3'),
                     lambda v: v['storyboard'][0].update(end_second=float('nan')),
                     lambda v: v['storyboard'][0].update(end_second=10**400),
                     lambda v: v.update(body='unvalidated text'),
                     lambda v: v['storyboard'].__setitem__(1, copy.deepcopy(v['storyboard'][2]))]
        for mutation in mutations:
            def edit(value, request):
                mutation(value)
                return value
            with self.subTest(mutation=mutation), self.assertRaisesRegex(RuntimeError, '未回退'):
                self.model(script_context(), edit)

    def test_timeline_can_be_contiguous_but_still_too_fast_to_speak(self):
        def too_fast(value, request):
            value['storyboard'][0]['end_second'] = 1
            value['storyboard'][1]['start_second'] = 1
            return value
        with self.assertRaisesRegex(RuntimeError, '未回退'):
            self.model(script_context(), too_fast)

    def test_provider_timeout_or_invalid_json_is_not_template_success(self):
        with patch.dict('os.environ', {'MARKETING_AI_API_KEY': 'synthetic-test-key'}):
            with patch.object(engine, '_open', side_effect=TimeoutError('private provider detail')):
                with self.assertRaisesRegex(RuntimeError, '未回退') as error:
                    engine.generate_asset(script_context())
            self.assertNotIn('private provider detail', str(error.exception))
            with patch.object(engine, '_open', return_value=provider_response('not json')):
                with self.assertRaises(RuntimeError):
                    engine.generate_asset(script_context())

    def test_unconfirmed_credentials_and_guaranteed_hits_are_not_a_usable_template(self):
        for claim in ('保证爆款', '国家级非遗传承人亲授'):
            ctx = script_context()
            ctx['offering']['description'] = claim
            with self.subTest(claim=claim), self.assertRaises(ValueError):
                engine.generate_asset(ctx)


if __name__ == '__main__':
    unittest.main()
