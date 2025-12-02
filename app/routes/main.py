from flask import Blueprint, render_template, request, redirect, url_for, session
from datetime import datetime
from app.extensions import db
from app.models import User, HealthRecord, HealthPlan, Post
from app.services.ai_service import call_deepseek_advisor

bp = Blueprint('main', __name__)

# --- 辅助装饰器：登录检查 ---
def login_required(func):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@bp.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@bp.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    # 1. 获取所有健康记录 (按时间正序排列)
    records = HealthRecord.query.filter_by(user_id=user_id).order_by(HealthRecord.date.asc()).all()
    # 2. 提取图表数据 (增加专业体征数据)
    dates = [r.date.strftime('%m-%d') for r in records]
    # 基础数据
    weights = [r.weight for r in records]
    steps = [r.steps for r in records]
    # === 新增：专业数据 (处理空值，如果没有数据则给 None，Chart.js 会自动断开连线) ===
    sleep_hours = [r.sleep_hours if r.sleep_hours else None for r in records]
    heart_rates = [r.heart_rate if r.heart_rate else None for r in records]
    bp_highs = [r.blood_pressure_high if r.blood_pressure_high else None for r in records]
    bp_lows = [r.blood_pressure_low if r.blood_pressure_low else None for r in records]
    # 3. 获取最新的 AI 计划
    latest_plan = HealthPlan.query.filter_by(user_id=user_id).order_by(HealthPlan.created_at.desc()).first()
    # 4. 计算今日活力值
    today_score = 0
    if records and records[-1].steps:
        # 简单算法：步数/100，上限100分
        today_score = min(int(records[-1].steps / 100), 100)
    return render_template('dashboard.html', 
                           nickname=session.get('nickname'),
                           dates=dates,
                           weights=weights,
                           steps=steps,
                           sleep_hours=sleep_hours, # 传递新数据
                           heart_rates=heart_rates,
                           bp_highs=bp_highs,
                           bp_lows=bp_lows,
                           latest_plan=latest_plan,
                           today_score=today_score)

@bp.route('/record', methods=['GET', 'POST'])
@login_required
def record():
    if request.method == 'POST':
        date_str = request.form.get('date')
        try:
            record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            return "日期格式错误"

        new_record = HealthRecord(
            user_id=session['user_id'],
            date=record_date,
            weight=float(request.form.get('weight') or 0),
            steps=int(request.form.get('steps') or 0),
            calories=int(request.form.get('calories') or 0),
            note=request.form.get('note'),
            sleep_hours=float(request.form.get('sleep_hours') or 0) if request.form.get('sleep_hours') else None,
            heart_rate=int(request.form.get('heart_rate') or 0) if request.form.get('heart_rate') else None,
            blood_pressure_high=int(request.form.get('bp_high') or 0) if request.form.get('bp_high') else None,
            blood_pressure_low=int(request.form.get('bp_low') or 0) if request.form.get('bp_low') else None
        )
        db.session.add(new_record)
        db.session.commit()
        return redirect(url_for('main.record'))

    user_records = HealthRecord.query.filter_by(user_id=session['user_id']).order_by(HealthRecord.date.desc()).all()
    return render_template('record.html', nickname=session.get('nickname'), records=user_records)

@bp.route('/plan', methods=['GET', 'POST'])
@login_required
def plan():
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        user_goal = request.form.get('goal')
        last_record = HealthRecord.query.filter_by(user_id=user.id).order_by(HealthRecord.date.desc()).first()
        
        # 数据预处理
        current_weight = str(last_record.weight) if last_record else "未知"
        age = datetime.now().year - user.birth_year if user.birth_year else "未知"
        medical = user.medical_history if user.medical_history else "无"
        
        # 构造 Prompt
        system_prompt = "你是一位专业的医学健康顾问。请根据用户数据和目标，生成Markdown格式的每日计划（包含饮食、运动、风险规避）。"
        user_prompt = f"""
        【用户档案】性别:{user.gender}, 年龄:{age}, 身高:{user.height}cm, 体重:{current_weight}kg, 病史:{medical}
        【目标】{user_goal}
        """

        # 调用 Service
        ai_content = call_deepseek_advisor(system_prompt, user_prompt)

        new_plan = HealthPlan(user_id=user.id, goal=user_goal, content=ai_content)
        db.session.add(new_plan)
        db.session.commit()
        return redirect(url_for('main.plan'))

    latest_plan = HealthPlan.query.filter_by(user_id=user.id).order_by(HealthPlan.created_at.desc()).first()
    return render_template('plan.html', nickname=session.get('nickname'), latest_plan=latest_plan)

@bp.route('/community', methods=['GET', 'POST'])
@login_required
def community():
    if request.method == 'POST':
        new_post = Post(user_id=session['user_id'], title=request.form.get('title'), content=request.form.get('content'))
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('main.community'))
        
    all_posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('community.html', nickname=session.get('nickname'), posts=all_posts)

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        user.nickname = request.form.get('nickname')
        user.gender = request.form.get('gender')
        user.height = float(request.form.get('height') or 0) if request.form.get('height') else None
        user.medical_history = request.form.get('medical_history')
        
        db.session.commit()
        session['nickname'] = user.nickname
        return redirect(url_for('main.settings'))
        
    return render_template('settings.html', user=user)

# --- 管理员路由 ---
@bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not session.get('is_admin'):
        return "🚫 权限不足"
    users = User.query.all()
    return render_template('admin_dashboard.html', users=users)

@bp.route('/admin/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if not session.get('is_admin'):
        return "权限不足"
    
    # 级联删除逻辑
    HealthRecord.query.filter_by(user_id=user_id).delete()
    HealthPlan.query.filter_by(user_id=user_id).delete()
    Post.query.filter_by(user_id=user_id).delete()
    User.query.filter_by(id=user_id).delete()
    db.session.commit()
    return redirect(url_for('main.admin_dashboard'))