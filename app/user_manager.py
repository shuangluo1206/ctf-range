"""UserManager：用户注册/登录/token 管理（JD：每个用户独立的应用环境）

教学实现：内存存储 + sha256 密码。
生产演进点（面试可讲）：换数据库持久化、bcrypt/argon2 加盐哈希、token 加过期时间。
"""
import hashlib
import secrets


class UserManager:
    def __init__(self):
        self.users: dict[str, dict] = {}   # username -> info
        self.tokens: dict[str, str] = {}   # token -> username

    # ---- 密码：sha256（教学级；生产要 bcrypt 加盐）----
    @staticmethod
    def _hash(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def register(self, username: str, password: str) -> tuple[dict, int]:
        if not username or not password:
            return {"error": "用户名和密码不能为空"}, 400
        if username in self.users:
            return {"error": "用户名已存在"}, 409
        self.users[username] = {"password": self._hash(password), "score": 0}
        return {"registered": username}, 201

    def login(self, username: str, password: str) -> tuple[dict, int]:
        user = self.users.get(username)
        if not user or user["password"] != self._hash(password):
            return {"error": "用户名或密码错误"}, 401
        token = secrets.token_hex(16)
        self.tokens[token] = username
        return {"token": token}, 200

    def get_by_token(self, token: str) -> dict | None:
        username = self.tokens.get(token)
        return self.users.get(username) if username else None

    def add_score(self, username: str, points: int = 1) -> None:
        if username in self.users:
            self.users[username]["score"] += points

    def scoreboard(self) -> list[dict]:
        return [
            {"username": name, "score": info["score"]}
            for name, info in sorted(
                self.users.items(), key=lambda kv: -kv[1]["score"]
            )
        ]
