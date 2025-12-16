from flask import Blueprint, render_template, session, redirect, url_for
from app.decorators import login_required
from app.services.stats_service import StatsService

# === 🔥 修改点：在这里直接定义 Blueprint ===
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

    # 使用 Service 层获取数据，保持 Controller 简洁
    data = StatsService.get_dashboard_data(user_id)

    return render_template('main/dashboard.html',
                           user=data['user'],
                           nickname=session.get('nickname'),
                           **data['chart_data'],
                           latest_plan=data['latest_plan'],
                           today_score=data['today_score'],
                           streak_days=data['streak_days'],
                           heatmap_data=data['heatmap_data'])


# 生成报告预览页 (逻辑简单，暂保留在 Controller，也可移入 Service)
@bp.route('/report/preview')
@login_required
def report_preview():
    user_id = session['user_id']
    # 复用 Service 中的一部分逻辑，或者单独写
    # 这里为了演示方便，暂时保留原逻辑，但建议后续也封装
    from app.models import User, HealthRecord, HealthPlan
    from datetime import datetime

    user = User.query.get(user_id)
    records = HealthRecord.query.filter_by(user_id=user_id).order_by(HealthRecord.date.desc()).limit(30).all()

    if not records:
        return render_template('main/dashboard.html', user=user, nickname=user.nickname, error="数据不足")

    last_rec = records[0]
    dates = [r.date.strftime('%m-%d') for r in records][::-1]
    weights = [r.weight for r in records][::-1]
    steps = [r.steps for r in records][::-1]

    avg_weight = round(sum(weights) / len(weights), 1)
    avg_steps = int(sum(steps) / len(steps))

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

    return render_template('main/report.html',
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