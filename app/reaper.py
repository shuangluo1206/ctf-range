"""EnvironmentReaper：后台守护线程，周期扫描超时环境并自动回收（第4关）

设计要点：
- 守护线程（daemon=True）：主进程退出即结束，不留孤儿线程
- 回收动作全部收敛在 ChallengeManager.reap_expired()，线程只负责"何时做"
- 扫描周期与 TTL 都在 config，可用环境变量调小加速测试
"""
import threading


class EnvironmentReaper:
    def __init__(self, challenge_manager, interval_seconds: int):
        self.cm = challenge_manager
        self.interval = interval_seconds
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="env-reaper", daemon=True)

    def _run(self) -> None:
        # wait(interval) 兼做睡眠与退出信号：stop() 一设立即醒，不用等满一个周期
        while not self._stop.wait(self.interval):
            reaped = self.cm.reap_expired()
            if reaped:
                print(f"[reaper] 回收超时环境: {reaped}", flush=True)

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
