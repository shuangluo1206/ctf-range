# 靶机镜像：SQL 注入登录页（教学用）
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir flask

COPY app.py .

# 占位默认值；真实 flag 由靶场调度时用 -e FLAG=xxx 注入覆盖
ENV FLAG=flag{placeholder}

# 与靶场的端口映射约定一致（宿主机动态端口 -> 容器 80）
EXPOSE 80

CMD ["python", "app.py"]
