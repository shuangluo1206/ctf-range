"""ChallengeManager：挑战环境的登记表 + 端口分配 + 生命周期（JD：每个用户独立的应用环境）

第3关改造：
- create 绑定归属用户（风控前提：谁的环境谁提交）
- 对外输出不再包含 flag（防抄答案；flag 只留在服务端内存与容器环境变量里）
- 每用户同时环境数上限（防薅资源）
"""
import socket
import uuid
from datetime import datetime

from .config import DEFAULT_IMAGE, MAX_ENV_PER_USER, PORT_RANGE, RANGE_LABEL
from .docker_service import DockerService


class ChallengeManager:
    """管理 challenge 的完整生命周期"""

    def __init__(self):
        self.docker = DockerService()
        # 内存登记表：challenge_id -> 信息（含 flag，永不直接外泄）
        self.challenges: dict[str, dict] = {}
        self.used_ports: set[int] = set()

    def _find_free_port(self) -> int:
        """在配置范围内找一个未被本系统登记、系统层面也空闲的端口

        注：bind 试探与 docker -p 之间存在微小竞态窗口，第4关治理
        """
        for port in range(*PORT_RANGE):
            if port in self.used_ports:
                continue
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("0.0.0.0", port))
                except OSError:
                    continue
            return port
        raise RuntimeError("端口耗尽")

    def _user_env_count(self, username: str) -> int:
        return sum(1 for i in self.challenges.values() if i["user"] == username)

    def create(self, username: str, image: str | None = None) -> dict:
        """开一个挑战环境：绑定用户 + 起容器 + 动态端口 + 注入唯一 flag"""
        if self._user_env_count(username) >= MAX_ENV_PER_USER:
            raise PermissionError(f"每人最多同时持有 {MAX_ENV_PER_USER} 个环境")

        image = image or DEFAULT_IMAGE
        challenge_id = uuid.uuid4().hex[:12]
        flag = f"flag{{{uuid.uuid4().hex[:16]}}}"
        port = self._find_free_port()

        container_id = self.docker.run(
            image,
            name=f"ctf-{challenge_id}",
            port=port,
            env={"FLAG": flag},
            labels=RANGE_LABEL,
        )

        info = {
            "id": challenge_id,
            "container_id": container_id,
            "image": image,
            "port": port,
            "flag": flag,   # 仅服务端内部使用，对外输出走 _public()
            "user": username,
            "created_at": datetime.now().isoformat(),
        }
        self.challenges[challenge_id] = info
        self.used_ports.add(port)
        return self._public(info)

    @staticmethod
    def _public(info: dict) -> dict:
        """对外视图：剔除 flag（第3关起 API 响应不再泄露答案）"""
        return {k: v for k, v in info.items() if k != "flag"}

    def get(self, challenge_id: str) -> dict | None:
        """内部查询（含 flag），供判分用"""
        info = self.challenges.get(challenge_id)
        if not info:
            return None
        info["status"] = self.docker.status(info["container_id"])
        return info

    def get_public(self, challenge_id: str, username: str) -> dict | None:
        """对外查询：必须是自己环境才可见"""
        info = self.challenges.get(challenge_id)
        if not info or info["user"] != username:
            return None
        view = self._public(info)
        view["status"] = self.docker.status(info["container_id"])
        return view

    def list(self, username: str) -> list[dict]:
        return [self._public(i) for i in self.challenges.values() if i["user"] == username]

    def delete(self, username: str, challenge_id: str) -> dict | None:
        """销毁自己的环境：删容器、归还端口。幂等"""
        info = self.challenges.get(challenge_id)
        if not info or info["user"] != username:
            return None
        self.challenges.pop(challenge_id, None)
        self.docker.remove(info["container_id"])
        self.used_ports.discard(info["port"])
        return info
