"""SubmissionManager：flag 提交判分 + 归属校验 + 记录（JD：答案风控防作弊）

防作弊三道闸（在 api/submissions.py 配合限流器完成）：
1. 归属校验：只能给自己的环境提交答案，抄别人的 flag 无效
2. 重复提交：同一环境答对只计一次分
3. 频率限制：见 rate_limiter（在路由层调用）
"""
from datetime import datetime


class SubmissionManager:
    def __init__(self, challenge_manager):
        self.cm = challenge_manager
        # challenge_id -> username（首个答对者）；提交流水另记
        self.solved_by: dict[str, str] = {}
        self.log: list[dict] = []

    def submit(self, username: str, challenge_id: str, flag: str) -> tuple[dict, int]:
        """提交答案。返回 (响应体, http状态码)"""
        info = self.cm.challenges.get(challenge_id)

        # 归属校验：环境不存在 或 不是你的环境 → 都拒绝
        if not info:
            return {"error": "challenge 不存在"}, 404
        if info["user"] != username:
            return {"error": "该环境不属于你，不能提交"}, 403

        correct = (flag == info["flag"])
        self.log.append({
            "user": username, "challenge": challenge_id,
            "correct": correct, "at": datetime.now().isoformat(),
        })

        if not correct:
            return {"result": "wrong", "msg": "flag 不正确"}, 200

        # 正确：判分（防重复计分——同环境只认第一次）
        if challenge_id in self.solved_by:
            return {"result": "correct", "msg": "正确，但该环境已解答过，不重复计分"}, 200
        self.solved_by[challenge_id] = username
        return {"result": "correct", "msg": "答案正确", "solved": True}, 200

    def history(self, username: str | None = None) -> list[dict]:
        if username:
            return [s for s in self.log if s["user"] == username]
        return self.log
