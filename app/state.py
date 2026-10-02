"""集中放共享单例，避免各模块循环导入"""
from .challenge_manager import ChallengeManager
from .rate_limiter import RateLimiter
from .submission_manager import SubmissionManager
from .user_manager import UserManager
from .config import SUBMIT_RATE

user_manager = UserManager()
challenge_manager = ChallengeManager()
submission_manager = SubmissionManager(challenge_manager)
submit_limiter = RateLimiter(max_calls=SUBMIT_RATE[0], window_seconds=SUBMIT_RATE[1])
