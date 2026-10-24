import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Tuple, List, Optional
from fastapi import Request, Depends
from sqlalchemy.orm import Session
from api.app.config import settings
from api.app.database import get_db
from api.app.models.entities import User, Session as DbSession, ClassMember
from api.app.security import verify_password
from api.app.schemas.common import AppError


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_user_session(db: Session, user_id: str) -> Tuple[str, str]:
    session_id = secrets.token_hex(32)
    csrf_token = secrets.token_hex(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.SESSION_EXPIRE_HOURS)

    db_session = DbSession(
        id=session_id,
        user_id=user_id,
        csrf_hash=csrf_token,
        expires_at=expires_at,
        created_at=datetime.now(timezone.utc),
    )
    db.add(db_session)
    db.commit()
    return session_id, csrf_token


def authenticate_user(
    db: Session, username: str, password: str
) -> Tuple[User, List[str], str, str]:
    user = db.query(User).filter(User.username == username, User.is_active.is_(True)).first()
    if not user or not verify_password(password, user.password_hash):
        raise AppError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Tên đăng nhập hoặc mật khẩu không chính xác.",
            fields={"username": "Sai thông tin đăng nhập"}
        )

    class_memberships = db.query(ClassMember).filter(ClassMember.user_id == user.id).all()
    class_ids = [m.class_id for m in class_memberships]

    session_id, csrf_token = create_user_session(db, user.id)
    return user, class_ids, session_id, csrf_token


def get_current_user_and_session(
    request: Request,
    db: Session = Depends(get_db)
) -> Tuple[User, List[str], DbSession]:
    # 1. Look for cookie
    session_id = request.cookies.get("session_id")
    
    # Fallback to Authorization: Bearer <session_id> or X-Session-Id for testing
    if not session_id:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_id = auth_header[7:].strip()
        elif request.headers.get("X-Session-Id"):
            session_id = request.headers.get("X-Session-Id")

    if not session_id:
        raise AppError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Chưa đăng nhập hoặc phiên làm việc đã hết hạn."
        )

    db_session = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not db_session:
        raise AppError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Phiên làm việc không tồn tại hoặc đã đăng xuất."
        )

    now = datetime.now(timezone.utc)
    # Handle naive datetime from SQLite or timezone aware from PostgreSQL
    session_expires = db_session.expires_at
    if session_expires.tzinfo is None:
        session_expires = session_expires.replace(tzinfo=timezone.utc)

    if session_expires < now:
        db.delete(db_session)
        db.commit()
        raise AppError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại."
        )

    user = db.query(User).filter(User.id == db_session.user_id, User.is_active.is_(True)).first()
    if not user:
        raise AppError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Tài khoản người dùng không còn hiệu lực."
        )

    class_memberships = db.query(ClassMember).filter(ClassMember.user_id == user.id).all()
    class_ids = [m.class_id for m in class_memberships]

    return user, class_ids, db_session


def get_current_user(
    auth_data: Tuple[User, List[str], DbSession] = Depends(get_current_user_and_session)
) -> Tuple[User, List[str]]:
    user, class_ids, _ = auth_data
    return user, class_ids


def require_roles(*allowed_roles: str):
    def role_checker(
        auth_data: Tuple[User, List[str], DbSession] = Depends(get_current_user_and_session)
    ) -> Tuple[User, List[str]]:
        user, class_ids, _ = auth_data
        if user.role not in allowed_roles:
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message=f"Hành động này yêu cầu vai trò {' hoặc '.join(allowed_roles)}.",
            )
        return user, class_ids
    return role_checker


def verify_csrf(
    request: Request,
    auth_data: Tuple[User, List[str], DbSession] = Depends(get_current_user_and_session)
):
    method = request.method.upper()
    if method in ["POST", "PUT", "DELETE", "PATCH"]:
        csrf_header = request.headers.get("X-CSRF-Token")
        _, _, db_session = auth_data
        if not csrf_header or csrf_header != db_session.csrf_hash:
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="CSRF token không hợp lệ hoặc bị thiếu.",
            )
