from flask_sqlalchemy import SQLAlchemy

# 只初始化对象，不绑定 app，绑定操作放在工厂函数里
db = SQLAlchemy()