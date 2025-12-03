from app.extensions import db
from datetime import datetime

# === 用户表 ===
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    nickname = db.Column(db.String(80))
    gender = db.Column(db.String(10))
    birth_year = db.Column(db.Integer)
    height = db.Column(db.Float)
    medical_history = db.Column(db.Text)
    is_admin = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    can_post = db.Column(db.Boolean, default=True)
    
    # 关联
    records = db.relationship('HealthRecord', backref='user', lazy=True)
    plans = db.relationship('HealthPlan', backref='user', lazy=True)
    posts = db.relationship('Post', backref='user', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True) # 新增：用户发出的评论

# === 帖子点赞表 (关联表) ===
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

# === 社区帖子表 (已更新) ===
class Post(db.Model):
    __tablename__ = 'post' # 显式指定表名，防止报错
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_announcement = db.Column(db.Boolean, default=False)
    
    # 新增关联：级联删除 (帖子删了，评论和点赞也一起删)
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan", order_by="Comment.created_at.asc()")
    likes = db.relationship('PostLike', backref='post', lazy='dynamic', cascade="all, delete-orphan")

    # 辅助方法：判断某人是否给这篇帖子点过赞
    def is_liked_by(self, user_id):
        return self.likes.filter_by(user_id=user_id).count() > 0

# === 其他表保持不变 ===
class HealthRecord(db.Model):
    __tablename__ = 'health_record'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    weight = db.Column(db.Float)
    steps = db.Column(db.Integer)
    calories = db.Column(db.Integer)
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