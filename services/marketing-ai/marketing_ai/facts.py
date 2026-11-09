"""Conservative checks of explicit, attributable commerce claims.

This is a bounded language recognizer, not a general fact verifier. Historical,
quoted, conditional, multi-item and unclear claims require human verification.
"""
import re
import unicodedata
from decimal import Decimal, InvalidOperation

NUMBER = r'(?:\d+(?:,\d{3})*(?:\.\d+)?(?:万|千)?|[零〇一二两三四五六七八九十百千万亿]+(?:点[零〇一二三四五六七八九]+)?)'
PRICE_LABEL = r'(?:现价|售价|价格|单价|报名费|课程费|学费|到手价|优惠价|仅售|只要|仅需)'
_PRICE = re.compile(rf'(?P<label>{PRICE_LABEL})\s*[:：为是]?\s*(?:人民币|RMB|CNY|[¥￥])?\s*(?P<number>{NUMBER})\s*(?P<unit>元|块)?(?P<minor>[零〇一二三四五六七八九\d])?(?:角)?', re.I)
_CURRENCY = re.compile(rf'(?:人民币|RMB|CNY|[¥￥])\s*(?P<prefix>{NUMBER})|(?P<number>{NUMBER})\s*(?P<unit>元|块)(?P<minor>[零〇一二三四五六七八九\d])?(?:角)?', re.I)
_QUANTITY = re.compile(rf'(?:库存|现货|剩余名额|名额|席位|余量|剩余|仅剩)\s*[:：为是]?\s*(?:还有|剩余|共|仅|有)?\s*(?P<number>{NUMBER})\s*(?:件|个|份|位|人|席|名|套)?')
_PLACE = re.compile(r'(?:上课地点|体验地点|上课地址|取货地址|自提地址|取货地点|门店地址|活动地点|地点|地址)\s*[:：为在是]\s*(?P<place>[^。！？；;，,\n]+)')
_SHIPPING = re.compile(r'(?:全国包邮|包邮|免费配送(?:上门)?|送货上门|快递发货|支持邮寄|支持快递|支持配送|免费送货|运费全免|无需运费|(?:支持|可以|仅支持|仅限|仅)?(?:到店)?自提)')
_UNCERTAIN = re.compile(r'待(?:确认|补充|核实|核验)|大约|约\s*\d|预计|可能|如果|假如|假设|建议|计划|考虑|例如|示例|举例|是否|[?？]|(?:元|块|件|人|位)起|左右|区间|(?:至|到|[-~～—])\s*[\d零一二两三四五六七八九十]')
_HISTORY = re.compile(r'原价|旧价|历史|去年|往年|以前|曾经|过去|原文|引用|有人说|顾客问|听说')
_MULTIPLE = re.compile(r'其他|其它|另款|另一|别款|多款|两款|分别|各自|套餐|套装|组合|竞品|[AB]款')
_CURRENT = re.compile(r'本品|本款|这款|该款|本商品|当前商品|本课程|本次课程|当前课程')
_NON_PRICE = re.compile(r'预算|运费|邮费|收入|退款|成本|补贴|押金|定金|订金|返现|优惠券|减免|满减')
_OTHER_UNIT = re.compile(r'\s*(?:分钟|小时|秒|天|年|个月|月|日|周|%|折|厘米|毫米|公里|米|公斤|千克|克|毫升|升|度|步|次|集|期|:\d)')
_CITIES = re.compile(r'北京|上海|天津|重庆|南京|杭州|广州|深圳|成都|武汉|西安|苏州|济南|长沙|郑州|福州|厦门|合肥|南昌|昆明|贵阳|南宁|海口|沈阳|大连|长春|哈尔滨|呼和浩特|乌鲁木齐|拉萨|西宁|银川|兰州|太原|石家庄')


def decimal_text(value):
    text = format(Decimal(str(value)), 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def number(text):
    text = text.replace(',', '').replace('两', '二').replace('〇', '零')
    if re.fullmatch(r'\d+(?:\.\d+)?[万千]?', text):
        multiplier = {'万': 10000, '千': 1000}.get(text[-1], 1)
        return Decimal(text[:-1] if multiplier != 1 else text) * multiplier
    digits = {c: i for i, c in enumerate('零一二三四五六七八九')}
    whole, _, fraction = text.partition('点')
    if not whole or any(c not in digits for c in fraction):
        raise ValueError('ambiguous amount')
    if not any(c in '十百千万亿' for c in whole):
        result = Decimal(''.join(str(digits[c]) for c in whole))
    else:
        # Colloquial 一百二/一千二 is ambiguous; do not guess 102 versus 120.
        if re.search(r'[百千万亿][一二三四五六七八九]$', whole):
            raise ValueError('ambiguous abbreviated number')
        total = section = digit = 0
        for char in whole:
            if char in digits:
                digit = digits[char]
            elif char in '十百千':
                section += (digit or 1) * {'十': 10, '百': 100, '千': 1000}[char]
                digit = 0
            else:
                section += digit
                total = (total + section) * {'万': 10000, '亿': 100000000}[char]
                section = digit = 0
        result = Decimal(total + section + digit)
    return result + (Decimal('0.' + ''.join(str(digits[c]) for c in fraction)) if fraction else 0)


def _quotes(text):
    spans = []
    for pattern in (r'“[^”]*”', r'「[^」]*」', r'『[^』]*』', r'"[^"\n]*"', r"'[^'\n]*'"):
        for match in re.finditer(pattern, text):
            prefix = text[max(0, match.start() - 12):match.start()]
            if not re.search(r'(?:口播|字幕|文案|正文|标题)\s*[:：]\s*$', prefix):
                spans.append(match.span())
    return spans


def _claims(clause):
    result, occupied = [], []
    for pattern, field in ((_PRICE, 'price'), (_CURRENCY, 'price'), (_QUANTITY, 'quantity'), (_PLACE, 'location'), (_SHIPPING, 'delivery')):
        for match in pattern.finditer(clause):
            if any(a <= match.start() < b for a, b in occupied):
                continue
            if field == 'price' and _NON_PRICE.search(clause[max(0, match.start() - 6):match.start()]):
                continue
            # Bare 仅需/只要/剩余 also introduce time, distances and discounts.
            # Recognized non-commerce units take precedence over numeric labels.
            if field in ('price', 'quantity') and _OTHER_UNIT.match(clause[match.end():]):
                continue
            if field == 'location' and re.search(r'收货|配送|买家|客户', clause[:match.start()]):
                continue
            if field == 'delivery' and re.search(r'(?:不|不支持|不能|不提供|无须)\s*$', clause[:match.start()]):
                continue
            if field in ('price', 'quantity'):
                try:
                    raw = match.groupdict().get('number') or match.groupdict().get('prefix')
                    value = number(raw)
                    minor = match.groupdict().get('minor')
                    if minor:
                        value += number(minor) / 10
                except (ValueError, KeyError, InvalidOperation):
                    value = None
            else:
                value = match.group('place').strip() if field == 'location' else match.group(0)
            result.append((field, match.start(), match.end(), value))
            occupied.append(match.span())
    for match in re.finditer(r'(?:本课程|报名费|课程费|学费|售价)\s*[:：为是]?\s*免费(?:报名)?|免费报名', clause):
        result.append(('price', match.start(), match.end(), Decimal(0)))
    return sorted(result, key=lambda c: c[1])


def _attribution(clause, start, end, name, previous, quoted):
    prefix = clause[:start]
    if quoted:
        return '引用文字，未确认是当前宣传主张', previous
    if _UNCERTAIN.search(clause):
        return '条件、估计或待确认表述', previous
    if _HISTORY.search(prefix):
        return '历史价格或引用说明', 'historical'
    if _MULTIPLE.search(clause):
        return '涉及多个项目或组合条件', 'unclear'
    if (name and name in prefix) or _CURRENT.search(prefix):
        return '', 'current'
    if re.match(r'\s*(?:现价|现在|当前|目前|如今)', clause):
        return '', 'current'
    # A named prefix such as 纸扇售价 is not necessarily the bound offering.
    cleaned = re.sub(r'^[\s#*【】\d.、]+', '', prefix)
    cleaned = re.sub(r'^(?:商品资料|项目资料|正确详情|口播|字幕|文案|正文|标题)\s*[:：]\s*[“\"\s]*', '', cleaned)
    cleaned = re.sub(r'^(?:现在|今日|今天|本次|当前|优惠|促销|活动|限时|原|现)', '', cleaned)
    if cleaned and not re.fullmatch(r'[\s:：\-—“”"\d¥￥.]*', cleaned):
        return '项目归属不明确', 'unclear'
    if previous == 'unclear':
        return '前文涉及其他项目，归属待确认', previous
    if previous == 'historical':
        return '前文为历史条件，当前适用性待确认', previous
    return '', 'current'


def _place_comparison(claim, actual):
    clean = lambda s: re.sub(r'\s|[。.]$', '', s)
    claim, actual = clean(claim), clean(actual)
    if claim == actual:
        return 'same'
    a, b = set(_CITIES.findall(claim)), set(_CITIES.findall(actual))
    if a and b and a.isdisjoint(b):
        return 'conflict'
    road = r'([\u3400-\u9fff]+?(?:路|街|巷))\s*(\d+)号'
    a, b = re.search(road, claim), re.search(road, actual)
    if a and b and a[1] == b[1] and a[2] != b[2]:
        return 'conflict'
    return 'unclear'  # Aliases, abbreviated locations and room changes need review.


def _delivery_comparison(claim, actual):
    pickup_only = bool(re.search(r'(?:仅|只|只限|仅限)(?:支持)?(?:到店)?自提|不支持(?:邮寄|配送|快递)', actual))
    shipping_only = bool(re.search(r'不支持(?:到店)?自提|仅(?:支持)?(?:邮寄|快递|配送)', actual))
    is_pickup = '自提' in claim
    if (pickup_only and not is_pickup) or (shipping_only and is_pickup):
        return 'conflict'
    if ('包邮' in claim or '免费' in claim or '运费全免' in claim or '无需运费' in claim) and re.search(r'运费自理|邮费自理|不包邮|运费[为是:：]?\s*[1-9]', actual):
        return 'conflict'
    if claim in actual or (pickup_only and is_pickup):
        return 'same'
    return 'unclear'


def check(text, ctx):
    text = unicodedata.normalize('NFKC', text)
    offer = ctx.get('offering') or {}
    name = str(offer.get('name') or '')
    labels = {'price': '价格', 'quantity': '名额' if offer.get('kind') == 'course' else '库存', 'location': '地点', 'delivery': '履约'}
    quotes = _quotes(text)
    result, seen, subject = [], set(), 'current'
    # Do not split decimal points or thousands separators inside numbers.
    boundaries = list(re.finditer(r'[。！？;；\n]|(?<!\d)[,，]|[,，](?!\d)', text))
    cursor = 0
    for boundary in boundaries + [None]:
        stop = boundary.start() if boundary else len(text)
        clause = text[cursor:stop]
        if name and name in clause and not _MULTIPLE.search(clause):
            subject = 'current'
        heading = re.fullmatch(r'\s*(?:商品|课程|项目)(?:名称)?[:：]\s*(.+)', clause)
        if heading and name and name not in heading[1]:
            subject = 'unclear'
        for field, start, end, value in _claims(clause):
            claim = clause[start:end]
            quoted = any(a <= cursor + start < b for a, b in quotes)
            reason, subject = _attribution(clause, start, end, name, subject, quoted)
            if offer.get('kind') == 'product' and re.search(r'本课程|报名费|学费|课程费', clause):
                reason = '文案提及课程，当前关联的是商品，归属不明确'
            actual = offer.get(field)
            label = labels[field]
            if not name or actual is None or actual == '':
                reason = f'缺少当前项目的{label}依据'
            if value is None:
                reason = '数字写法有歧义'
            if reason:
                level, message = 'warning', f'待核验{label}：“{claim}”；{reason}，未自动判错。'
            else:
                if field in ('price', 'quantity'):
                    outcome = 'same' if value == Decimal(str(actual)) else 'conflict'
                    evidence = decimal_text(actual) + ('元' if field == 'price' else '')
                elif field == 'location':
                    outcome, evidence = _place_comparison(value, str(actual)), str(actual)
                else:
                    outcome, evidence = _delivery_comparison(value, str(actual)), str(actual)
                if outcome == 'same':
                    continue
                level = 'error' if outcome == 'conflict' else 'warning'
                message = (f'{label}冲突：“{claim}”与「{name}」商家资料中的{label}“{evidence}”不一致，请修订后重新审核。'
                           if outcome == 'conflict' else f'待核验{label}：“{claim}”；已提供依据为“{evidence}”，现有规则无法确定二者是否一致。')
            if (level, message) not in seen:
                result.append({'level': level, 'message': message})
                seen.add((level, message))
        if boundary and boundary[0] in '。！？;；\n' and subject == 'historical':
            subject = 'current'
        cursor = stop + 1
    return result
