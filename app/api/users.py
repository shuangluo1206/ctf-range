"""users 路由：注册/登录/积分榜/Webhook 注册（token 鉴权见 auth.require_auth）"""
from flask import Blueprint, jsonify, request

from ..auth import require_auth
from ..state import user_manager

bp = Blueprint("users", __name__)


@bp.post("/users/register")
def register():
    body = request.get_json(silent=True) or {}
    result, status = user_manager.register(
        body.get("username", ""), body.get("password", "")
    )
    return jsonify(result), status


@bp.post("/users/login")
def login():
    body = request.get_json(silent=True) or {}
    result, status = user_manager.login(
        body.get("username", ""), body.get("password", "")
    )
    return jsonify(result), status


@bp.get("/scoreboard")
def scoreboard():
    return jsonify(user_manager.scoreboard())


@bp.post("/users/webhook")
@require_auth
def set_webhook(username: str):
    """注册 Webhook 回调地址（第5关）：环境回收/答对等事件会 POST 到该地址"""
    body = request.get_json(silent=True) or {}
    url = body.get("url", "")
    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "url 必须以 http:// 或 https:// 开头"}), 400
    user_manager.users[username]["webhook"] = url
    return jsonify({"user": username, "webhook": url})
