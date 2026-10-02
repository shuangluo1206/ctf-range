"""ctf-range 配置：集中管理，方便功能拓展（JD：模块化设计）"""
import os

# 容器镜像：第2关会换成自制靶机镜像
DEFAULT_IMAGE = os.getenv("RANGE_IMAGE", "nginx:alpine")

# 动态端口分配范围
PORT_RANGE = (9100, 9999)

# 所有自建容器统一打这个标签：回收只认标签，绝不碰别人的容器
RANGE_LABEL = {"ctf-range": "true"}

# Docker 接入点：默认走本机 UNIX Socket（docker.from_env 读 DOCKER_HOST），
# 换成 TCP+TLS 只需设 DOCKER_HOST=tcp://... 并带证书（JD：UNIX Socket / Docker TCP TLS 接入）
