# app/__init__.py

from flask import Flask
from config import Config
from app.extensions import db
from flask_migrate import Migrate # <--- 新增

import pymysql
pymysql.install_as_MySQLdb()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    
    # 初始化迁移工具
    Migrate(app, db) # <--- 新增

    from app.routes import auth, main, api
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(api.bp)

    return app