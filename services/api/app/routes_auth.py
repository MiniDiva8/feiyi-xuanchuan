import hashlib, os, re
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from .models import User, Workspace, Membership, LoginSession
from .security import (
    db_session,
    current_user,
    new_session,
    hash_password,
    verify_password,
    COOKIE,
)
from .schemas import Register, Login, WorkspaceInput

router = APIRouter(prefix="/api")


def workspace_dict(workspace, role):
    return {
        "id": workspace.id,
        "name": workspace.name,
        "description": workspace.description,
        "created_at": workspace.created_at,
        "role": role,
    }


def identity(db, user):
    memberships = db.scalars(
        select(Membership).where(Membership.user_id == user.id)
    ).all()
    return {
        "user": {"id": user.id, "name": user.name, "email": user.email},
        "workspaces": [
            workspace_dict(db.get(Workspace, m.workspace_id), m.role)
            for m in memberships
        ],
    }


def email(value):
    value = value.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise HTTPException(422, "邮箱格式不正确")
    return value


def add_workspace(db, user, name, description=""):
    w = Workspace(name=name, description=description)
    db.add(w)
    db.flush()
    db.add(Membership(workspace_id=w.id, user_id=user.id, role="owner"))
    db.flush()
    return w


@router.post("/auth/register", status_code=201)
def register(
    data: Register, request: Request, response: Response, db=Depends(db_session)
):
    request.app.state.limiter.check(("register", request.client.host), limit=10)
    address = email(data.email)
    if db.scalar(select(User).where(User.email == address)):
        raise HTTPException(409, "该邮箱已注册")
    user = User(
        name=data.name, email=address, password_hash=hash_password(data.password)
    )
    db.add(user)
    db.flush()
    add_workspace(db, user, data.workspace_name)
    new_session(db, user, response, request.app.state.secure_cookie)
    return identity(db, user)


@router.post("/auth/login")
def login(data: Login, request: Request, response: Response, db=Depends(db_session)):
    address = data.email.lower()
    request.app.state.limiter.check(("login-ip", request.client.host), limit=30)
    request.app.state.limiter.check(("login-email", address), limit=10)
    user = db.scalar(select(User).where(User.email == address))
    # Run the same slow KDF for unknown emails to reduce user enumeration timing.
    encoded = user.password_hash if user else request.app.state.dummy_password
    valid = verify_password(data.password, encoded)
    if not user or not valid:
        raise HTTPException(401, "邮箱或密码不正确")
    new_session(db, user, response, request.app.state.secure_cookie)
    return identity(db, user)


@router.get("/auth/me")
def me(user=Depends(current_user), db=Depends(db_session)):
    return identity(db, user)


@router.post("/auth/logout")
def logout(request: Request, response: Response, db=Depends(db_session)):
    token = request.cookies.get(COOKIE, "")
    session = (
        db.get(LoginSession, hashlib.sha256(token.encode()).hexdigest())
        if token
        else None
    )
    if session:
        db.delete(session)
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/workspaces")
def workspaces(user=Depends(current_user), db=Depends(db_session)):
    return identity(db, user)["workspaces"]


@router.post("/workspaces", status_code=201)
def create_workspace(
    data: WorkspaceInput, user=Depends(current_user), db=Depends(db_session)
):
    return workspace_dict(add_workspace(db, user, data.name, data.description), "owner")
