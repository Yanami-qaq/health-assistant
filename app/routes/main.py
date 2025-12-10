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

    # === 🔥 修复点 1：必须查询出 user 对象 ===
    user = User.query.get(user_id)
    # ======================================

    # 1. 获取最近 14 天记录
    recent_records = HealthRecord.query.filter_by(user_id=user_id) \
        .order_by(HealthRecord.date.desc()) \
        .limit(14).all()
    records = recent_records[::-1]

    # 2. 提取图表数据
    dates = [r.date.strftime('%m-%d') for r in records]

    weights = [r.weight for r in records]
    steps = [r.steps for r in records]
    sleep_hours = [r.sleep_hours if r.sleep_hours else None for r in records]
    heart_rates = [r.heart_rate if r.heart_rate else None for r in records]

    # 新增字段数据 (防止报错，处理 None)
    body_fats = [r.body_fat if r.body_fat else None for r in records]
    water_intakes = [r.water_intake if r.water_intake else None for r in records]
    blood_glucoses = [r.blood_glucose if r.blood_glucose else None for r in records]

    # 3. 最新计划
    latest_plan = HealthPlan.query.filter_by(user_id=user_id).order_by(HealthPlan.created_at.desc()).first()

    # 4. 活力值计算
    today_score = 0
    if records:
        last_rec = records[-1]

        # 运动分
        step_val = last_rec.steps or 0
        score_move = min((step_val / 10000) * 100, 100)

        # 睡眠分
        sleep_val = last_rec.sleep_hours or 0
        if 7 <= sleep_val <= 9:
            score_sleep = 100
        elif 6 <= sleep_val < 7 or 9 < sleep_val <= 10:
            score_sleep = 80
        else:
            score_sleep = 60

        # BMI 分
        score_body = 80
        if user.height and last_rec.weight:
            height_m = user.height / 100
            bmi = last_rec.weight / (height_m * height_m)
            if 18.5 <= bmi <= 24:
                score_body = 100
            elif 24 < bmi <= 28 or 17 <= bmi < 18.5:
                score_body = 80
            else:
                score_body = 60

        # 饮水加分
        water_val = last_rec.water_intake or 0
        bonus = 5 if water_val >= 2000 else 0

        today_score = int(score_move * 0.5 + score_sleep * 0.3 + score_body * 0.2) + bonus
        today_score = min(today_score, 100)

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
                else:
                    break

    # 6. 热力图数据
    heatmap_data = []
    all_records = HealthRecord.query.filter_by(user_id=user_id).all()
    for r in all_records:
        if r.steps:
            heatmap_data.append([r.date.strftime('%Y-%m-%d'), r.steps])

    return render_template('dashboard.html',
                           # === 🔥 修复点 2：这里必须把 user 传给前端 ===
                           user=user,
                           # =========================================
                           nickname=session.get('nickname'),
                           dates=dates, weights=weights, steps=steps,
                           sleep_hours=sleep_hours, heart_rates=heart_rates,
                           body_fats=body_fats, water_intakes=water_intakes, blood_glucoses=blood_glucoses,
                           latest_plan=latest_plan, today_score=today_score,
                           streak_days=streak_days, heatmap_data=heatmap_data)


# === 生成报告预览页 ===
@bp.route('/report/preview')
@login_required
def report_preview():
    user_id = session['user_id']
    user = User.query.get(user_id)

    records = HealthRecord.query.filter_by(user_id=user_id).order_by(HealthRecord.date.desc()).limit(30).all()

    if not records:
        # 如果没数据，也需要传 user 防止报错
        return render_template('dashboard.html', user=user, nickname=user.nickname, error="数据不足")

    last_rec = records[0]
    dates = [r.date.strftime('%m-%d') for r in records][::-1]
    weights = [r.weight for r in records][::-1]
    steps = [r.steps for r in records][::-1]

    avg_weight = round(sum(weights) / len(weights), 1)
    avg_steps = int(sum(steps) / len(steps))

    # 防止 sleep_hours 为 None 导致计算错误
    valid_sleeps = [r.sleep_hours for r in records if r.sleep_hours]
    avg_sleep = round(sum(valid_sleeps) / len(valid_sleeps), 1) if valid_sleeps else 0

    bmi = 0
    bmi_status = "未知"
    if user.height and last_rec.weight:
        h_m = user.height / 100
        bmi = round(last_rec.weight / (h_m * h_m), 1)
        if bmi < 18.5:
            bmi_status = "偏瘦"
        elif 18.5 <= bmi <= 24:
            bmi_status = "正常"
        elif 24 < bmi <= 28:
            bmi_status = "超重"
        else:
            bmi_status = "肥胖"

    latest_plan = HealthPlan.query.filter_by(user_id=user.id).order_by(HealthPlan.created_at.desc()).first()

    return render_template('report.html',
                           user=user,
                           last_rec=last_rec,
                           avg_weight=avg_weight,
                           avg_steps=avg_steps,
                           avg_sleep=avg_sleep,
                           bmi=bmi,
                           bmi_status=bmi_status,
                           dates=dates,
                           weights=weights,
                           steps=steps,
                           latest_plan=latest_plan,
                           generate_date=datetime.now().strftime('%Y年%m月%d日'))