from flask import Flask
from config import Config
from app.extensions import db, mail
import pymysql

# 注册 MySQL 驱动
pymysql.install_as_MySQLdb()


def create_app():
    app = Flask(__name__)

    # 1. 加载配置
    app.config.from_object(Config)

    # 2. 初始化插件
    db.init_app(app)
    mail.init_app(app)  # 🔥 关键：绑定邮件服务

    # 3. 注册 Blueprints
    from app.blueprints.core import main_bp, api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    from app.blueprints.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.blueprints.user import bp as user_bp
    app.register_blueprint(user_bp)

    from app.blueprints.health import record_bp, plan_bp
    app.register_blueprint(record_bp)
    app.register_blueprint(plan_bp)

    from app.blueprints.social import bp as social_bp
    app.register_blueprint(social_bp)

    from app.blueprints.admin import bp as admin_bp
    app.register_blueprint(admin_bp)

    return app