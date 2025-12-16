from app.extensions import db
from datetime import datetime
import json


# ... (User, PostLike, Comment, Post 表保持不变，省略以节省空间) ...
# 请保留上面的 User, Post 等类，只修改下面的 HealthRecord 和 HealthPlan

# === 用户表 (保持不变) ===
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)  # 暂时允许为空，避免旧数据报错
    password = db.Column(db.String(200), nullable=False)
    nickname = db.Column(db.String(80))
    gender = db.Column(db.String(10))
    birth_year = db.Column(db.Integer)
    height = db.Column(db.Float)
    medical_history = db.Column(db.Text)
    is_admin = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    can_post = db.Column(db.Boolean, default=True)

    records = db.relationship('HealthRecord', backref='user', lazy=True)
    plans = db.relationship('HealthPlan', backref='user', lazy=True)
    posts = db.relationship('Post', backref='user', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)


class PostLike(db.Model):
    __tablename__ = 'post_like'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)


class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)


class Post(db.Model):
    __tablename__ = 'post'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_announcement = db.Column(db.Boolean, default=False)
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan",
                               order_by="Comment.created_at.asc()")
    likes = db.relationship('PostLike', backref='post', lazy='dynamic', cascade="all, delete-orphan")

    def is_liked_by(self, user_id):
        return self.likes.filter_by(user_id=user_id).count() > 0


class HealthRecord(db.Model):
    __tablename__ = 'health_record'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)

    weight = db.Column(db.Float)
    steps = db.Column(db.Integer)
    calories = db.Column(db.Integer)
    body_fat = db.Column(db.Float)
    water_intake = db.Column(db.Integer)
    blood_glucose = db.Column(db.Float)

    note = db.Column(db.String(200))
    sleep_hours = db.Column(db.Float)
    heart_rate = db.Column(db.Integer)
    blood_pressure_high = db.Column(db.Integer)
    blood_pressure_low = db.Column(db.Integer)


# === 🔥 修改：健康计划表 ===
class HealthPlan(db.Model):
    __tablename__ = 'health_plan'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    goal = db.Column(db.String(100))
    content = db.Column(db.Text)  # 这里的 Markdown 文本

    # 新增：存储任务列表 JSON 字符串 (例如: '[{"title":"跑步","done":false}]')
    tasks_json = db.Column(db.Text, default='[]')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 辅助方法：获取任务列表对象
    def get_tasks(self):
        try:
            return json.loads(self.tasks_json) if self.tasks_json else []
        except:
            return []