"""KubernetesService：K8s 调度后端（第7关，JD：预计使用 K8S 重构）

与 DockerService 同接口（run/status/remove），业务层（ChallengeManager 等）零改动——
当初把容器操作收敛到一个类，就是为了今天能整体替换调度层。

架构：每个环境 = 一个 Pod + 一个 Service(NodePort)
- Pod 跑靶机镜像，flag 走环境变量（与 docker run -e 一致）
- Service 用唯一 NodePort 暴露，替代原来的端口映射；端口表由 K8s 自己管
- labels: ctf-range=true（回收只认标签，跨后端同一约定）
- namespace: ctf-range，和系统负载隔离
"""
from kubernetes import client as k8s, config as k8s_config
from kubernetes.client.rest import ApiException

NAMESPACE = "ctf-range"

# NodePort 合法区间是 30000-32767（API Server 写死），与业务端口范围不同：
# 顺序映射 9100-9999 → 30000-30899（业务范围 900 个 < NodePort 可用量 2768 个，无冲突）
NODE_PORT_BASE = 30000
BUSINESS_PORT_BASE = 9100


def to_node_port(port: int) -> int:
    return NODE_PORT_BASE + (port - BUSINESS_PORT_BASE)


class KubernetesService:
    """容器操作的唯一出口（K8s 实现），隔离 kubernetes SDK 细节"""

    def __init__(self, port_range: tuple[int, int]):
        # kind 内建 ServiceAccount 走 kubeconfig；远端集群同样 kubeconfig 注入即可
        k8s_config.load_kube_config()
        self.core = k8s.CoreV1Api()
        self.port_range = port_range
        self._ensure_namespace()

    def _ensure_namespace(self) -> None:
        try:
            self.core.read_namespace(NAMESPACE)
        except ApiException as e:
            if e.status == 404:
                self.core.create_namespace(
                    k8s.V1Namespace(metadata=k8s.V1ObjectMeta(name=NAMESPACE)))
            else:
                raise

    def _used_ports(self) -> set[int]:
        """已被本系统 Service 占用的业务端口（以集群为准，不自己记账）

        集群里记的是 NodePort（30000 段），换算回业务端口（9100 段）
        """
        used = set()
        for svc in self.core.list_namespaced_service(NAMESPACE).items:
            if svc.metadata.labels and svc.metadata.labels.get("ctf-range"):
                for p in (svc.spec.ports or []):
                    if p.node_port:
                        used.add(p.node_port - NODE_PORT_BASE + BUSINESS_PORT_BASE)
        return used

    def _find_free_port(self) -> int:
        used = self._used_ports()
        for port in range(*self.port_range):
            if port not in used:
                return port
        raise RuntimeError("端口耗尽")

    def run(self, image: str, name: str, port: int, env: dict, labels: dict):
        """起一个环境：Pod + Service(NodePort)。返回 Pod 名（作容器 id 用）

        port 是业务端口（9100 段），落集群时映射为 NodePort（30000 段）
        """
        node_port = to_node_port(port)
        try:
            self.core.create_namespaced_pod(NAMESPACE, k8s.V1Pod(
                metadata=k8s.V1ObjectMeta(name=name, labels={**labels, "app": name}),
                spec=k8s.V1PodSpec(
                    containers=[k8s.V1Container(
                        name="challenge", image=image,
                        env=[k8s.V1EnvVar(name=k, value=v) for k, v in env.items()],
                        ports=[k8s.V1ContainerPort(container_port=80)],
                    )],
                ),
            ))
            self.core.create_namespaced_service(NAMESPACE, k8s.V1Service(
                metadata=k8s.V1ObjectMeta(name=name, labels=labels),
                spec=k8s.V1ServiceSpec(
                    type="NodePort",
                    selector={"app": name},
                    ports=[k8s.V1ServicePort(port=80, target_port=80, node_port=node_port)],
                ),
            ))
            return name
        except ApiException as e:
            self.remove(name)  # 半途失败不留脏资源
            raise RuntimeError(f"K8s 启动失败: {e.reason}") from e

    def wait_ready(self, name: str, timeout: int = 60) -> bool:
        """等 Pod Running（kind 上拉镜像要时间，镜像大时调大 timeout）"""
        import time
        deadline = time.time() + timeout
        while time.time() < deadline:
            pod = self.core.read_namespaced_pod(name, NAMESPACE)
            if pod.status.phase == "Running":
                return True
            if pod.status.phase in ("Failed", "Unknown"):
                return False
            time.sleep(1)
        return False

    def status(self, container_id: str) -> str:
        """Pod 真实状态；查不到返回 gone（登记表可能失忆，以集群为准）"""
        try:
            phase = self.core.read_namespaced_pod(container_id, NAMESPACE).status.phase
            return {"Running": "running"}.get(phase, phase.lower())
        except ApiException as e:
            if e.status == 404:
                return "gone"
            raise

    def remove(self, container_id: str) -> bool:
        """删 Pod + Service。幂等：不存在不报错"""
        ok = False
        for deleter, args in ((self.core.delete_namespaced_service, (container_id, NAMESPACE)),
                              (self.core.delete_namespaced_pod, (container_id, NAMESPACE))):
            try:
                deleter(*args)
                ok = True
            except ApiException as e:
                if e.status != 404:
                    raise
        return ok
