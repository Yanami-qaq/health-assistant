from flask import Blueprint, render_template, session, redirect, url_for, flash
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


# 生成报告预览页
@bp.route('/report/preview')
@login_required
def report_preview():
    user_id = session['user_id']
    from app.models import User, HealthRecord, HealthPlan
    from datetime import datetime

    user = User.query.get(user_id)
    # 获取最近 30 条记录
    records = HealthRecord.query.filter_by(user_id=user_id).order_by(HealthRecord.date.desc()).limit(30).all()

    # ✅ 修复点1：没有数据时，跳转回仪表盘并提示，防止 streak_days 报错
    if not records:
        flash("暂无健康数据，请先记录或同步数据后再生成报告。", "warning")
        return redirect(url_for('main.dashboard'))

    last_rec = records[0]

    # === 🔥 修复点2：处理数据中的 None 值 (防止 TypeError) ===
    dates = [r.date.strftime('%m-%d') for r in records][::-1]

    # 把 None 转换成 0，防止同步数据后体重为空导致报错
    weights = [(r.weight or 0) for r in records][::-1]
    steps = [(r.steps or 0) for r in records][::-1]

    # 计算平均体重 (排除 0 值，否则平均值会偏低)
    valid_weights = [w for w in weights if w > 0]
    avg_weight = round(sum(valid_weights) / len(valid_weights), 1) if valid_weights else 0

    # 计算平均步数
    valid_steps = [s for s in steps if s > 0]
    avg_steps = int(sum(valid_steps) / len(valid_steps)) if valid_steps else 0

    # 睡眠数据处理 (已经包含 None 过滤)
    valid_sleeps = [r.sleep_hours for r in records if r.sleep_hours]
    avg_sleep = round(sum(valid_sleeps) / len(valid_sleeps), 1) if valid_sleeps else 0

    # BMI 计算 (防止 last_rec.weight 为 None)
    bmi = 0
    bmi_status = "未知"

    # 获取当前有效体重 (如果最新的一条没体重，就找最近一次有的)
    current_weight = last_rec.weight
    if not current_weight and valid_weights:
        current_weight = valid_weights[-1]

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