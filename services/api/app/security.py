import hashlib, hmac, secrets, time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from .models import User, Membership, LoginSession

COOKIE = "heritage_session"


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), 600000
    ).hex()
    return f"pbkdf2_sha256$600000${salt}${digest}"


def verify_password(password, encoded):
    try:
        _, iterations, salt, digest = encoded.split("$")
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(iterations)
        ).hex()
        return hmac.compare_digest(actual, digest)
    except (ValueError, TypeError):
        return False


def db_session(request: Request):
    with request.app.state.sessions() as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise


def current_user(request: Request, db=Depends(db_session)):
    token = request.cookies.get(COOKIE, "")
    session = (
        db.get(LoginSession, hashlib.sha256(token.encode()).hexdigest())
        if token
        else None
    )
    if not session or datetime.fromisoformat(session.expires_at) <= datetime.now(
        timezone.utc
    ):
        raise HTTPException(401, "请先登录，会话可能已过期")
    return db.get(User, session.user_id)


def member(workspace_id: str, user=Depends(current_user), db=Depends(db_session)):
    membership = db.get(Membership, (workspace_id, user.id))
    if not membership:
        raise HTTPException(404, "商家空间不存在或无权访问")
    return membership


def editor(membership=Depends(member)):
    if membership.role not in ("owner", "editor"):
        raise HTTPException(403, "需要编辑权限")
    return membership


def reviewer(membership=Depends(member)):
    if membership.role not in ("owner", "reviewer"):
        raise HTTPException(403, "需要审核权限")
    return membership


def owner(membership=Depends(member)):
    if membership.role != "owner":
        raise HTTPException(403, "仅空间所有者可管理成员")
    return membership


def new_session(db, user, response, secure=False):
    token = secrets.token_urlsafe(48)
    db.add(
        LoginSession(
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            user_id=user.id,
            expires_at=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        )
    )
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=604800,
        path="/",
    )


class RateLimiter:
    def __init__(self):
        self.attempts = defaultdict(deque)

    def check(self, key, limit=15, window=300):
        now = time.monotonic()
        q = self.attempts[key]
        while q and q[0] < now - window:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(429, "请求过于频繁，请稍后重试")
        q.append(now)
        if len(self.attempts) > 10000:
            for old in list(self.attempts):
                if not self.attempts[old] or self.attempts[old][-1] < now - window:
                    self.attempts.pop(old, None)
