import bcrypt


def hash_password(password: str) -> str:
    """Băm mật khẩu bằng bcrypt (an toàn, cắt tối đa 72 bytes theo giới hạn chuẩn của bcrypt)."""
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu khớp với chuỗi hash bcrypt."""
    password_bytes = plain_password.encode("utf-8")[:72]
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)
