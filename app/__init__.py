from flask import Flask
from config import Config
from app.extensions import db
import pymysql

# 注册 MySQL 驱动
pymysql.install_as_MySQLdb()


def create_app():
    app = Flask(__name__)

    # 1. 加载配置
    app.config.from_object(Config)

    # 2. 初始化数据库插件
    db.init_app(app)

    # 3. 注册 Blueprints (模块化注册)
    # ---------------------------------------------------------

    # (1) 核心模块 (Dashboard, 首页, 通用API)
    # 前提：app/blueprints/core/__init__.py 导出了 main_bp 和 api_bp
    from app.blueprints.core import main_bp, api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    # (2) 认证模块 (登录, 注册)
    # 前提：app/blueprints/auth/__init__.py 导出了 bp
    from app.blueprints.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    # (3) 用户模块 (设置, 个人资料)
    # 前提：app/blueprints/user/__init__.py 导出了 bp
    from app.blueprints.user import bp as user_bp
    app.register_blueprint(user_bp)

    # (4) 健康模块 (记录, AI计划)
    # 前提：app/blueprints/health/__init__.py 导出了 record_bp 和 plan_bp
    from app.blueprints.health import record_bp, plan_bp
    app.register_blueprint(record_bp)
    app.register_blueprint(plan_bp)

    # (5) 社交模块 (社区广场)
    # 前提：app/blueprints/social/__init__.py 导出了 bp
    from app.blueprints.social import bp as social_bp
    app.register_blueprint(social_bp)

    # (6) 管理模块 (后台管理)
    # 前提：app/blueprints/admin/__init__.py 导出了 bp
    from app.blueprints.admin import bp as admin_bp
    app.register_blueprint(admin_bp)

    return app