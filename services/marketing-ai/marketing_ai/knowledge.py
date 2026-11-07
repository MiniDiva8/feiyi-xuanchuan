"""Deterministic lexical retrieval, after tenant/consent filtering.

Records are atomic: budget pressure drops an entire record, never a qualifier.
The unbudgeted eligible records remain available to local factual checks only.
"""
import json
import math
import re
import unicodedata
from collections import Counter

MAX_RECORDS = 40
MAX_RECORD_CHARS = 4000
MAX_CONTEXT_CHARS = 14000


def eligible(records, workspace_id):
    result = []
    for item in records or []:
        if not isinstance(item, dict) or item.get('workspace_id', workspace_id) != workspace_id:
            continue
        if item.get('confirmed') is not True or item.get('usage_scope') != 'marketing':
            continue
        # Preserve full provenance and content. No character slicing here.
        row = {k: str(item.get(k) or '') for k in ('id', 'title', 'content', 'source')}
        row.update(workspace_id=workspace_id, confirmed=True, usage_scope='marketing')
        result.append(row)
    return result


def _tokens(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    result = set(re.findall(r'[a-z][a-z0-9_-]+', text))
    for word in re.findall(r'[\u3400-\u9fff]+', text):
        result.update(word[i:i + 2] for i in range(len(word) - 1))
    return result


def select(records, ctx):
    offer, campaign, plan = ctx.get('offering') or {}, ctx.get('campaign') or {}, ctx.get('plan') or {}
    objectives = {'sales': '商品销售购买', 'registration': '课程报名体验', 'awareness': '品牌宣传介绍'}
    groups = [
        ('商品/课程', ' '.join(str(offer.get(k) or '') for k in ('name', 'description')), 8),
        ('活动目标', ' '.join(str(campaign.get(k) or '') for k in ('name', 'audience')) + objectives.get(campaign.get('objective'), ''), 3),
        ('表达要求', ctx.get('instructions') or '', 6),
    ]
    if plan.get('status') == 'approved':
        groups.append(('已批准方案', json.dumps(plan.get('content') or {}, ensure_ascii=False), 4))
    queries = [(label, _tokens(text), weight) for label, text, weight in groups]
    all_terms = set().union(*(tokens for _, tokens, _ in queries))
    prepared = []
    frequency = Counter()
    for row in records:
        title_terms = _tokens(row['title']) & all_terms
        content_terms = _tokens(row['content']) & all_terms
        found = title_terms | content_terms
        frequency.update(found)
        prepared.append((row, title_terms, found))
    ranked = []
    for row, title_terms, found in prepared:
        score, reasons = 0, []
        for label, terms, weight in queries:
            matches = terms & found
            if matches:
                reasons.append(label)
                score += weight * sum((1 + math.log((1 + len(records)) / (1 + frequency[t]))) *
                                      (2 if t in title_terms else 1) for t in sorted(matches))
        candidate = dict(row, selection_reason={'matched_fields': reasons or ['无直接词项匹配'], 'score': round(score, 6)})
        # IDs and canonical content break ties, never incoming creation order.
        stable = (row['id'], row['title'], row['source'], row['content'])
        ranked.append((-round(score, 6), stable, candidate))
    ranked.sort(key=lambda x: (x[0], x[1]))
    selected, used, skipped = [], 2, 0  # list brackets, plus separators below
    for _, _, candidate in ranked:
        size = len(json.dumps(candidate, ensure_ascii=False))
        if size > MAX_RECORD_CHARS or used + size + 2 > MAX_CONTEXT_CHARS or len(selected) >= MAX_RECORDS:
            skipped += 1
            continue
        selected.append(candidate)
        used += size + 2
    return selected, {'eligible': len(records), 'selected': len(selected), 'omitted': skipped}


def selection_check(ctx):
    counts = ctx.get('knowledge_selection') or {}
    notes = []
    for row in ctx.get('knowledge', [])[:3]:
        reason = '、'.join(row.get('selection_reason', {}).get('matched_fields', []))
        notes.append(f'资料「{row["title"]}」（ID：{row["id"]}；依据：{reason}）')
    return {'level': 'info', 'message':
            f'从全部{counts.get("eligible", 0)}条合格资料中按相关性选择{counts.get("selected", 0)}条；'
            '数量和长度预算只影响生成，不缩减本地事实核对依据。' + '；'.join(notes)}
