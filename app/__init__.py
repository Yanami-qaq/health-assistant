from flask import Flask
from config import Config
from app.extensions import db
import pymysql

pymysql.install_as_MySQLdb()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    # 注册 Blueprints
    from app.routes import auth, main, api, record, plan, community, user, admin
    
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(api.bp)
    
    # 新增的模块
    app.register_blueprint(record.bp)
    app.register_blueprint(plan.bp)
    app.register_blueprint(community.bp)
    app.register_blueprint(user.bp)
    app.register_blueprint(admin.bp)

    return app