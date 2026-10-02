"""Notifier：统一事件出口——WebSocket 实时推送 + Webhook 回调（第5关，JD 点名功能）

设计要点：
- WebSocket：推到该用户的私有房间（房间在 api/ws.py 的 connect 事件里进）
- Webhook：用户自己注册回调地址才发；异步发不阻塞主请求，失败只打日志不重试
  （送达可靠需消息队列，当前规模故意不上，README 已注明取舍）
"""
import threading

import requests


class Notifier:
    def __init__(self, socketio, user_manager):
        self.socketio = socketio
        self.um = user_manager

    def emit(self, username: str, event: str, data: dict) -> None:
        """WebSocket 推送到指定用户的私有房间"""
        self.socketio.emit(event, data, to=f"user-{username}")

    def broadcast(self, event: str, data) -> None:
        """全站广播（如积分榜刷新）"""
        self.socketio.emit(event, data)

    def webhook(self, username: str, event: str, data: dict) -> None:
        """给用户注册的 Webhook 地址发 POST（异步，不阻塞主请求）"""
        url = self.um.users.get(username, {}).get("webhook")
        if not url:
            return
        payload = {"event": event, "user": username, "data": data}
        threading.Thread(target=self._post, args=(url, payload), daemon=True).start()

    @staticmethod
    def _post(url: str, payload: dict) -> None:
        try:
            requests.post(url, json=payload, timeout=3)
        except requests.RequestException:
            print(f"[webhook] 送达失败: {url}", flush=True)
