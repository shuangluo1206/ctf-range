"""应用工厂：注册蓝图，方便后续挂 Webhook / WebSocket 模块（JD：方便功能拓展）"""
from flask import Flask

from .api.challenges import bp as challenges_bp
from .api.submissions import bp as submissions_bp
from .api.users import bp as users_bp
from .state import socketio


def create_app() -> Flask:
    # static 放仓库根的 static/，第5关的简易前端从这出
    app = Flask(__name__, static_folder="../static", static_url_path="/static")
    app.register_blueprint(users_bp)
    app.register_blueprint(challenges_bp)
    app.register_blueprint(submissions_bp)

    # WebSocket 挂到本应用；import 即注册 socketio 事件处理器
    socketio.init_app(app, cors_allowed_origins="*")
    from .api import ws  # noqa: F401

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    return app
