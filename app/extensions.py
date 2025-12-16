from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail

# 初始化数据库和邮件插件
db = SQLAlchemy()
mail = Mail()