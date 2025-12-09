from flask import Blueprint, render_template, session, redirect, url_for
from app.models import User, HealthRecord, HealthPlan
from app.decorators import login_required
from datetime import datetime

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@bp.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    
    # 1. 最近记录
    recent_records = HealthRecord.query.filter_by(user_id=user_id)\
                                       .order_by(HealthRecord.date.desc())\
                                       .limit(14).all()
    records = recent_records[::-1] 

    # 2. 图表数据
    dates = [r.date.strftime('%m-%d') for r in records]
    weights = [r.weight for r in records]
    steps = [r.steps for r in records]
    sleep_hours = [r.sleep_hours if r.sleep_hours else None for r in records]
    heart_rates = [r.heart_rate if r.heart_rate else None for r in records]
    bp_highs = [r.blood_pressure_high if r.blood_pressure_high else None for r in records]
    bp_lows = [r.blood_pressure_low if r.blood_pressure_low else None for r in records]

    # 3. 最新计划
    latest_plan = HealthPlan.query.filter_by(user_id=user_id).order_by(HealthPlan.created_at.desc()).first()

    # 4. 活力值计算
    today_score = 0
    if records:
        last_rec = records[-1]
        user = User.query.get(user_id)
        
        step_val = last_rec.steps or 0
        score_move = min((step_val / 10000) * 100, 100)
        
        sleep_val = last_rec.sleep_hours or 0
        score_sleep = 100 if 7 <= sleep_val <= 9 else (80 if 6 <= sleep_val < 7 or 9 < sleep_val <= 10 else 60)
        
        score_body = 80
        if user.height and last_rec.weight:
            height_m = user.height / 100
            bmi = last_rec.weight / (height_m * height_m)
            score_body = 100 if 18.5 <= bmi <= 24 else (80 if 24 < bmi <= 28 or 17 <= bmi < 18.5 else 60)
            
        today_score = int(score_move * 0.5 + score_sleep * 0.3 + score_body * 0.2)

    # 5. 连续打卡
    streak_days = 0
    if records:
        all_dates = [r.date for r in records][::-1]
        if (datetime.now().date() - all_dates[0]).days <= 1:
            streak_days = 1
            prev = all_dates[0]
            for d in all_dates[1:]:
                if (prev - d).days == 1:
                    streak_days += 1
                    prev = d
                else: break

    return render_template('dashboard.html', 
                           nickname=session.get('nickname'),
                           dates=dates, weights=weights, steps=steps,
                           sleep_hours=sleep_hours, heart_rates=heart_rates,
                           bp_highs=bp_highs, bp_lows=bp_lows,
                           latest_plan=latest_plan, today_score=today_score,
                           streak_days=streak_days)