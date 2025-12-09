# init_db.py
from app import create_app
from app.extensions import db

# 必须导入 models，这样 SQLAlchemy 才知道有哪些表需要创建
from app.models import User, HealthRecord, HealthPlan, Post, PostLike, Comment

app = create_app()

print("正在连接云数据库并创建表...")
with app.app_context():
    # 这行代码会根据您的 models.py 自动在数据库里建表
    db.create_all()
    print("✅ 成功！所有数据库表已在云端创建完毕。")