"""Evidence and missing-data boundaries for goal-specific activity reviews."""
import copy
import importlib
import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'services' / 'marketing-ai'))
engine = importlib.import_module('marketing_ai.engine')


def review_context(objective='registration', stats=None, records=2):
    return {
        'workspace': {'id': 'shop-1', 'name': '测试工坊'},
        'campaign': {'id': 'campaign-1', 'workspace_id': 'shop-1', 'objective': objective},
        'knowledge': [],
        'analytics': {'workspace_id': 'shop-1', 'records': records, 'stats': stats or {}},
    }


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict('os.environ', {'MARKETING_AI_API_KEY': ''})
        self.env.start()
        self.addCleanup(self.env.stop)

    def content(self, *args, **kwargs):
        return engine.build_review(review_context(*args, **kwargs))['content']

    def test_course_ratios_have_numeric_evidence_and_goal_specific_next_step(self):
        content = self.content(stats={'inquiries': 10, 'registrations': 4, 'checkins': 3})
        facts = content['facts']
        attendance = next(row for row in facts if '到场/报名计数比' in row['statement'])
        self.assertIn('75%', attendance['statement'])
        self.assertIn('checkins(3) / registrations(4)', attendance['evidence'])
        self.assertTrue(any('报名/咨询计数比' in row['statement'] and '40%' in row['statement'] for row in facts))
        self.assertTrue(any('去重' in line and '转化率' in line for line in content['limitations']))
        self.assertTrue(any('到场' in row['metric'] for row in content['suggestions']))
        self.assertFalse(any('订单/咨询计数比' in row['statement'] for row in facts))

    def test_sales_review_uses_orders_without_treating_course_counts_as_sales(self):
        content = self.content('sales', {'inquiries': 10, 'orders': 5, 'registrations': 9, 'checkins': 8})
        self.assertTrue(any('订单/咨询计数比' in row['statement'] and '50%' in row['statement'] for row in content['facts']))
        self.assertFalse(any('到场/报名计数比' in row['statement'] for row in content['facts']))
        self.assertTrue(any('订单' in row['metric'] and '退款' in row['metric'] for row in content['suggestions']))

    def test_missing_metrics_remain_unknown_instead_of_zero(self):
        content = self.content(stats={'impressions': 200})
        self.assertFalse(any('计数比' in row['statement'] for row in content['facts']))
        self.assertFalse(any(row['statement'].startswith('报名：0') for row in content['facts']))
        missing = '\n'.join(content['limitations'])
        self.assertIn('报名', missing)
        self.assertIn('缺少', missing)
        self.assertTrue(any('补齐' in row['action'] for row in content['suggestions']))

    def test_zero_denominators_are_explained_without_dividing_or_hiding_zero(self):
        content = self.content(stats={'inquiries': 0, 'registrations': 0, 'checkins': 0})
        self.assertFalse(any('计数比' in row['statement'] for row in content['facts']))
        self.assertTrue(any(row['statement'] == '报名：0。' for row in content['facts']))
        self.assertTrue(any('分母为0' in line for line in content['limitations']))

    def test_no_records_cannot_turn_leftover_stats_into_performance(self):
        content = self.content(stats={'inquiries': 10, 'registrations': 4, 'checkins': 3}, records=0)
        self.assertEqual(len(content['facts']), 1)
        self.assertTrue(any('尚无实际指标数据' in line for line in content['limitations']))
        self.assertTrue(any('录入' in row['action'] for row in content['suggestions']))

    def test_empty_review_only_asks_for_the_first_record_even_with_a_provider(self):
        cases = {'registration': ('咨询', '报名', '到场'),
                 'sales': ('咨询', '订单', '收入'),
                 'awareness': ('曝光', '互动')}
        for objective, metrics in cases.items():
            with self.subTest(objective=objective), patch.object(engine, '_model') as provider:
                ctx = review_context(objective, stats={'revenue': 500}, records=0)
                result = engine.build_review(ctx)
                provider.assert_not_called()
                self.assertEqual(result['generation_mode'], 'template')
                self.assertEqual(result['usage']['total_tokens'], 0)
                content = result['content']
                self.assertEqual([row['evidence'] for row in content['facts']], ['analytics.records=0'])
                self.assertEqual(content['hypotheses'], [])
                action, = content['suggestions']
                for metric in metrics:
                    self.assertIn(metric, action['action'])
                self.assertEqual(len(content['limitations']), 1)

    def test_unknown_attribution_and_refunds_remain_separate_from_profit(self):
        content = self.content('sales', {'revenue': 0.3, 'refunds': 0.1, 'unknown_revenue': 0.1, 'spend': 0.05})
        net = next(row for row in content['facts'] if row['statement'].startswith('收入扣除退款'))
        self.assertEqual(net['statement'], '收入扣除退款为0.2元。')
        share = next(row for row in content['facts'] if '归因未知收入占录入收入比' in row['statement'])
        self.assertIn('33.33%', share['statement'])
        self.assertIn('unknown_revenue(0.1) / revenue(0.3)', share['evidence'])
        self.assertTrue(any('归因' in row['action'] for row in content['suggestions']))
        self.assertTrue(any('利润' in line for line in content['limitations']))

    def test_decimal_money_is_calculated_without_float_cancellation(self):
        content = self.content('sales', {'revenue': Decimal('100000000000.03'), 'refunds': Decimal('100000000000.01')})
        self.assertTrue(any(row['statement'] == '收入扣除退款为0.02元。' for row in content['facts']))

    def test_counts_over_denominator_are_not_clamped_or_called_conversion(self):
        content = self.content('sales', {'inquiries': 2, 'orders': 3})
        ratio = next(row for row in content['facts'] if '订单/咨询计数比' in row['statement'])
        self.assertIn('150%', ratio['statement'])
        self.assertTrue(any('超过100%' in line for line in content['limitations']))

    def test_foreign_analytics_are_rejected_before_provider(self):
        ctx = review_context(stats={'registrations': 5})
        ctx['analytics']['workspace_id'] = 'other-shop'
        with patch.object(engine, '_model') as model:
            with self.assertRaises(ValueError):
                engine.build_review(ctx)
            model.assert_not_called()

    def test_model_cannot_remove_numeric_facts_or_required_limitations_and_actions(self):
        ctx = review_context(stats={'inquiries': 10, 'registrations': 4, 'checkins': 3})
        original = copy.deepcopy(ctx)
        baseline = engine.build_review(ctx)['content']
        generated = {'facts': [{'statement': '虚构成效', 'evidence': 'invented'}],
                     'hypotheses': [{'statement': '入口可能影响报名', 'validation': '同口径单变量测试'}],
                     'suggestions': [{'action': '比较两个入口位置', 'metric': '咨询数'}], 'limitations': []}
        with patch.object(engine, '_model', return_value=(generated, {'total_tokens': 10})):
            result = engine.build_review(ctx)
        self.assertEqual(result['generation_mode'], 'ai')
        self.assertEqual(result['content']['facts'], baseline['facts'])
        self.assertEqual(result['content']['limitations'], baseline['limitations'])
        self.assertTrue(all(row in result['content']['suggestions'] for row in baseline['suggestions']))
        self.assertNotIn('虚构成效', json.dumps(result, ensure_ascii=False))
        self.assertEqual(ctx, original)


if __name__ == '__main__':
    unittest.main()
