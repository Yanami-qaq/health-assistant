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
    from app.models import User, HealthRecord, HealthPlan
    from datetime import datetime

    user = User.query.get(user_id)
    # 获取最近 30 条记录
    records = HealthRecord.query.filter_by(user_id=user_id).order_by(HealthRecord.date.desc()).limit(30).all()

    if not records:
        # 如果完全没有数据，返回并提示（防止 dashboard 报错，这里简单处理）
        return render_template('main/dashboard.html', user=user, nickname=session.get('nickname'),
                               error="数据不足，无法生成报告")

    # 取最新的一条记录
    last_rec = records[0]

    # === 🔥 修复开始：处理数据中的 None 值 ===

    # 1. 准备日期列表 (倒序，用于图表显示)
    dates = [r.date.strftime('%m-%d') for r in records][::-1]

    # 2. 准备体重和步数数据 (把 None 变成 0，防止报错)
    weights = [(r.weight or 0) for r in records][::-1]
    steps = [(r.steps or 0) for r in records][::-1]

    # 3. 计算平均值 (注意：计算平均体重时，应该排除 0 的数据，否则平均值会偏低)
    valid_weights = [w for w in weights if w > 0]
    if valid_weights:
        avg_weight = round(sum(valid_weights) / len(valid_weights), 1)
    else:
        avg_weight = 0

    valid_steps = [s for s in steps if s > 0]
    if valid_steps:
        avg_steps = int(sum(valid_steps) / len(valid_steps))
    else:
        avg_steps = 0

    # 4. 睡眠数据处理 (已经包含 None 过滤)
    valid_sleeps = [r.sleep_hours for r in records if r.sleep_hours]
    avg_sleep = round(sum(valid_sleeps) / len(valid_sleeps), 1) if valid_sleeps else 0

    # 5. BMI 计算 (防止 last_rec.weight 为 None)
    bmi = 0
    bmi_status = "未知"

    # 如果最新的一条没体重（比如是同步来的），就尝试用最近一次有效的体重，或者用平均体重
    current_weight = last_rec.weight
    if not current_weight and valid_weights:
        current_weight = valid_weights[-1]  # 取最近的一个有效体重

    if user.height and current_weight:
        h_m = user.height / 100
        bmi = round(current_weight / (h_m * h_m), 1)
        if bmi < 18.5:
            bmi_status = "偏瘦"
        elif 18.5 <= bmi <= 24:
            bmi_status = "正常"
        elif 24 < bmi <= 28:
            bmi_status = "超重"
        else:
            bmi_status = "肥胖"

    # === 🔥 修复结束 ===

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