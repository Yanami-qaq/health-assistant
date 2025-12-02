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
    height = db.Column(db.Float)          # 身高 (cm)
    medical_history = db.Column(db.Text)  # 既往病史
    is_admin = db.Column(db.Boolean, default=False)
    
    # 关联关系
    records = db.relationship('HealthRecord', backref='user', lazy=True)
    plans = db.relationship('HealthPlan', backref='user', lazy=True)
    posts = db.relationship('Post', backref='user', lazy=True)

# === 健康记录表 ===
class HealthRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    weight = db.Column(db.Float)
    steps = db.Column(db.Integer)
    calories = db.Column(db.Integer)
    note = db.Column(db.String(200))
    
    # 专业体征
    sleep_hours = db.Column(db.Float)
    heart_rate = db.Column(db.Integer)
    blood_pressure_high = db.Column(db.Integer)
    blood_pressure_low = db.Column(db.Integer)

# === AI 计划表 ===
class HealthPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    goal = db.Column(db.String(100))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# === 社区帖子表 ===
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)