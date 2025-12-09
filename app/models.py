from app.extensions import db
from datetime import datetime


# === 用户表 (保持不变) ===
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    nickname = db.Column(db.String(80))
    gender = db.Column(db.String(10))
    birth_year = db.Column(db.Integer)
    height = db.Column(db.Float)  # 身高存这里
    medical_history = db.Column(db.Text)
    is_admin = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    can_post = db.Column(db.Boolean, default=True)

    records = db.relationship('HealthRecord', backref='user', lazy=True)
    plans = db.relationship('HealthPlan', backref='user', lazy=True)
    posts = db.relationship('Post', backref='user', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)


# === 帖子点赞表 ===
class PostLike(db.Model):
    __tablename__ = 'post_like'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)


# === 帖子评论表 ===
class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)


# === 社区帖子表 ===
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


# === ✨ 健康记录表 (核心升级) ===
class HealthRecord(db.Model):
    __tablename__ = 'health_record'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)

    # 基础数据
    weight = db.Column(db.Float)  # 体重
    steps = db.Column(db.Integer)  # 步数
    calories = db.Column(db.Integer)  # 卡路里

    # 新增：专业体征数据
    body_fat = db.Column(db.Float)  # 体脂率 (%)
    water_intake = db.Column(db.Integer)  # 饮水量 (ml)
    blood_glucose = db.Column(db.Float)  # 空腹血糖 (mmol/L)

    # 其他
    note = db.Column(db.String(200))
    sleep_hours = db.Column(db.Float)
    heart_rate = db.Column(db.Integer)
    blood_pressure_high = db.Column(db.Integer)
    blood_pressure_low = db.Column(db.Integer)


class HealthPlan(db.Model):
    __tablename__ = 'health_plan'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    goal = db.Column(db.String(100))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)