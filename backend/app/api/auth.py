"""认证相关 API"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from redis import Redis

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_token, get_current_user,
)
from app.core.config import settings
from app.models import User
from app.services.sms import SmsProviderError, send_code as send_sms_code, verify_and_consume
from app.schemas import (
    SendCodeRequest, RegisterRequest, LoginRequest, SmsLoginRequest,
    ResetPasswordRequest, TokenResponse, UserResponse, ChangeInitialPasswordRequest,
)

router = APIRouter(prefix="/api/auth", tags=["认证"])


def mask_phone(phone: str) -> str:
    return f"{phone[:3]}****{phone[-4:]}"


@router.post("/send-code")
def send_code(
    req: SendCodeRequest,
    redis: Redis = Depends(get_redis),
    db: Session = Depends(get_db),
):
    """发送短信验证码"""
    if req.scene in {"login", "reset"} and not db.query(User).filter(User.phone == req.phone).first():
        raise HTTPException(status_code=400, detail="该手机号未注册")
    if req.scene == "register" and db.query(User).filter(User.phone == req.phone).first():
        raise HTTPException(status_code=400, detail="该手机号已注册")

    # 频率限制检查
    interval_key = f"sms:interval:{req.phone}"
    hour_key = f"sms:hour:{req.phone}"
    day_key = f"sms:day:{req.phone}"

    if redis.exists(interval_key):
        ttl = redis.ttl(interval_key)
        raise HTTPException(status_code=429, detail=f"请{ttl}秒后再试")

    hour_count = int(redis.get(hour_key) or 0)
    if hour_count >= settings.SMS_HOURLY_LIMIT:
        raise HTTPException(status_code=429, detail="该手机号发送次数已达每小时上限")

    day_count = int(redis.get(day_key) or 0)
    if day_count >= settings.SMS_DAILY_LIMIT:
        raise HTTPException(status_code=429, detail="该手机号发送次数已达每日上限")

    try:
        code = send_sms_code(req.phone, req.scene, redis)
    except SmsProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    redis.setex(interval_key, settings.SMS_SEND_INTERVAL_SECONDS, "1")
    redis.setex(hour_key, 3600, str(hour_count + 1))
    redis.setex(day_key, 86400, str(day_count + 1))

    return {
        "message": "验证码已发送",
        "code": code if settings.SMS_PROVIDER.lower() == "console" and settings.ENVIRONMENT == "development" else None,
    }


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, redis: Redis = Depends(get_redis), db: Session = Depends(get_db)):
    """手机号验证码注册"""
    # 校验验证码
    try:
        verified = verify_and_consume(req.phone, req.code, "register", redis)
    except SmsProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    if not verified:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    # 检查手机号是否已注册
    if db.query(User).filter(User.phone == req.phone).first():
        raise HTTPException(status_code=400, detail="该手机号已注册")

    # 创建用户
    user = User(
        phone=req.phone,
        password_hash=hash_password(req.password),
        name=req.name,
        role=1,
        status=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 生成 token
    token_data = {"sub": str(user.id), "role": user.role}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """账号密码登录（农户/专家，管理员请走 /admin-login）"""
    user = db.query(User).filter(User.phone == req.phone).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="手机号或密码错误")

    if user.status == 0:
        raise HTTPException(status_code=403, detail="账号已被禁用，请联系管理员")

    # 管理员不能走农户/专家登录入口
    if user.role == 3:
        raise HTTPException(status_code=403, detail="该账号为管理员，请使用管理员登录入口")

    # 专家首次登录强制改密码：不签发 token，前端引导走改密流程
    if user.must_change_password:
        return TokenResponse(must_change_password=True)

    token_data = {"sub": str(user.id), "role": user.role}
    refresh_token = create_refresh_token(token_data)

    # Refresh Token 存入 HttpOnly Cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        samesite="lax",
        secure=False,
    )

    return TokenResponse(
        access_token=create_access_token(
            token_data,
            expires_delta=timedelta(days=7) if req.remember else None,
        ),
        refresh_token=refresh_token,
    )


@router.post("/admin-login", response_model=TokenResponse)
def admin_login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """管理员手机号密码登录（不支持注册）"""
    user = db.query(User).filter(User.phone == req.phone).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="手机号或密码错误")
    if user.role != 3:
        raise HTTPException(status_code=403, detail="该账号不是管理员")
    if user.status == 0:
        raise HTTPException(status_code=403, detail="账号已被禁用，请联系管理员")

    token_data = {"sub": str(user.id), "role": user.role}
    refresh_token = create_refresh_token(token_data)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        samesite="lax",
        secure=False,
    )

    return TokenResponse(
        access_token=create_access_token(
            token_data,
            expires_delta=timedelta(days=7) if req.remember else None,
        ),
        refresh_token=refresh_token,
    )


@router.post("/sms-login", response_model=TokenResponse)
def sms_login(req: SmsLoginRequest, response: Response, redis: Redis = Depends(get_redis), db: Session = Depends(get_db)):
    """短信验证码登录"""
    try:
        verified = verify_and_consume(req.phone, req.code, "login", redis)
    except SmsProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    if not verified:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    user = db.query(User).filter(User.phone == req.phone).first()
    if not user:
        raise HTTPException(status_code=400, detail="该手机号未注册")

    if user.status == 0:
        raise HTTPException(status_code=403, detail="账号已被禁用，请联系管理员")

    # 管理员不能走短信登录入口
    if user.role == 3:
        raise HTTPException(status_code=403, detail="该账号为管理员，请使用管理员登录入口")

    # 必须先走账号密码登录触发初始密码修改
    if user.must_change_password:
        raise HTTPException(status_code=403, detail="请先使用账号密码登录并修改初始密码")

    token_data = {"sub": str(user.id), "role": user.role}
    refresh_token = create_refresh_token(token_data)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        samesite="lax",
        secure=False,
    )

    return TokenResponse(
        access_token=create_access_token(
            token_data,
            expires_delta=timedelta(days=7) if req.remember else None,
        ),
        refresh_token=refresh_token,
    )


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, redis: Redis = Depends(get_redis), db: Session = Depends(get_db)):
    """短信验证码重置密码"""
    try:
        verified = verify_and_consume(req.phone, req.code, "reset", redis)
    except SmsProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    if not verified:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    user = db.query(User).filter(User.phone == req.phone).first()
    if not user:
        raise HTTPException(status_code=400, detail="该手机号未注册")

    user.password_hash = hash_password(req.password)
    # 短信重置后视为用户已知密码，清除强制改密标记
    user.must_change_password = False
    db.commit()
    return {"message": "密码已重置"}


@router.post("/change-initial-password")
def change_initial_password(req: ChangeInitialPasswordRequest, db: Session = Depends(get_db)):
    """专家首次登录强制修改初始密码（已知初始密码，无需短信验证码）"""
    user = db.query(User).filter(User.phone == req.phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="该手机号未注册")
    if not user.must_change_password:
        raise HTTPException(status_code=400, detail="当前账号无需修改初始密码")
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status_code=401, detail="原密码错误")
    if req.old_password == req.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")

    user.password_hash = hash_password(req.new_password)
    user.must_change_password = False
    db.commit()
    return {"message": "初始密码修改成功，请使用新密码登录"}


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(response: Response, db: Session = Depends(get_db)):
    """刷新 Access Token（需要 Refresh Token Cookie）"""
    # 实际项目中从 Cookie 读取，这里简化处理
    raise HTTPException(status_code=401, detail="Refresh token not provided")


@router.post("/logout")
def logout(response: Response, current_user: User = Depends(get_current_user)):
    """登出"""
    response.delete_cookie("refresh_token")
    return {"message": "已登出"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user
