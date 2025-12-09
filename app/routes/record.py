from flask import Blueprint, render_template, request, redirect, url_for, session, make_response, flash
from app.extensions import db
from app.models import HealthRecord
from app.decorators import login_required
from datetime import datetime
import csv
import io

bp = Blueprint('record', __name__)


# === 1. 首页 (录入模式) ===
@bp.route('/record', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        # 处理新增逻辑
        date_str = request.form.get('date')
        try:
            record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            flash("❌ 日期格式错误")
            return redirect(url_for('record.index'))

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
        flash("✅ 记录已保存！")
        return redirect(url_for('record.index'))

    # 获取列表用于展示
    user_records = HealthRecord.query.filter_by(user_id=session['user_id']).order_by(HealthRecord.date.desc()).all()
    return render_template('record.html', nickname=session.get('nickname'), records=user_records, edit_record=None)


# === 2. 编辑模式视图 (点击编辑按钮后跳转到这里) ===
@bp.route('/record/edit/<int:record_id>')
@login_required
def edit_view(record_id):
    # 查找要编辑的记录
    target_record = HealthRecord.query.get_or_404(record_id)

    # 安全检查
    if target_record.user_id != session['user_id']:
        flash("❌ 您无权编辑此记录")
        return redirect(url_for('record.index'))

    # 获取列表（右侧边栏依然需要显示）
    user_records = HealthRecord.query.filter_by(user_id=session['user_id']).order_by(HealthRecord.date.desc()).all()

    # 渲染模板，但多传一个 edit_record 参数
    return render_template('record.html',
                           nickname=session.get('nickname'),
                           records=user_records,
                           edit_record=target_record)


# === 3. 执行更新 (保存修改) ===
@bp.route('/record/update/<int:record_id>', methods=['POST'])
@login_required
def update(record_id):
    record = HealthRecord.query.get_or_404(record_id)
    if record.user_id != session['user_id']:
        return redirect(url_for('record.index'))

    try:
        # 更新字段
        record.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        record.weight = float(request.form.get('weight') or 0)
        record.steps = int(request.form.get('steps') or 0)
        record.calories = int(request.form.get('calories') or 0)
        record.note = request.form.get('note')

        # 处理可选字段
        s_val = request.form.get('sleep_hours')
        record.sleep_hours = float(s_val) if s_val else None

        hr_val = request.form.get('heart_rate')
        record.heart_rate = int(hr_val) if hr_val else None

        bp_h = request.form.get('bp_high')
        record.blood_pressure_high = int(bp_h) if bp_h else None

        bp_l = request.form.get('bp_low')
        record.blood_pressure_low = int(bp_l) if bp_l else None

        db.session.commit()
        flash("✅ 修改已保存！")
    except Exception as e:
        flash(f"❌ 保存失败: {e}")

    return redirect(url_for('record.index'))


# === 4. 导出功能 ===
@bp.route('/record/export')
@login_required
def export():
    records = HealthRecord.query.filter_by(user_id=session['user_id']).order_by(HealthRecord.date.desc()).all()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['日期', '体重(kg)', '步数', '卡路里', '睡眠(h)', '心率(bpm)', '高压', '低压', '备注'])
    for r in records:
        cw.writerow([r.date, r.weight, r.steps, r.calories, r.sleep_hours, r.heart_rate, r.blood_pressure_high,
                     r.blood_pressure_low, r.note])
    output = make_response(si.getvalue().encode('utf-8-sig'))
    output.headers["Content-Disposition"] = "attachment; filename=health_data.csv"
    output.headers["Content-type"] = "text/csv"
    return output


# === 5. 删除功能 ===
@bp.route('/record/delete/<int:record_id>')
@login_required
def delete(record_id):
    record = HealthRecord.query.get_or_404(record_id)
    if record.user_id != session['user_id']:
        flash("❌ 您无权删除此记录")
        return redirect(url_for('record.index'))
    db.session.delete(record)
    db.session.commit()
    flash("🗑️ 记录已删除")
    return redirect(url_for('record.index'))