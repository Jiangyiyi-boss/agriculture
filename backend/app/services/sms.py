"""短信验证码服务。

开发环境默认使用控制台验证码；配置 SMS_PROVIDER=aliyun 后调用阿里云号码认证服务。
"""

from __future__ import annotations

import json
import random
from functools import lru_cache
from typing import Literal

from redis import Redis

from app.core.config import settings

SmsScene = Literal["login", "register", "reset"]


class SmsProviderError(RuntimeError):
    """短信供应商返回失败。"""


def _scene_key(phone: str) -> str:
    return f"sms:scene:{phone}"


def _code_key(phone: str) -> str:
    return f"sms:code:{phone}"


def _template_code(scene: SmsScene) -> str:
    return {
        "login": settings.ALIYUN_SMS_TEMPLATE_LOGIN,
        "register": settings.ALIYUN_SMS_TEMPLATE_REGISTER,
        "reset": settings.ALIYUN_SMS_TEMPLATE_RESET,
    }[scene]


@lru_cache(maxsize=1)
def _aliyun_client():
    if not settings.ALIYUN_ACCESS_KEY_ID or not settings.ALIYUN_ACCESS_KEY_SECRET:
        raise SmsProviderError("未配置阿里云 AccessKey，请检查 ALIYUN_ACCESS_KEY_ID 和 ALIYUN_ACCESS_KEY_SECRET")
    if not settings.ALIYUN_SMS_SIGN_NAME:
        raise SmsProviderError("未配置阿里云短信签名，请检查 ALIYUN_SMS_SIGN_NAME")

    try:
        from alibabacloud_credentials.client import Client as CredentialClient
        from alibabacloud_credentials import models as credential_models
        from alibabacloud_dypnsapi20170525.client import Client as DypnsapiClient
        from alibabacloud_tea_openapi import models as open_api_models
    except ImportError as error:
        raise SmsProviderError("缺少阿里云短信 SDK，请先安装后端依赖") from error

    credential = CredentialClient(
        credential_models.Config(
            type="access_key",
            access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
            access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET,
        )
    )
    config = open_api_models.Config(credential=credential)
    config.endpoint = settings.ALIYUN_SMS_ENDPOINT
    return DypnsapiClient(config)


def _aliyun_error(response) -> str:
    body = getattr(response, "body", None)
    return (
        getattr(body, "message", None)
        or getattr(body, "code", None)
        or "阿里云短信服务返回失败"
    )


def _send_with_aliyun(phone: str, scene: SmsScene) -> None:
    from alibabacloud_dypnsapi20170525 import models as dypnsapi_models
    from alibabacloud_tea_util import models as util_models

    request = dypnsapi_models.SendSmsVerifyCodeRequest(
        phone_number=phone,
        sign_name=settings.ALIYUN_SMS_SIGN_NAME,
        template_code=_template_code(scene),
        template_param=json.dumps(
            {"code": "##code##", "min": str(settings.SMS_CODE_TTL_SECONDS // 60)},
            ensure_ascii=False,
        ),
        code_length=6,
        code_type=1,
        duplicate_policy=1,
        interval=settings.SMS_SEND_INTERVAL_SECONDS,
        valid_time=settings.SMS_CODE_TTL_SECONDS,
        return_verify_code=True,
        scheme_name=settings.ALIYUN_SMS_SCHEME_NAME or None,
    )
    try:
        response = _aliyun_client().send_sms_verify_code_with_options(
            request,
            util_models.RuntimeOptions(),
        )
    except Exception as error:
        message = getattr(error, "message", None) or str(error)
        raise SmsProviderError(f"阿里云短信请求失败: {message}") from error
    body = getattr(response, "body", None)
    if not body or body.success is False or body.code != "OK":
        raise SmsProviderError(_aliyun_error(response))


def _verify_with_aliyun(phone: str, code: str) -> bool:
    from alibabacloud_dypnsapi20170525 import models as dypnsapi_models
    from alibabacloud_tea_util import models as util_models

    request = dypnsapi_models.CheckSmsVerifyCodeRequest(
        phone_number=phone,
        verify_code=code,
        scheme_name=settings.ALIYUN_SMS_SCHEME_NAME or None,
    )
    try:
        response = _aliyun_client().check_sms_verify_code_with_options(
            request,
            util_models.RuntimeOptions(),
        )
    except Exception as error:
        message = getattr(error, "message", None) or str(error)
        raise SmsProviderError(f"阿里云验证码校验失败: {message}") from error
    body = getattr(response, "body", None)
    return bool(body and body.success is True and body.code == "OK")


def send_code(phone: str, scene: SmsScene, redis: Redis) -> str | None:
    """发送验证码并记录场景。控制台模式返回验证码，阿里云模式不返回验证码。"""
    provider = settings.SMS_PROVIDER.lower()
    code = None

    if provider == "aliyun":
        _send_with_aliyun(phone, scene)
    elif provider == "console":
        code = str(random.randint(100000, 999999))
        redis.setex(_code_key(phone), settings.SMS_CODE_TTL_SECONDS, code)
        print(
            f"\n{'=' * 50}\n"
            f"SMS verification code [development]\n"
            f"phone: {phone}\n"
            f"scene: {scene}\n"
            f"code: {code}\n"
            f"{'=' * 50}\n"
        )
    else:
        raise SmsProviderError(f"不支持的短信供应商: {settings.SMS_PROVIDER}")

    redis.setex(_scene_key(phone), settings.SMS_CODE_TTL_SECONDS, scene)
    return code


def verify_and_consume(phone: str, code: str, scene: SmsScene, redis: Redis) -> bool:
    """校验验证码并在成功后消费，避免同一验证码重复使用。"""
    if redis.get(_scene_key(phone)) != scene:
        return False

    if settings.SMS_PROVIDER.lower() == "aliyun":
        verified = _verify_with_aliyun(phone, code)
    else:
        verified = redis.get(_code_key(phone)) == code

    if verified:
        redis.delete(_scene_key(phone), _code_key(phone))
    return verified
