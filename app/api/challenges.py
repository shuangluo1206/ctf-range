"""challenges 路由：环境生命周期（第3关起必须登录，环境归属当前用户）"""
from flask import Blueprint, jsonify, request

from ..auth import require_auth
from ..state import challenge_manager

bp = Blueprint("challenges", __name__)


@bp.post("/challenges")
@require_auth
def create_challenge(username: str):
    body = request.get_json(silent=True) or {}
    image = body.get("image")  # 可选，缺省用配置里的默认镜像
    try:
        info = challenge_manager.create(username, image)
    except PermissionError as e:
        return jsonify({"error": str(e)}), 429
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(info), 201


@bp.get("/challenges")
@require_auth
def list_challenges(username: str):
    return jsonify(challenge_manager.list(username))


@bp.get("/challenges/<challenge_id>")
@require_auth
def get_challenge(username: str, challenge_id: str):
    info = challenge_manager.get_public(challenge_id, username)
    if not info:
        return jsonify({"error": "challenge 不存在"}), 404
    return jsonify(info)


@bp.delete("/challenges/<challenge_id>")
@require_auth
def delete_challenge(username: str, challenge_id: str):
    info = challenge_manager.delete(username, challenge_id)
    if not info:
        return jsonify({"error": "challenge 不存在或不是你的"}), 404
    return jsonify({"deleted": challenge_id})
