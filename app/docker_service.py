"""DockerService：所有容器操作只经过这一层（JD：面向对象和模块化设计）

接入方式由 DOCKER_HOST 环境变量决定：
- 本机：默认 UNIX Socket（unix:///var/run/docker.sock）
- 远端：DOCKER_HOST=tcp://host:2376 + TLS 证书（异地部署用）
"""
import docker
from docker.errors import APIError, NotFound


class DockerService:
    """容器操作的唯一出口，隔离 docker SDK 细节"""

    def __init__(self):
        self.client = docker.from_env()

    def run(self, image: str, name: str, port: int, env: dict, labels: dict):
        """起一个容器：端口映射到宿主机、注入环境变量、打标签

        返回短 id；失败抛 RuntimeError
        """
        try:
            container = self.client.containers.run(
                image,
                name=name,
                environment=env,
                ports={"80/tcp": port},
                detach=True,
                labels=labels,
            )
            return container.id[:12]
        except APIError as e:
            raise RuntimeError(f"容器启动失败: {e}") from e

    def status(self, container_id: str) -> str:
        """容器真实状态；查不到返回 gone（登记表可能失忆，以 Docker 为准）"""
        try:
            return self.client.containers.get(container_id).status
        except NotFound:
            return "gone"

    def remove(self, container_id: str) -> bool:
        """强制删除容器（连同可写层）。幂等：不存在不报错"""
        try:
            self.client.containers.get(container_id).remove(force=True)
            return True
        except NotFound:
            return False
