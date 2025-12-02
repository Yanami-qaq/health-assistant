from flask import Flask
from config import Config
from app.extensions import db
import pymysql

# 注册 MySQL 驱动
pymysql.install_as_MySQLdb()

def create_app():
    app = Flask(__name__)
    # 加载配置
    app.config.from_object(Config)

    # 初始化数据库
    db.init_app(app)

    # 注册蓝图 (Blueprints)
    from app.routes import auth, main, api
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(api.bp)

    return app