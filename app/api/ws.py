"""WebSocket 事件处理：连接时带 token，验证通过进私有房间

客户端：io("http://host:8000/?token=xxx")
"""
from flask import request
from flask_socketio import join_room

from ..state import socketio, user_manager


@socketio.on("connect")
def on_connect():
    token = request.args.get("token", "")
    username = user_manager.tokens.get(token)
    if not username:
        return False  # 返回 False 拒绝连接（无效 token 连 WebSocket 也不让进）
    join_room(f"user-{username}")
