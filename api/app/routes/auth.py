from fastapi import APIRouter, Depends, Response, Request
from sqlalchemy.orm import Session
from api.app.database import get_db
from api.app.config import settings
from api.app.services.auth_service import (
    authenticate_user,
    get_current_user_and_session,
)
from api.app.models.entities import Session as DbSession, User
from api.app.schemas import (
    LoginRequest,
    AuthResponse,
    UserSchema,
    LogoutResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=AuthResponse)
def login(login_data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user, class_ids, session_id, csrf_token = authenticate_user(
        db, login_data.username, login_data.password
    )
    # Set HttpOnly session cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=settings.SESSION_EXPIRE_HOURS * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.IS_PRODUCTION,
        path="/",
    )
    return AuthResponse(
        user=UserSchema(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            class_ids=class_ids,
        ),
        csrf_token=csrf_token,
    )


@router.get("/me", response_model=AuthResponse)
def get_me(
    auth_data: tuple[User, list[str], DbSession] = Depends(get_current_user_and_session)
):
    user, class_ids, db_session = auth_data
    return AuthResponse(
        user=UserSchema(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            class_ids=class_ids,
        ),
        csrf_token=db_session.csrf_hash,
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    session_id = request.cookies.get("session_id")
    if not session_id:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_id = auth_header[7:].strip()
        elif request.headers.get("X-Session-Id"):
            session_id = request.headers.get("X-Session-Id")

    if session_id:
        db.query(DbSession).filter(DbSession.id == session_id).delete()
        db.commit()

    response.delete_cookie(key="session_id", path="/")
    return LogoutResponse(message="Đăng xuất thành công")
