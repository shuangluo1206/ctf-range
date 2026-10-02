"""鉴权装饰器：校验 Authorization: Bearer <token>，把 username 注入视图首参"""
from functools import wraps

from flask import jsonify, request


def require_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        from .state import user_manager  # 延迟导入，避免与 state 循环

        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        username = user_manager.tokens.get(token)
        if not username:
            return jsonify({"error": "未登录或 token 无效"}), 401
        return view(username, *args, **kwargs)

    return wrapper
