"""Entirely fictional merchant data; reserved example domains, no real accounts."""
import json


def script_context(kind='product'):
    course = kind == 'course'
    return {
        'workspace': {'id': 'fictional-shop', 'name': '虚构测试工坊'},
        'campaign': {'id': 'fictional-campaign', 'workspace_id': 'fictional-shop',
                     'name': '虚构测试：周末手作体验' if course else '虚构测试：手作日常',
                     'objective': 'registration' if course else 'sales', 'offering_id': 'fictional-offer',
                     'audience': '希望了解手作的本地成年人', 'start_date': '2026-11-07',
                     'end_date': '2026-11-14', 'budget': 100, 'channels': ['抖音'], 'notes': ''},
        'offering': {'id': 'fictional-offer', 'workspace_id': 'fictional-shop', 'kind': kind,
                     'name': '扎染方巾体验课' if course else '竹编杯垫',
                     'description': '体验绑扎和染色，完成一块方巾。' if course else '竹条交织成圆形杯垫，用于桌面放置茶杯。',
                     'price': 128 if course else 48, 'quantity': 6 if course else 20,
                     'location': '虚构测试街1号体验室' if course else '虚构测试工坊',
                     'delivery': '11月8日14点开课，现场体验90分钟；材料包含在费用内。' if course
                                 else '仅到店自提；付款后与商家确认取货时间。',
                     'conversion_url': 'https://example.org/fictional/book' if course else 'https://example.org/fictional/buy'},
        'knowledge': [{'id': 'fictional-source', 'workspace_id': 'fictional-shop', 'title': '虚构测试商家确认资料',
                       'content': '课程时长90分钟，包含绑扎与染色体验。' if course else '杯垫使用竹条交织，成品表面保留编织纹路。',
                       'source': '虚构测试资料卡，不是真实商家资质或经营数据',
                       'confirmed': True, 'usage_scope': 'marketing'}],
        'plan': {'id': 'fictional-plan', 'workspace_id': 'fictional-shop', 'campaign_id': 'fictional-campaign',
                 'status': 'approved', 'content': {
                     'theme': '先看体验内容，再决定报名' if course else '先看编织细节，再核对购买条件',
                     'channels': [{'channel': '抖音', 'reason': '展示实际内容',
                                   'content_ideas': ['绑扎体验、真实场次、报名说明'] if course else ['杯垫纹路、自提说明、购买入口']}]}},
        'kind': 'script', 'channel': '抖音', 'instructions': '',
    }


def provider_response(value):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, limit=-1):
            return json.dumps({'choices': [{'message': {'content': value if isinstance(value, str) else json.dumps(value)}}],
                               'usage': {'prompt_tokens': 100, 'completion_tokens': 300, 'total_tokens': 400}}).encode()
    return Response()
