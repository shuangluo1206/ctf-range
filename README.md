# ctf-range

动态靶场 / Agent 评测沙箱：用户点一下就拿到独立容器环境，flag 环境变量注入，
用完自动回收。（对标 JD：Python Flask、每用户独立环境、答案注入容器环境变量、
风控防作弊、Webhook/WebSocket 通知、面向对象模块化设计）

## 分层结构（面向对象 + 模块化）

```
app/
├── __init__.py            # 应用工厂 create_app，注册蓝图 + SocketIO
├── config.py              # 集中配置（镜像、端口范围、风控参数、TTL，环境变量可覆盖）
├── state.py               # 共享单例集中地（防循环导入）
├── docker_service.py      # DockerService：容器操作唯一出口（SDK 隔离）
├── challenge_manager.py   # ChallengeManager：登记表 + 端口分配 + 生命周期
├── user_manager.py        # UserManager：注册/登录/积分榜
├── submission_manager.py  # SubmissionManager：flag 判分 + 归属校验 + 防重复计分
├── rate_limiter.py        # RateLimiter：滑动窗口限流
├── reaper.py              # EnvironmentReaper：超时自动回收线程
├── notifier.py            # Notifier：统一事件出口（WebSocket 推送 + Webhook 回调）
└── api/
    ├── users.py           # 注册/登录/积分榜/Webhook 注册
    ├── challenges.py      # 环境生命周期 + 续期
    ├── submissions.py     # flag 提交（风控三道闸收口）
    ├── catalog.py         # 题目目录（描述不含漏洞类型——识别漏洞是考点）
    └── ws.py              # WebSocket 连接鉴权（token → 私有房间）
challenges/                 # 自制靶机镜像（含 Dockerfile）
agent/                      # 机器人选手（第6关：LLM 自动解题）
├── agent_core.py          # RangeClient（选手动作）+ LLMBrain（OpenAI兼容 function calling）
└── play.py                # CLI 入口（--mock 规则选手 / LLM 选手）
static/                     # 简易前端（登录/开环境/提交flag/实时通知）
run.py                      # 启动入口（socketio.run，同端口服务 HTTP + WebSocket）
```

## 功能清单

| 接口 | 作用 |
|---|---|
| `POST /users/register` `POST /users/login` | 注册/登录，返回 Bearer token |
| `GET /scoreboard` | 积分榜 |
| `POST /users/webhook` | 注册 Webhook 回调地址（答对事件 POST 通知） |
| `POST /challenges` | 开环境：动态分配 9100-9999 空闲端口，flag 环境变量注入，默认存活 1 小时 |
| `GET/DELETE /challenges/{id}` | 查看/销毁自己的环境（幂等） |
| `POST /challenges/{id}/extend` | 续期：重置 TTL |
| `POST /submissions` | 提交 flag 判分 |
| `GET /catalog` | 题目目录（公开） |
| `GET /` | 简易前端页面 |

**风控防作弊三道闸**（收口在 submissions 路由）：登录鉴权 → 归属校验（只能提交自己环境的 flag，抄别人的 403）→ 滑动窗口限流（10次/60秒防爆破）；另有每人环境数配额（3个）和同环境防重复计分。

**WebSocket 事件**（连接时带 `?token=` 进私有房间）：`env_created` / `env_expiring`（临期预警）/ `env_reaped` / `env_extended` / `env_deleted` / `submission_result` / `scoreboard`（答对全站广播）。

**Webhook**：用户注册回调地址后，答对等事件异步 POST 到该地址（失败不重试，可靠送达需消息队列，当前规模故意不上）。

**Agent 评测沙箱**（第6关）：`agent/` 里的机器人选手走和人类**完全相同**的 API——开环境、打靶机、提交 flag，风控对机器人一视同仁，解出即自动上榜。

```bash
# 规则脚本选手（不用 LLM，验证闭环）
python3 agent/play.py --user bot-rule --challenge sqli-login --mock

# LLM 选手（OpenAI 兼容接口；题目描述不含漏洞类型，模型要自己侦察）
export LLM_BASE_URL=... LLM_API_KEY=... LLM_MODEL=...
python3 agent/play.py --user bot-ernie --challenge sqli-login
```

对局报告（solved / turns / 用时 / 全程工具调用轨迹）输出为 JSON，可直接喂给评测分析。实测：ernie-4.5-turbo 在不知漏洞类型的情况下，4 轮解出 sqli-login（侦察页面 → 构造注入 → 提取 flag → 提交）。

## 设计约定

- 所有自建容器打 `ctf-range=true` 标签，回收只认标签，绝不碰其他容器
- flag = `flag{uuid随机16位}`，同一镜像每个环境不同 flag（防抄答案）
- Docker 接入走 `DOCKER_HOST`（本机 UNIX Socket / 远端 TCP+TLS 均可）
- 已知简化：登记表在内存（重启失忆）→ 后续换持久化

## 运行

```bash
pip3 install -r requirements.txt
python3 run.py             # :8000，浏览器打开 http://127.0.0.1:8000
```

环境变量：`RANGE_IMAGE`（默认镜像）、`RANGE_TTL`（环境存活秒数，默认 3600）、`RANGE_REAP_INTERVAL`（回收扫描周期）、`RANGE_WARN`（临期预警秒数）。
测试加速示例：`RANGE_TTL=8 RANGE_REAP_INTERVAL=2 python3 run.py`

## 通关计划

- [x] 第 0 关：理解容器（手动 run/删、-e 注入、同镜像多容器不同 flag）
- [x] 第 1 关：Flask 容器 API（动态端口 + flag 注入 + 生命周期）
- [x] 第 2 关：自制靶机镜像（challenges/sqli-login，sqlite 真 SQL 注入，flag 从环境变量读）
- [x] 第 3 关：用户会话 + flag 归属校验 + 提交频率限制（风控防作弊）
- [x] 第 4 关：生命周期管理，超时自动回收（TTL + 回收线程 + 续期接口）
- [x] 第 5 关：WebSocket 实时推送 + Webhook + 简易前端
- [x] 第 6 关：接 AI Agent 自动解题 + 自动打分（Agent 评测沙箱）
- [ ] 第 7 关：调度层换 K8s（Job/Pod + Service）
