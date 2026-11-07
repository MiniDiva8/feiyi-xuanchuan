"""Explain backend-provided aggregate changes without inferring causality."""
from datetime import date
from decimal import Decimal, InvalidOperation


def _number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return value if value.is_finite() and value >= 0 else None


def _text(value):
    text = format(value, 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def analyze(analytics):
    facts, actions, limits, channel_facts = [], [], [], []
    rows = analytics.get('trends')
    dates = {}
    duplicate = set()
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('date'), str):
                continue
            day = row['date']
            try:
                if date.fromisoformat(day).isoformat() != day:
                    continue
            except ValueError:
                continue
            if day in dates:
                duplicate.add(day)
            dates[day] = row
    for day in duplicate:
        dates.pop(day, None)
    ordered = sorted(dates)
    if duplicate:
        limits.append('按日期汇总中存在重复日期，已排除该日期，不能把重复项当作不同日期比较。')
    if len(ordered) < 2:
        limits.append('目前没有两个可比较的不同日期汇总，无法判断随时间的变化；两条记录也可能属于同一天。')
        actions.append({'action': '在不同日期录入同渠道、同来源和相同统计口径的数据，再重新生成复盘。',
                        'metric': '记录日期、渠道、统计区间及曝光、收入、花费'})
    else:
        first_day, last_day = ordered[-2:]
        before, after = dates[first_day], dates[last_day]
        for key, label, unit in (('impressions', '曝光', ''), ('revenue', '收入', '元'), ('spend', '营销花费', '元')):
            first, last = _number(before.get(key)), _number(after.get(key))
            if first is None or last is None:
                limits.append(f'最近两个日期的{label}汇总缺失或无效，无法比较该指标。')
                continue
            delta = last - first
            direction = '增加' if delta > 0 else '减少' if delta < 0 else '持平'
            amount = f'{direction}{_text(abs(delta))}{unit}' if delta else '持平'
            rate = (f'；前值为0，基数为0不计算百分比' if first == 0 else
                    f'；变化{_text((delta / first * 100).quantize(Decimal("0.01")))}%')
            facts.append({'statement': f'录入日汇总{label}：{first_day}为{_text(first)}{unit}，{last_day}为{_text(last)}{unit}，{amount}{rate}。',
                          'evidence': f'analytics.trends：{first_day} {key}={_text(first)}；{last_day} {key}={_text(last)}；差值=后值−前值；百分比=差值/前值。'})
            if key == 'impressions' and delta < 0:
                actions.append({'action': '曝光录入汇总减少：先核对两个日期的渠道、发布作品和统计区间；下一轮只调整开场，继续记录同口径曝光。', 'metric': '同渠道、同区间曝光和发布作品；原因待验证'})
            elif key == 'impressions' and delta > 0:
                actions.append({'action': '曝光录入汇总增加：先核对两个日期的渠道和统计区间，记录当时的开场与发布时间，下一轮只测试一个变量。', 'metric': '同渠道、同区间曝光和互动；不能据此认定原因'})
            elif key == 'revenue' and delta != 0:
                actions.append({'action': '收入录入汇总发生变化：核对对应订单、退款、来源及统计区间，再决定是否调整承接方式。', 'metric': '同口径收入、订单、退款和未知归因金额'})
        limits.append('比较的是最近两个有记录日期的跨渠道录入合计，可能隔天数不一或渠道构成不同；先核对同渠道、同统计区间及增量/累计口径，不能据此认定效果或原因。')
    if analytics.get('records'):
        limits.append('当前录入和汇总流程可能把未填写的指标补零；显示的0可能并非实际为零。累计快照可能被重复相加，须先核对原始记录。')

    channels = analytics.get('channels')
    if isinstance(channels, list):
        for row in channels:
            if not isinstance(row, dict) or not isinstance(row.get('channel'), str):
                continue
            name, impressions = row['channel'].strip(), _number(row.get('impressions'))
            if not name or len(name) > 100 or impressions is None:
                continue
            channel_facts.append({'statement': f'渠道「{name}」录入汇总曝光：{_text(impressions)}。',
                                  'evidence': f'analytics.channels 中该渠道 impressions={_text(impressions)}；覆盖整个活动的已录入记录。'})
        if len(channel_facts) > 1:
            limits.append('渠道汇总可能覆盖不同天数、预算或作品，不能直接用总量判定渠道优劣；当前数据无法还原单个渠道的逐日变化。')
    facts.extend(channel_facts)
    return facts, actions, limits, channel_facts
