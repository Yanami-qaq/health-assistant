from flask import Blueprint, render_template, request, redirect, url_for, session, make_response, flash
from app.extensions import db
from app.models import HealthRecord, User  # 👈 必须导入 User
from app.decorators import login_required
from datetime import datetime
import csv
import io

bp = Blueprint('record', __name__)


@bp.route('/record', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
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

            # 新增字段
            body_fat=float(request.form.get('body_fat') or 0) if request.form.get('body_fat') else None,
            water_intake=int(request.form.get('water_intake') or 0) if request.form.get('water_intake') else None,
            blood_glucose=float(request.form.get('blood_glucose') or 0) if request.form.get('blood_glucose') else None,

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

    # === 🔥 修复点：必须获取 user 对象传给前端计算 BMI ===
    user = User.query.get(session['user_id'])
    # ==================================================

    user_records = HealthRecord.query.filter_by(user_id=session['user_id']).order_by(HealthRecord.date.desc()).all()

    return render_template('record.html',
                           nickname=session.get('nickname'),
                           records=user_records,
                           user=user,  # 👈 这里必须传 user
                           edit_record=None)


@bp.route('/record/edit/<int:record_id>')
@login_required
def edit_view(record_id):
    target_record = HealthRecord.query.get_or_404(record_id)
    if target_record.user_id != session['user_id']:
        flash("❌ 您无权编辑此记录")
        return redirect(url_for('record.index'))

    # === 🔥 修复点：编辑页面也要传 user ===
    user = User.query.get(session['user_id'])
    # ===================================

    user_records = HealthRecord.query.filter_by(user_id=session['user_id']).order_by(HealthRecord.date.desc()).all()

    return render_template('record.html',
                           nickname=session.get('nickname'),
                           records=user_records,
                           user=user,  # 👈 这里也要传
                           edit_record=target_record)


@bp.route('/record/update/<int:record_id>', methods=['POST'])
@login_required
def update(record_id):
    record = HealthRecord.query.get_or_404(record_id)
    if record.user_id != session['user_id']: return redirect(url_for('record.index'))

    try:
        record.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        record.weight = float(request.form.get('weight') or 0)
        record.steps = int(request.form.get('steps') or 0)
        record.calories = int(request.form.get('calories') or 0)

        # 更新新字段
        bf = request.form.get('body_fat')
        record.body_fat = float(bf) if bf else None

        wi = request.form.get('water_intake')
        record.water_intake = int(wi) if wi else None

        bg = request.form.get('blood_glucose')
        record.blood_glucose = float(bg) if bg else None

        record.note = request.form.get('note')

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


@bp.route('/record/export')
@login_required
def export():
    records = HealthRecord.query.filter_by(user_id=session['user_id']).order_by(HealthRecord.date.desc()).all()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(
        ['日期', '体重(kg)', '体脂率(%)', '步数', '饮水量(ml)', '卡路里', '睡眠(h)', '血糖(mmol/L)', '心率(bpm)',
         '高压', '低压', '备注'])
    for r in records:
        cw.writerow([
            r.date, r.weight, r.body_fat, r.steps, r.water_intake, r.calories,
            r.sleep_hours, r.blood_glucose, r.heart_rate,
            r.blood_pressure_high, r.blood_pressure_low, r.note
        ])
    output = make_response(si.getvalue().encode('utf-8-sig'))
    output.headers["Content-Disposition"] = "attachment; filename=health_data.csv"
    output.headers["Content-type"] = "text/csv"
    return output


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