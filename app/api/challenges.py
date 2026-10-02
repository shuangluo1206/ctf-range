"""challenges 路由：HTTP API 层，只做参数校验和转发，业务在 ChallengeManager"""
from flask import Blueprint, jsonify, request

from ..challenge_manager import ChallengeManager

bp = Blueprint("challenges", __name__)

# 单例：整个应用共用一个登记表
manager = ChallengeManager()


@bp.post("/challenges")
def create_challenge():
    body = request.get_json(silent=True) or {}
    image = body.get("image")  # 可选，缺省用配置里的默认镜像
    try:
        info = manager.create(image)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(info), 201


@bp.get("/challenges")
def list_challenges():
    return jsonify(manager.list())


@bp.get("/challenges/<challenge_id>")
def get_challenge(challenge_id: str):
    info = manager.get(challenge_id)
    if not info:
        return jsonify({"error": "challenge 不存在"}), 404
    return jsonify(info)


@bp.delete("/challenges/<challenge_id>")
def delete_challenge(challenge_id: str):
    info = manager.delete(challenge_id)
    if not info:
        return jsonify({"error": "challenge 不存在"}), 404
    return jsonify({"deleted": challenge_id})
