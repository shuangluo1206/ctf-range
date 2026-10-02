# ctf-range

动态靶场 / Agent 评测沙箱：用户点一下就拿到独立容器环境，flag 环境变量注入，
用完自动回收。（对标 JD：Python Flask、每用户独立环境、答案注入容器环境变量、
风控防作弊、Webhook/WebSocket 通知、模块化设计）

## 分层结构（面向对象 + 模块化）

```
app/
├── __init__.py            # 应用工厂 create_app，注册蓝图
├── config.py              # 集中配置（镜像、端口范围、容器标签）
├── docker_service.py      # DockerService：容器操作唯一出口（SDK 隔离）
├── challenge_manager.py   # ChallengeManager：登记表 + 端口分配 + 生命周期
└── api/
    └── challenges.py      # 路由层：参数校验 + 转发，不含业务
run.py                     # 启动入口
```

## 第 1 关（当前）：容器 API

| 接口 | 作用 |
|---|---|
| `POST /challenges` | 开环境：动态分配 9100-9999 空闲端口，flag 以环境变量注入容器 |
| `GET /challenges` | 列出所有环境 |
| `GET /challenges/{id}` | 查单个环境（附带容器真实状态） |
| `DELETE /challenges/{id}` | 销毁环境（强删容器 + 归还端口，幂等） |

## 设计约定

- 所有自建容器打 `ctf-range=true` 标签，回收只认标签，绝不碰其他容器
- flag = `flag{uuid随机16位}`，同一镜像每个环境不同 flag（防抄答案）
- Docker 接入走 `DOCKER_HOST`（本机 UNIX Socket / 远端 TCP+TLS 均可）
- 已知简化：登记表在内存（重启失忆）→ 第 3 关换持久化；端口分配有微小竞态窗口 → 第 4 关治理

## 运行

```bash
pip3 install -r requirements.txt
python3 run.py             # :8000
```

## 通关计划

- [x] 第 0 关：理解容器（手动 run/删、-e 注入、同镜像多容器不同 flag）
- [x] 第 1 关：Flask 容器 API（动态端口 + flag 注入 + 生命周期）
- [ ] 第 2 关：自制靶机镜像（带真漏洞的小应用，flag 环境变量注入）
- [ ] 第 3 关：用户会话 + flag 归属校验 + 提交频率限制（风控防作弊）
- [ ] 第 4 关：生命周期管理，超时自动回收
- [ ] 第 5 关：WebSocket 实时推送 + Webhook + 简易前端
- [ ] 第 6 关：接 AI Agent 自动解题 + 自动打分（Agent 评测沙箱）
- [ ] 第 7 关：调度层换 K8s（Job/Pod + Service）
