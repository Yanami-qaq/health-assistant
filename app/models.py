from app.extensions import db
from datetime import datetime
from flask import url_for
import json

# === 用户表 ===
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password = db.Column(db.String(200), nullable=False)
    nickname = db.Column(db.String(80))
    gender = db.Column(db.String(10))
    birth_year = db.Column(db.Integer)
    height = db.Column(db.Float)
    weight = db.Column(db.Float)
    medical_history = db.Column(db.Text)
    goal_type = db.Column(db.String(20), default='maintain')  # 健康目标：weight_loss(减肥), muscle_gain(增肌), maintain(维持健康)
    is_admin = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    can_post = db.Column(db.Boolean, default=True)

    # 🔥 新增：头像字段 (存储文件名)
    avatar = db.Column(db.String(200), nullable=True)

    records = db.relationship('HealthRecord', backref='user', lazy=True)
    plans = db.relationship('HealthPlan', backref='user', lazy=True)
    posts = db.relationship('Post', backref='user', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)

    # 🔥 新增：头像 URL 辅助属性
    # 前端直接调用 {{ user.avatar_url }} 即可自动判断
    @property
    def avatar_url(self):
        if self.avatar:
            # 如果有上传过头像，返回本地静态文件路径
            return url_for('static', filename='avatars/' + self.avatar)
        else:
            # 否则返回 UI Avatars 生成的默认头像
            name = self.nickname if self.nickname else self.username
            return f"https://ui-avatars.com/api/?name={name}&background=0d6efd&color=fff&size=128"


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


class HealthPlan(db.Model):
    __tablename__ = 'health_plan'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    goal = db.Column(db.String(100))
    content = db.Column(db.Text)
    tasks_json = db.Column(db.Text, default='[]')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tasks = db.relationship('PlanTask', backref='plan', lazy=True, cascade="all, delete-orphan")

    def get_tasks(self):
        """
        兼容性辅助方法：返回字典列表，方便前端渲染
        """
        return [{"id": t.id, "title": t.title, "done": t.is_done} for t in self.tasks]


class PlanTask(db.Model):
    __tablename__ = 'plan_task'
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('health_plan.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    is_done = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_tasks(self):
        try:
            return json.loads(self.tasks_json) if self.tasks_json else []
        except:
            return []


class HealthAssessment(db.Model):
    __tablename__ = 'health_assessment'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    health_score = db.Column(db.Integer, nullable=False)  # 健康分数 0-100
    assessments = db.Column(db.Text)  # JSON格式存储各项指标评估
    suggestions = db.Column(db.Text)  # JSON格式存储改善建议
    summary = db.Column(db.Text)  # 评估总结
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref='assessments')
    
    def get_assessments(self):
        """解析assessments JSON"""
        try:
            return json.loads(self.assessments) if self.assessments else {}
        except:
            return {}
    
    def get_suggestions(self):
        """解析suggestions JSON"""
        try:
            return json.loads(self.suggestions) if self.suggestions else []
        except:
            return []
    
    def to_dict(self):
        """转换为字典格式，方便API返回"""
        return {
            'status': 'success',
            'health_score': self.health_score,
            'assessments': self.get_assessments(),
            'suggestions': self.get_suggestions(),
            'summary': self.summary,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }