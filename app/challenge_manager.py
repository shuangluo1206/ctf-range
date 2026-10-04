"""ChallengeManager：挑战环境的登记表 + 端口分配 + 生命周期（JD：每个用户独立的应用环境）

第3关改造：
- create 绑定归属用户（风控前提：谁的环境谁提交）
- 对外输出不再包含 flag（防抄答案；flag 只留在服务端内存与容器环境变量里）
- 每用户同时环境数上限（防薅资源）

第4关改造：
- 环境带 TTL（expires_at），到期由 EnvironmentReaper 自动回收
- extend() 续期：选手还在做题就别把他环境收了

第7关改造：
- 调度后端可切换：RANGE_BACKEND=docker（默认）/ k8s（Pod+Service）
  两套后端同接口，本类零改动——容器操作收敛在一层的收益在此兑现
"""
import os
import socket
import time
import uuid
from datetime import datetime

from .config import DEFAULT_IMAGE, ENV_TTL_SECONDS, MAX_ENV_PER_USER, PORT_RANGE, RANGE_LABEL
from .docker_service import DockerService


class ChallengeManager:
    """管理 challenge 的完整生命周期"""

    def __init__(self):
        if os.getenv("RANGE_BACKEND", "docker") == "k8s":
            from .kubernetes_service import KubernetesService
            self.docker = KubernetesService(PORT_RANGE)
            self.backend = "k8s"
        else:
            self.docker = DockerService()
            self.backend = "docker"
        # 内存登记表：challenge_id -> 信息（含 flag，永不直接外泄）
        self.challenges: dict[str, dict] = {}
        self.used_ports: set[int] = set()

    def _find_free_port(self) -> int:
        """在配置范围内找一个未被本系统登记、系统层面也空闲的端口

        k8s 后端：由 KubernetesService._find_free_port 查集群 Service 占用
        docker 后端：bind 试探与 docker -p 之间存在微小竞态窗口
        """
        if self.backend == "k8s":
            return self.docker._find_free_port()
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
        # Pod 名 / 容器名统一用 ctf-{id}（k8s 里也是资源名）
        workload_id = self.docker.run(
            image,
            name=f"ctf-{challenge_id}",
            port=port,
            env={"FLAG": flag},
            labels=RANGE_LABEL,
        )
        if self.backend == "k8s":
            # Pod Ready 才算就绪（KubernetesService 里已等 Running；再等端口可连）
            self.docker.wait_ready(workload_id)
            workload_id = workload_id  # k8s: workload_id 即 pod 名

        info = {
            "id": challenge_id,
            "container_id": workload_id,  # docker: 容器短id / k8s: Pod 名
            "image": image,
            "port": port,
            "flag": flag,   # 仅服务端内部使用，对外输出走 _public()
            "user": username,
            "created_at": datetime.now().isoformat(),
            "expires_at": time.time() + ENV_TTL_SECONDS,  # epoch 秒，到期回收
        }
        self.challenges[challenge_id] = info
        self.used_ports.add(port)
        return self._public(info)

    # 内部字段（flag、记账用的 warned、epoch 时间戳）不对外
    _INTERNAL_KEYS = {"flag", "warned", "expires_at"}

    def _public(self, info: dict) -> dict:
        """对外视图：剔除内部字段，换算剩余存活时间"""
        view = {k: v for k, v in info.items() if k not in self._INTERNAL_KEYS}
        view["expires_in_seconds"] = max(0, int(info["expires_at"] - time.time()))
        return view

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

    def extend(self, username: str, challenge_id: str) -> dict | None:
        """续期：重置 TTL。选手还在做题就别把他环境收了"""
        info = self.challenges.get(challenge_id)
        if not info or info["user"] != username:
            return None
        info["expires_at"] = time.time() + ENV_TTL_SECONDS
        return self._public(info)

    def reap_expired(self) -> list[dict]:
        """回收所有超时环境：删容器、归还端口、释放该用户配额。返回被回收的对外视图（供通知）"""
        now = time.time()
        expired = [cid for cid, i in self.challenges.items() if i["expires_at"] <= now]
        views = []
        for cid in expired:
            info = self.challenges[cid]
            views.append(self._public(info))
            self._destroy(info)
        return views

    def _destroy(self, info: dict) -> None:
        """销毁单个环境：删容器、归还端口、下登记表"""
        self.challenges.pop(info["id"], None)
        self.docker.remove(info["container_id"])
        self.used_ports.discard(info["port"])

    def delete(self, username: str, challenge_id: str) -> dict | None:
        """销毁自己的环境：删容器、归还端口。幂等"""
        info = self.challenges.get(challenge_id)
        if not info or info["user"] != username:
            return None
        self._destroy(info)
        return info
