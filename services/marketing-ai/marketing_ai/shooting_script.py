"""Source-bound shooting scripts, rendered into the existing editable asset body.

The model edits a shot list using supplied candidates and timings. Factual copy
is deliberately not free-form: a candidate's visual, speech and subtitle must
be returned verbatim. This makes invented prices/places/fulfilment/links fail
validation rather than merely appending the correct facts to false claims.
"""
from __future__ import annotations

import copy
import math
import re
from decimal import Decimal


DURATION = 30
MAX_SPEECH_UNITS_PER_SECOND = 4
_ROLES = ('hook', 'project', 'evidence', 'terms', 'cta')


def _line(value):
    return ' '.join(str(value or '').split())


def speech_units(text):
    # Conservative Chinese rehearsal budget; also counts letters/digits.
    return len(re.findall(r'\w', text, flags=re.UNICODE))


def _excerpt(text, limit):
    """Never truncate a factual sentence or turn a qualifier into a claim."""
    text = _line(text)
    for sentence in re.split(r'(?<=[。！？；])', text):
        if sentence and speech_units(sentence) <= limit and not re.search(r'https?://', sentence):
            return sentence
    return ''


def _amount(value):
    # Already validated by engine._context; don't invent zeros for absent keys.
    if value is None:
        return '待补充'
    text = format(Decimal(str(value)), 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def prepare(ctx):
    campaign, offer = ctx['campaign'], ctx['offering'] or {}
    objective = campaign.get('objective')
    expected = {'sales': 'product', 'registration': 'course'}.get(objective)
    if offer and expected and offer.get('kind') != expected:
        raise ValueError('offering kind does not match campaign objective')
    course = offer.get('kind') == 'course' or (not offer and objective == 'registration')
    action, quantity_label = ('报名', '名额') if course else ('购买', '库存')
    name = _line(offer.get('name')) or '项目名称待补充'
    description = _line(offer.get('description'))
    location, delivery = _line(offer.get('location')), _line(offer.get('delivery'))
    url = _line(offer.get('conversion_url'))
    missing = []
    for key, label in [('name', '项目名称'), ('description', '项目内容'), ('price', '价格'),
                       ('quantity', quantity_label), ('location', '地点'), ('delivery', '履约说明'),
                       ('conversion_url', action + '入口')]:
        if key not in offer or offer[key] is None or (isinstance(offer[key], str) and not offer[key].strip()):
            missing.append(label)
    knowledge = ctx['knowledge']
    if not knowledge:
        missing.append('已确认且允许营销使用的来源资料')
    plan = ctx.get('plan') or {}
    if plan and plan.get('status') != 'approved':
        raise ValueError('script requires an approved plan')
    channel = ctx['channel'] or '渠道待补充'
    if campaign.get('channels') and channel not in campaign['channels']:
        raise ValueError('script channel is outside campaign')
    plan_content = plan.get('content') or {}
    channels = plan_content.get('channels') or []
    channel_plan = next((x for x in channels if x.get('channel') == channel), None)
    if plan and not channel_plan:
        raise ValueError('script channel is outside plan')
    if not plan:
        missing.append('已批准方案（产品接口生成前必须批准）')

    # Prefer confirmed material related to the approved channel direction. This
    # affects selection only: we still quote a whole source sentence verbatim.
    direction = _line(plan_content.get('theme')) + ' '.join((channel_plan or {}).get('content_ideas', []))
    pairs = {direction[i:i + 2] for i in range(len(direction) - 1)
             if re.fullmatch(r'[\w]{2}', direction[i:i + 2])}
    knowledge = sorted(knowledge, key=lambda item: -sum(pair in item['content'] for pair in pairs))

    terms = [f'项目：{name}', f'项目内容：{description or "待补充"}',
             f'价格：{_amount(offer.get("price"))}' + ('元' if offer.get('price') is not None else ''),
             f'{quantity_label}：{_amount(offer.get("quantity"))}（拍摄与发布前重新核实）',
             f'地点：{location or "待补充"}', f'履约说明：{delivery or "待补充"}',
             f'{action}入口：{url or "待补充；暂勿引导交易"}']
    ready = bool(url and offer.get('quantity', 0) > 0 and not missing)
    cta = (f'请先核对详情，再通过商家确认的入口{action}。' if ready
           else '信息尚未齐备，请补齐并核实后再发布。')
    warnings = ['仅交付脚本与拍摄准备；不生成视频、不自动发布、不读取渠道账号数据。',
                '入口仅为商家已配置的外部地址；须人工核验可用性及渠道允许的呈现方式，未验证抖音挂链能力。',
                '按实际商品或课程拍摄；人物肖像、场地、图片和音乐须逐项确认营销使用权。',
                '30秒为剪辑目标；口播按每秒最多4个字/字母/数字预检，拍摄前仍需真人试读。']
    if missing:
        warnings.append('待补充：' + '、'.join(missing) + '。补齐前保留草稿，不作为可发布内容。')
    if offer.get('quantity') == 0:
        warnings.append(f'{quantity_label}为0，暂停{action}引导；更新资料并重新审核后再发布。')

    hook_choices = (['想亲手试试这门手艺吗？', '报体验课前，先看清内容。'] if course
                    else ['选一件手作，先看看细节。', '想把手艺带进日常吗？'])
    project_speech = _excerpt(name + '。' + description, 29) or '项目名称和内容见字幕，请先核对详情。'
    # Prefer the real product/course description, not just a renamed generic ad.
    description_speech = _excerpt(description, 28)
    if description_speech:
        project_speech = ('课程内容：' if course else '这件作品：') + description_speech
        if speech_units(project_speech) > 32:
            project_speech = description_speech
    fact = next((s for item in knowledge if (s := _excerpt(item['content'], 28))), '')
    fact_speech = fact or '具体内容以商家已确认资料为准，待补充。'
    price_speech = (f'价格{_amount(offer["price"])}元，先核对履约说明。'
                    if 'price' in offer else '价格和履约信息待补充，暂勿发布。')
    if speech_units(price_speech) > 20:
        price_speech = '价格见信息卡，请核对履约说明。'
    visuals = {
        'hook': ('竖屏近景：对准本课程实际使用的材料与手部，保留操作原声；不展示未授权学员。' if course
                 else '竖屏微距：将实际商品放在干净背景上，缓慢展示一处纹理；保持实物原色。'),
        'project': ('俯拍课程现场实际操作；按项目内容拍摄，不把未包含的环节拍成课程承诺。' if course
                    else '中景转近景：展示商品正反面和实际使用动作；不虚构制作步骤或性能。'),
        'evidence': '固定近景：拍摄与已确认资料对应的实物细节；无法现场验证时用文字资料卡，不摆拍成历史事实。',
        'terms': '定机拍项目信息卡；价格与履约资料保持清晰，长信息放发布文案，现场核对后再拍。',
        'cta': '定格实际项目画面与行动提示；入口的呈现位置由商家按渠道实际权限确认，不预设购物车或挂链。',
    }
    subtitles = {
        'project': name if len(name) <= 36 else '项目全名与内容见下方发布文案',
        'evidence': fact if fact and len(fact) <= 40 else '来源已列入拍摄资料；未确认内容待补充',
        'terms': terms[2] + '｜' + ('履约说明见发布文案' if delivery else '履约待补充'),
        'cta': f'{action}详情：{url}' if ready else '待补充并审核后发布',
    }
    candidates = []
    def add(role, speech, subtitle, visual=None):
        candidates.append({'candidate_id': f'{role}-{sum(c["role"] == role for c in candidates) + 1}',
                           'role': role, 'visual': visual or visuals[role],
                           'voiceover': speech, 'subtitle': subtitle})
    for hook in hook_choices:
        add('hook', hook, hook)
    add('project', project_speech, subtitles['project'])
    if speech_units(name) <= 25 and name != project_speech:
        add('project', ('这次体验的是' if course else '这件作品是') + name + '。', subtitles['project'])
    add('evidence', fact_speech, subtitles['evidence'])
    for item in knowledge[1:5]:
        excerpt = _excerpt(item['content'], 28)
        if excerpt:
            add('evidence', excerpt, excerpt)
    add('terms', price_speech, subtitles['terms'])
    add('cta', cta, subtitles['cta'])
    times = [(0, 3), (3, 11), (11, 19), (19, 24), (24, 30)]
    storyboard = []
    for role, (start, end) in zip(_ROLES, times):
        candidate = next(c for c in candidates if c['role'] == role)
        storyboard.append({k: v for k, v in candidate.items() if k != 'role'} |
                          {'start_second': start, 'end_second': end})
    title = f'{name}｜' + ('体验与报名指南' if course else '细节与购买指南')
    brief = [f'活动：{_line(campaign.get("name")) or "待补充"}',
             f'目标：{ {"sales": "商品销售", "registration": "课程报名", "awareness": "品牌宣传"}.get(objective, "待补充") }',
             f'受众：{_line(campaign.get("audience")) or "待补充"}',
             f'活动区间：{campaign.get("start_date") or "待补充"} 至 {campaign.get("end_date") or "待补充"}（不是课程场次）',
             f'方案主题：{_line(plan_content.get("theme")) or "待补充"}',
             '渠道内容方向：' + ('；'.join(map(_line, channel_plan.get('content_ideas', []))) if channel_plan else '待补充')]
    evidence = [{k: item[k] for k in ('id', 'title', 'source')} for item in knowledge]
    preparation = {
        'props': [name + ('对应的实际课程材料（按现场清单核对）' if course else '实物及实际交付包装（未确认时待补充）'),
                  '手机、支架、收音设备与补光（拍摄建议，按现有条件准备）', '按以下真实信息制作的项目与入口卡'],
        'locations': ['商家确认有权拍摄的场景；拍摄前清理无关个人信息',
                      '项目履约地点：' + (location or '待补充，不能假定到店地址')],
        'materials': [f'{x["title"]}：{x["content"]}（来源：{x["source"] or "待补充"}；资料ID：{x["id"]}）' for x in knowledge]
                     or ['事实来源待补充；不使用未经确认的身份、历史和工艺表述'],
    }
    preparation['materials'] += ['实拍画面、人物、图片与音乐授权记录（逐项核对；未提供时待补充）',
                                 f'{action}入口核对：{url or "待补充"}；人工测试后决定渠道呈现方式']
    name_tag = '#' + re.sub(r'[^\w]', '', name)
    hashtags = ['#手作体验', '#课程报名'] if course else ['#手作日常', '#好物分享']
    if offer.get('name') and 1 < len(name_tag) <= 21:
        hashtags.insert(0, name_tag)
    return {'title': title, 'channel': channel, 'duration_seconds': DURATION,
            'storyboard': storyboard, 'brief': brief, 'details': '\n'.join(terms),
            'preparation': preparation, 'caption': title + '\n' + '\n'.join(terms) + '\n' + cta,
            'hashtags': hashtags,
            'cta': cta, 'warnings': warnings, 'missing_information': missing, 'evidence': evidence}, candidates


def validate(value, candidates):
    if not isinstance(value, dict) or set(value) != {'duration_seconds', 'storyboard'}:
        raise ValueError('invalid script structure')
    if type(value['duration_seconds']) is not int or value['duration_seconds'] != DURATION:
        raise ValueError('script must last 30 seconds')
    shots = value['storyboard']
    if not isinstance(shots, list) or len(shots) != len(_ROLES):
        raise ValueError('script requires five complete shots')
    lookup = {c['candidate_id']: c for c in candidates}
    fields = {'candidate_id', 'start_second', 'end_second', 'visual', 'voiceover', 'subtitle'}
    cursor, roles, result = 0, [], []
    for shot in shots:
        if not isinstance(shot, dict) or set(shot) != fields:
            raise ValueError('incomplete shot')
        cid = shot['candidate_id']
        if not isinstance(cid, str) or cid not in lookup:
            raise ValueError('unknown source candidate')
        candidate = lookup[cid]
        for field in ('visual', 'voiceover', 'subtitle'):
            if not isinstance(shot[field], str) or not shot[field].strip() or shot[field] != candidate[field]:
                raise ValueError('shot contains ungrounded or changed copy')
        start, end = shot['start_second'], shot['end_second']
        if any(isinstance(x, bool) or not isinstance(x, (int, float))
               or x < 0 or x > DURATION or not math.isfinite(x) for x in (start, end)):
            raise ValueError('invalid shot time')
        if start != cursor or end <= start or end > DURATION:
            raise ValueError('shot timeline has gap, overlap or exceeds duration')
        if speech_units(shot['voiceover']) > (end - start) * MAX_SPEECH_UNITS_PER_SECOND:
            raise ValueError('voiceover exceeds rehearsal budget')
        cursor = end
        roles.append(candidate['role'])
        result.append(copy.deepcopy(shot))
    if cursor != DURATION or roles[0] != 'hook' or roles[-1] != 'cta' or set(roles) != set(_ROLES):
        raise ValueError('incomplete script beats or duration')
    return result


def render(draft, mode):
    content = copy.deepcopy(draft)
    content['hook'] = content['storyboard'][0]['voiceover']
    # Keep legacy content.shots as strings; structured data is additive.
    content['shots'] = [f'镜头{i}（{s["start_second"]:g}—{s["end_second"]:g}秒）\n'
                        f'画面：{s["visual"]}\n口播：“{s["voiceover"]}”\n字幕：{s["subtitle"]}'
                        for i, s in enumerate(content['storyboard'], 1)]
    lines = ['【模板脚本｜未调用模型】' if mode == 'template' else '【AI编排脚本｜事实文案来自已确认输入】',
             '拍摄草稿，须核实资料、试读并审核后使用。',
             f'标题：{content["title"]}', f'渠道：{content["channel"]}｜总时长：30秒',
             '开场吸引点：' + content['hook'], '\n活动与方案', *content['brief'],
             '\n分镜与口播', *content['shots'], '\n拍摄准备']
    for key, label in [('props', '实物与设备'), ('locations', '场景'), ('materials', '素材与来源')]:
        lines += [label + '：', *['- ' + x for x in content['preparation'][key]]]
    lines += ['\n真实项目与入口信息', content['details'], '\n配套发布文案', content['caption'],
              '话题建议：' + ' '.join(content['hashtags']), '\n结尾行动提示：' + content['cta'],
              '\n待补充与拍摄前核对', *['- ' + x for x in content['warnings']]]
    body = '\n'.join(lines)
    if len(body) > 48000:
        raise ValueError('script exceeds editable body size')
    return {'title': content['title'], 'body': body, 'content': content}
