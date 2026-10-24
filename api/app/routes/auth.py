from fastapi import APIRouter
from api.app.schemas.common import ErrorResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login")
def login_placeholder():
    """Gói A sẽ hoàn thiện xác thực, mật khẩu bcrypt và phiên cookie."""
    return {"message": "Auth login endpoint shell"}


@router.get("/me")
def me_placeholder():
    """Gói A sẽ hoàn thiện trả thông tin tài khoản hiện tại."""
    return {"message": "Auth me endpoint shell"}


@router.post("/logout")
def logout_placeholder():
    """Gói A sẽ hoàn thiện xóa phiên làm việc."""
    return {"message": "Đăng xuất thành công"}
