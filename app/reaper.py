"""EnvironmentReaper：后台守护线程，周期扫描超时环境并自动回收（第4关）

第5关改造：回收/临期事件经 Notifier 推 WebSocket 通知（env_reaped / env_expiring）

设计要点：
- 守护线程（daemon=True）：主进程退出即结束，不留孤儿线程
- 回收动作全部收敛在 ChallengeManager.reap_expired()，线程只负责"何时做"
- 扫描周期与 TTL 都在 config，可用环境变量调小加速测试
"""
import threading

from .config import RANGE_WARN_SECONDS


class EnvironmentReaper:
    def __init__(self, challenge_manager, interval_seconds: int, notifier=None):
        self.cm = challenge_manager
        self.notifier = notifier
        self.interval = interval_seconds
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="env-reaper", daemon=True)

    def _run(self) -> None:
        # wait(interval) 兼做睡眠与退出信号：stop() 一设立即醒，不用等满一个周期
        while not self._stop.wait(self.interval):
            self._warn_expiring()
            for view in self.cm.reap_expired():
                if self.notifier:
                    self.notifier.emit(view["user"], "env_reaped", view)

    def _warn_expiring(self) -> None:
        """临期预警：剩余不足 RANGE_WARN_SECONDS 秒时推一次（只推一次）"""
        import time
        now = time.time()
        for info in self.cm.challenges.values():
            left = info["expires_at"] - now
            if 0 < left <= RANGE_WARN_SECONDS and not info.get("warned"):
                info["warned"] = True
                if self.notifier:
                    self.notifier.emit(
                        info["user"], "env_expiring",
                        {"id": info["id"], "port": info["port"],
                         "expires_in_seconds": max(0, int(left))},
                    )

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
