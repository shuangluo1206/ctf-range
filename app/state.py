"""集中放共享单例，避免各模块循环导入"""
from flask_socketio import SocketIO

from .challenge_manager import ChallengeManager
from .config import REAP_INTERVAL_SECONDS, SUBMIT_RATE
from .notifier import Notifier
from .rate_limiter import RateLimiter
from .reaper import EnvironmentReaper
from .submission_manager import SubmissionManager
from .user_manager import UserManager

# WebSocket：延迟初始化（init_app 在应用工厂里调）
socketio = SocketIO(async_mode="threading")

user_manager = UserManager()
challenge_manager = ChallengeManager()
submission_manager = SubmissionManager(challenge_manager)
submit_limiter = RateLimiter(max_calls=SUBMIT_RATE[0], window_seconds=SUBMIT_RATE[1])

notifier = Notifier(socketio, user_manager)

# 第4关：环境超时自动回收线程（回收时顺带推 env_reaped 通知，第5关）
reaper = EnvironmentReaper(challenge_manager, REAP_INTERVAL_SECONDS, notifier)
reaper.start()
