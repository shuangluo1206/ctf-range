"""启动入口：python run.py（第5关起由 socketio.run 驱动，同时服务 HTTP + WebSocket）"""
from app import create_app
from app.state import socketio

app = create_app()

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=8000, debug=True, allow_unsafe_werkzeug=True)
