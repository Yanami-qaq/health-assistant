from flask import Flask
from config import Config
from app.extensions import db, mail
import pymysql
import logging
from logging.handlers import RotatingFileHandler
import os

# 注册 MySQL 驱动
pymysql.install_as_MySQLdb()


def create_app():
    app = Flask(__name__)

    # 1. 加载配置
    app.config.from_object(Config)

    # 2. 初始化插件
    db.init_app(app)
    mail.init_app(app)

    # 3. 注册 Blueprints (保持不变)
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

    # 🔥 新增：配置日志系统
    _configure_logging(app)

    return app


def _configure_logging(app):
    # 如果 logs 文件夹不存在，创建一个
    if not os.path.exists('logs'):
        os.mkdir('logs')

    # 设置日志格式：时间 - 级别 - 文件:行号 - 信息
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )

    # 1. 文件日志处理器 (写入 logs/app.log)
    # maxBytes=10MB, backupCount=10 (保留最近10个文件)
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240000, backupCount=10)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # 2. 将处理器添加到 Flask 的 logger
    app.logger.addHandler(file_handler)

    # 全局设置级别
    app.logger.setLevel(logging.INFO)
    app.logger.info('Health Assistant Startup')