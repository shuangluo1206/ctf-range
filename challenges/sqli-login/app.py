"""靶机：带 SQL 注入漏洞的登录页（教学用，故意写歪）

漏洞点：/login 处的用户输入被直接字符串拼接进 SQL。
正常登录几乎不可能（密码是随机强密码），但注入可绕过。

flag 不写死：从环境变量 FLAG 读，由靶场调度时注入（每个环境唯一）。
"""
import os
import sqlite3

from flask import Flask, request

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "flag{no_flag_injected}")

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>内部管理系统</title></head>
<body style="font-family:sans-serif;max-width:400px;margin:80px auto">
<h2>内部管理系统 · 登录</h2>
<p>提示：管理员的密码是随机的强密码，没人记得住。</p>
<form method="post" action="/login">
  用户名 <input name="username" style="width:100%"><br><br>
  密码 <input name="password" type="password" style="width:100%"><br><br>
  <button style="width:100%">登录</button>
</form></body></html>"""

WELCOME = """<!doctype html>
<html><head><meta charset="utf-8"><title>内部管理系统</title></head>
<body style="font-family:sans-serif;max-width:600px;margin:80px auto">
<h2>登录成功，欢迎回来，管理员</h2>
<p>你的会话令牌：<code>{flag}</code></p>
</body></html>"""

DENIED = """<!doctype html>
<html><body style="font-family:sans-serif;max-width:400px;margin:80px auto">
<h2>用户名或密码错误</h2><a href="/">返回</a></body></html>"""


def check_login(username: str, password: str) -> bool:
    """故意写歪：字符串拼接进 SQL，注入点就在这（正常代码应该用参数绑定 ?）"""
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)")
    # 真实场景里这是强密码；无论如何你都不该能"猜"出来
    db.execute("INSERT INTO users VALUES (1, 'admin', 'Xk9#mQ2$vLp7!zRw')")
    db.commit()
    sql = f"SELECT id FROM users WHERE username='{username}' AND password='{password}'"
    row = db.execute(sql).fetchone()
    db.close()
    return row is not None


@app.get("/")
def index():
    return PAGE


@app.post("/login")
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    if check_login(username, password):
        return WELCOME.format(flag=FLAG)
    return DENIED


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
