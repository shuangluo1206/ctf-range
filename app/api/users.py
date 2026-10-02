"""users 路由：注册/登录/积分榜（token 鉴权见 auth.require_auth）"""
from flask import Blueprint, jsonify, request

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
