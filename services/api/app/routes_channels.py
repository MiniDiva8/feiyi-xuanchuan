"""Merchant channel profiles and attributed snapshots, not a scraping service."""
from datetime import date, datetime
from zoneinfo import ZoneInfo
from typing import Literal
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, field_validator
from .schemas import Input
from .security import member, editor, current_user, db_session
from .workflow import records, get_record, create, audit, public, digest

router = APIRouter(prefix='/api/workspaces/{workspace_id}', dependencies=[Depends(member)])
PLATFORMS = {
    'douyin': ('douyin.com', 'iesdouyin.com'),
    'bilibili': ('bilibili.com', 'b23.tv'),
    'xiaohongshu': ('xiaohongshu.com', 'xhslink.com'),
    'kuaishou': ('kuaishou.com', 'gifshow.com'),
    'channels': ('weixin.qq.com', 'weixin.com'),
}


class ChannelInput(Input):
    platform: Literal['douyin', 'bilibili', 'xiaohongshu', 'kuaishou', 'channels']
    name: str = Field(min_length=1, max_length=120)
    account_id: str = Field(min_length=1, max_length=200)
    profile_url: str = Field(default='', max_length=2000)


class SnapshotInput(Input):
    date: date
    source: str = Field(min_length=1, max_length=300)
    followers: int | None = Field(default=None, ge=0, le=10**12)
    views: int | None = Field(default=None, ge=0, le=10**15)
    likes: int | None = Field(default=None, ge=0, le=10**15)
    comments: int | None = Field(default=None, ge=0, le=10**15)
    shares: int | None = Field(default=None, ge=0, le=10**15)
    posts: int | None = Field(default=None, ge=0, le=10**9)
    latest_post_date: date | None = None

    @field_validator('followers', 'views', 'likes', 'comments', 'shares', 'posts', mode='before')
    @classmethod
    def integer_only(cls, value):
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            raise ValueError('请输入非负整数')
        return value


@router.get('/channels')
def channel_list(workspace_id: str, db=Depends(db_session)):
    snapshots = records(db, workspace_id, 'channel_snapshot')
    result = []
    for account in records(db, workspace_id, 'channel'):
        history = sorted((public(x) for x in snapshots if x.parent_id == account.id), key=lambda x: x['date'])
        result.append({**public(account), 'sync_status': 'not_connected', 'snapshots': history,
                       'latest': history[-1] if history else None,
                       'follower_change': history[-1]['followers'] - history[-2]['followers'] if len(history) >= 2 and history[-1]['followers'] is not None and history[-2]['followers'] is not None else None})
    return result


@router.post('/channels', status_code=201, dependencies=[Depends(editor)])
def channel_create(workspace_id: str, data: ChannelInput, user=Depends(current_user), db=Depends(db_session)):
    key = validate_channel(db, workspace_id, data)
    item = create(db, workspace_id, 'channel', data.model_dump(), dedupe=key)
    audit(db, workspace_id, user, 'create', item)
    return public(item)


def validate_channel(db, workspace_id, data, exclude=None):
    if data.profile_url:
        try:
            url = urlsplit(data.profile_url)
        except ValueError:
            raise HTTPException(422, '主页链接格式不正确')
        host = (url.hostname or '').lower()
        if url.scheme != 'https' or url.username or url.password or ':' in url.netloc or not any(host == d or host.endswith('.' + d) for d in PLATFORMS[data.platform]):
            raise HTTPException(422, '请填写对应平台的HTTPS主页链接；没有公开链接可留空')
    key = digest([data.platform, data.account_id.casefold()])
    if any(x.dedupe_key == key and x.id != exclude for x in records(db, workspace_id, 'channel')):
        raise HTTPException(409, '该平台账号已添加')
    return key


@router.patch('/channels/{id}', dependencies=[Depends(editor)])
def channel_edit(workspace_id: str, id: str, data: ChannelInput, user=Depends(current_user), db=Depends(db_session)):
    item = get_record(db, workspace_id, 'channel', id)
    if (data.platform, data.account_id.casefold()) != (item.data['platform'], item.data['account_id'].casefold()):
        raise HTTPException(422, '平台和账号标识不能更换，请为其他账号单独建档，避免混用历史数据')
    key = validate_channel(db, workspace_id, data, exclude=id)
    before = dict(item.data)
    item.data = data.model_dump()
    item.dedupe_key = key
    audit(db, workspace_id, user, 'edit_channel', item, {'before': before, 'after': item.data})
    return public(item)


@router.post('/channels/{id}/snapshots', status_code=201, dependencies=[Depends(editor)])
def snapshot_create(workspace_id: str, id: str, data: SnapshotInput, user=Depends(current_user), db=Depends(db_session)):
    get_record(db, workspace_id, 'channel', id)
    if data.date > datetime.now(ZoneInfo('Asia/Shanghai')).date() or (data.latest_post_date and data.latest_post_date > data.date):
        raise HTTPException(422, '记录日期不能在未来，最近更新不能晚于记录日期')
    if not any(getattr(data, key) is not None for key in ('followers', 'views', 'likes', 'comments', 'shares', 'posts')):
        raise HTTPException(422, '至少填写一项实际取得的指标')
    key = digest([id, data.date.isoformat()])
    if any(x.dedupe_key == key for x in records(db, workspace_id, 'channel_snapshot')):
        raise HTTPException(409, '该账号当天已有记录，请勿重复录入')
    item = create(db, workspace_id, 'channel_snapshot', {**data.model_dump(mode='json'), 'source_type': 'manual'}, parent=id, dedupe=key)
    audit(db, workspace_id, user, 'record_snapshot', item)
    return public(item)
