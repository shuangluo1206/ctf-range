"""集中放共享单例，避免各模块循环导入"""
from .challenge_manager import ChallengeManager
from .config import REAP_INTERVAL_SECONDS, SUBMIT_RATE
from .rate_limiter import RateLimiter
from .reaper import EnvironmentReaper
from .submission_manager import SubmissionManager
from .user_manager import UserManager

user_manager = UserManager()
challenge_manager = ChallengeManager()
submission_manager = SubmissionManager(challenge_manager)
submit_limiter = RateLimiter(max_calls=SUBMIT_RATE[0], window_seconds=SUBMIT_RATE[1])

# 第4关：环境超时自动回收线程（随单例启动）
reaper = EnvironmentReaper(challenge_manager, REAP_INTERVAL_SECONDS)
reaper.start()
