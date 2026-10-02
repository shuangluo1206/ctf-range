"""CLI 入口：放一个机器人选手上场（第6关）

用法（仓库根目录运行）：
  # 规则脚本选手（不需要 LLM，用来验证靶场侧闭环）
  python3 agent/play.py --user bot-rule --challenge sqli-login --mock

  # LLM 选手（OpenAI 兼容接口，环境变量 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL）
  python3 agent/play.py --user bot-glm --challenge sqli-login
"""
import argparse
import json
import os
import re
import sys

import requests

sys.path.insert(0, os.path.dirname(__file__))
from agent_core import RangeClient, run_agent  # noqa: E402

RANGE = os.getenv("RANGE_BASE", "http://127.0.0.1:8000")


def get_token(user: str) -> str:
    """机器人也是普通用户：注册（已存在则跳过）→ 登录拿 token"""
    requests.post(f"{RANGE}/users/register",
                  json={"username": user, "password": "bot-pass-123"}, timeout=10)
    r = requests.post(f"{RANGE}/users/login",
                      json={"username": user, "password": "bot-pass-123"}, timeout=10)
    return r.json()["token"]


def run_mock(client: RangeClient, challenge_name: str) -> dict:
    """规则脚本选手：固定打 SQL 注入盲打payload，验证靶场侧闭环用"""
    import time
    started = time.time()
    trace = []
    for step in ["START", "GET /", "INJECT", "SUBMIT"]:
        if step == "START":
            r = client.start(challenge_name)
            trace.append({"tool": "start_challenge", "args": {"challenge_name": challenge_name},
                          "result": json.dumps(r, ensure_ascii=False)})
            if "error" in r:
                return {"challenge": challenge_name, "solved": False, "turns": len(trace),
                        "duration_seconds": round(time.time() - started, 1), "trace": trace}
        elif step == "GET /":
            r = client.http("GET", "/")
            trace.append({"tool": "http_request", "args": {"GET": "/"}, "result": r["status"]})
        elif step == "INJECT":
            # 经典万能密码注入（靶机漏洞在登录表单的字符串拼接）
            r = client.http("POST", "/login", {"username": "admin' -- ", "password": "x"})
            m = re.search(r"flag\{[^}]+\}", r["body"])
            trace.append({"tool": "http_request", "args": {"POST": "/login 注入"},
                          "result": "命中flag" if m else "未命中"})
            if not m:
                return {"challenge": challenge_name, "solved": False, "turns": len(trace),
                        "duration_seconds": round(time.time() - started, 1), "trace": trace}
            flag = m.group(0)
        else:
            r = client.submit(flag)
            trace.append({"tool": "submit_flag", "args": {"flag": flag},
                          "result": json.dumps(r, ensure_ascii=False)})
    return {"challenge": challenge_name, "solved": r.get("solved", False),
            "turns": len(trace), "duration_seconds": round(time.time() - started, 1),
            "trace": trace}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--user", required=True, help="机器人用户名，如 bot-glm")
    p.add_argument("--challenge", default="sqli-login")
    p.add_argument("--mock", action="store_true", help="规则脚本选手（不用 LLM）")
    p.add_argument("--max-turns", type=int, default=15)
    args = p.parse_args()

    token = get_token(args.user)
    client = RangeClient(RANGE, token)
    catalog = {c["name"]: c for c in client.catalog()}
    if args.challenge not in catalog:
        print(f"题目不存在: {args.challenge}，可选: {list(catalog)}")
        sys.exit(1)

    if args.mock:
        report = run_mock(client, args.challenge)
    else:
        base, key, model = (os.getenv("LLM_BASE_URL"), os.getenv("LLM_API_KEY"),
                            os.getenv("LLM_MODEL"))
        if not (base and key and model):
            print("缺 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL 环境变量（或加 --mock 用规则选手）")
            sys.exit(1)
        from agent_core import LLMBrain
        brain = LLMBrain(base, key, model, max_turns=args.max_turns)
        report = run_agent(client, brain, args.challenge,
                            catalog[args.challenge]["description"])

    print(json.dumps(report, ensure_ascii=False, indent=2))
    verdict = "🎉 解出" if report["solved"] else "❌ 未解出"
    print(f"\n{verdict} | 选手: {args.user} | turns: {report['turns']} "
          f"| 用时: {report['duration_seconds']}s")
    sys.exit(0 if report["solved"] else 2)


if __name__ == "__main__":
    main()
