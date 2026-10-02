"""应用工厂：注册蓝图，方便后续挂 Webhook / WebSocket 模块（JD：方便功能拓展）"""
from flask import Flask

from .api.challenges import bp as challenges_bp
from .api.submissions import bp as submissions_bp
from .api.users import bp as users_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(users_bp)
    app.register_blueprint(challenges_bp)
    app.register_blueprint(submissions_bp)
    return app
