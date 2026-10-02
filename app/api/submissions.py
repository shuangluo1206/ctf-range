"""submissions 路由：flag 提交入口——风控三道闸在此收口

1. 登录（require_auth）
2. 归属校验（SubmissionManager：只能提交自己环境的答案）
3. 频率限制（RateLimiter：防爆破 flag）
"""
from flask import Blueprint, jsonify, request

from ..auth import require_auth
from ..state import submission_manager, submit_limiter, user_manager

bp = Blueprint("submissions", __name__)


@bp.post("/submissions")
@require_auth
def submit_flag(username: str):
    # 闸3：频率限制（按用户维度）
    if not submit_limiter.allow(username):
        return jsonify({
            "error": "提交太频繁，稍后再试",
            "remaining_window_seconds": submit_limiter.window,
        }), 429

    body = request.get_json(silent=True) or {}
    challenge_id = body.get("challenge_id", "")
    flag = body.get("flag", "")
    result, status = submission_manager.submit(username, challenge_id, flag)

    # 答对才计分（solved=True 首次解答）
    if result.get("solved"):
        user_manager.add_score(username)
        result["score"] = user_manager.users[username]["score"]
    return jsonify(result), status


@bp.get("/submissions")
@require_auth
def my_history(username: str):
    return jsonify(submission_manager.history(username))
