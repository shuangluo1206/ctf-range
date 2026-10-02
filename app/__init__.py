"""应用工厂：注册蓝图，方便后续挂 Webhook / WebSocket 模块（JD：方便功能拓展）"""
from flask import Flask

from .api.challenges import bp as challenges_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(challenges_bp)
    return app
