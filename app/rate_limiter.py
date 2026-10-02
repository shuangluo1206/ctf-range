"""RateLimiter：固定窗口限流（JD：答案风控防作弊——防爆破提交）

教学实现：内存 + 固定窗口。缺点：窗口边界可突刺 2 倍流量。
生产演进点（面试可讲）：滑动窗口 / 令牌桶 / Redis + Lua 跨实例限流。
"""
import time


class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: int):
        self.max_calls = max_calls
        self.window = window_seconds
        self.hits: dict[str, list[float]] = {}  # key -> 时间戳列表（滑动窗口）

    def allow(self, key: str) -> bool:
        """是否放行。用滑动窗口：只统计 window 内的命中"""
        now = time.monotonic()
        recent = [t for t in self.hits.get(key, []) if now - t < self.window]
        if len(recent) >= self.max_calls:
            self.hits[key] = recent
            return False
        recent.append(now)
        self.hits[key] = recent
        return True

    def remaining(self, key: str) -> int:
        """当前窗口内还剩几次（给响应头/提示用）"""
        now = time.monotonic()
        recent = [t for t in self.hits.get(key, []) if now - t < self.window]
        return max(0, self.max_calls - len(recent))
