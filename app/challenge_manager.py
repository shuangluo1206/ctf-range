"""ChallengeManager：挑战环境的登记表 + 端口分配 + 生命周期（JD：每个用户独立的应用环境）

第1关范围：开环境 / 查状态 / 销毁。
第3关会把登记表换成持久化并绑定用户会话（答案风控防作弊）。
"""
import socket
import uuid
from datetime import datetime

from .config import DEFAULT_IMAGE, PORT_RANGE, RANGE_LABEL
from .docker_service import DockerService


class ChallengeManager:
    """管理 challenge 的完整生命周期"""

    def __init__(self):
        self.docker = DockerService()
        # 内存登记表：challenge_id -> 信息；重启会失忆，以 Docker 实况为准
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

    def create(self, image: str | None = None) -> dict:
        """开一个挑战环境：起容器 + 动态端口 + 注入唯一 flag

        flag 用环境变量注入（JD：用户答案注入容器环境变量）——
        同一镜像给每个环境不同的 flag，防抄答案
        """
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
            "flag": flag,  # 演示阶段直接返回；第3关做归属校验后不再明给
            "created_at": datetime.now().isoformat(),
        }
        self.challenges[challenge_id] = info
        self.used_ports.add(port)
        return info

    def get(self, challenge_id: str) -> dict | None:
        info = self.challenges.get(challenge_id)
        if not info:
            return None
        info["status"] = self.docker.status(info["container_id"])
        return info

    def list(self) -> list[dict]:
        return list(self.challenges.values())

    def delete(self, challenge_id: str) -> dict | None:
        """销毁环境：删容器、归还端口。幂等"""
        info = self.challenges.pop(challenge_id, None)
        if not info:
            return None
        self.docker.remove(info["container_id"])
        self.used_ports.discard(info["port"])
        return info
