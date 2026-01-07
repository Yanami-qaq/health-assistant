from flask import Blueprint, render_template, request, redirect, url_for, session, make_response, flash
from app.extensions import db
from app.models import HealthRecord, User
from app.decorators import login_required
from datetime import datetime
import csv
import io

# === 🔥 修改点：在这里定义 Blueprint ===
# 注意：我们这里叫它 bp，方便统一习惯
bp = Blueprint('record', __name__)


# === 🔥 新增：数据验证函数 ===
def validate_health_data(form_data):
    """
    验证健康数据的合理性
    返回: (is_valid, error_message)
    """
    errors = []
    
    # 1. 验证体重 (20-300 kg，必填)
    weight = form_data.get('weight')
    if not weight or weight.strip() == '':
        errors.append("体重为必填项")
    else:
        try:
            weight_val = float(weight)
            if weight_val <= 0:
                errors.append("体重必须大于0")
            elif weight_val < 20 or weight_val > 300:
                errors.append("体重必须在 20-300 kg 之间")
        except ValueError:
            errors.append("体重格式不正确")
    
    # 2. 验证体脂率 (3-60%)
    body_fat = form_data.get('body_fat')
    if body_fat:
        try:
            bf_val = float(body_fat)
            if bf_val < 3 or bf_val > 60:
                errors.append("体脂率必须在 3-60% 之间")
            elif bf_val < 0:
                errors.append("体脂率不能为负数")
        except ValueError:
            errors.append("体脂率格式不正确")
    
    # 3. 验证步数 (0-100000)
    steps = form_data.get('steps')
    if steps:
        try:
            steps_val = int(steps)
            if steps_val < 0:
                errors.append("步数不能为负数")
            elif steps_val > 100000:
                errors.append("步数不能超过 100000")
        except ValueError:
            errors.append("步数必须是整数")
    
    # 4. 验证卡路里 (0-10000)
    calories = form_data.get('calories')
    if calories:
        try:
            cal_val = int(calories)
            if cal_val < 0:
                errors.append("卡路里不能为负数")
            elif cal_val > 10000:
                errors.append("卡路里不能超过 10000")
        except ValueError:
            errors.append("卡路里必须是整数")
    
    # 5. 验证饮水量 (0-10000 ml)
    water = form_data.get('water_intake')
    if water:
        try:
            water_val = int(water)
            if water_val < 0:
                errors.append("饮水量不能为负数")
            elif water_val > 10000:
                errors.append("饮水量不能超过 10000 ml")
        except ValueError:
            errors.append("饮水量必须是整数")
    
    # 6. 验证血糖 (2-30 mmol/L)
    glucose = form_data.get('blood_glucose')
    if glucose:
        try:
            glucose_val = float(glucose)
            if glucose_val < 2 or glucose_val > 30:
                errors.append("血糖必须在 2-30 mmol/L 之间")
            elif glucose_val < 0:
                errors.append("血糖不能为负数")
        except ValueError:
            errors.append("血糖格式不正确")
    
    # 7. 验证睡眠时长 (0-24 小时)
    sleep = form_data.get('sleep_hours')
    if sleep:
        try:
            sleep_val = float(sleep)
            if sleep_val < 0 or sleep_val > 24:
                errors.append("睡眠时长必须在 0-24 小时之间")
        except ValueError:
            errors.append("睡眠时长格式不正确")
    
    # 8. 验证心率 (30-250 bpm)
    heart_rate = form_data.get('heart_rate')
    if heart_rate:
        try:
            hr_val = int(heart_rate)
            if hr_val < 30 or hr_val > 250:
                errors.append("心率必须在 30-250 bpm 之间")
            elif hr_val < 0:
                errors.append("心率不能为负数")
        except ValueError:
            errors.append("心率必须是整数")
    
    # 9. 验证血压高压 (60-250 mmHg)
    bp_high = form_data.get('bp_high')
    if bp_high:
        try:
            bp_high_val = int(bp_high)
            if bp_high_val < 60 or bp_high_val > 250:
                errors.append("高压必须在 60-250 mmHg 之间")
            elif bp_high_val < 0:
                errors.append("高压不能为负数")
        except ValueError:
            errors.append("高压必须是整数")
    
    # 10. 验证血压低压 (40-150 mmHg)
    bp_low = form_data.get('bp_low')
    if bp_low:
        try:
            bp_low_val = int(bp_low)
            if bp_low_val < 40 or bp_low_val > 150:
                errors.append("低压必须在 40-150 mmHg 之间")
            elif bp_low_val < 0:
                errors.append("低压不能为负数")
        except ValueError:
            errors.append("低压必须是整数")
    
    # 11. 验证血压逻辑关系（高压应该大于低压）
    if bp_high and bp_low:
        try:
            if int(bp_high) <= int(bp_low):
                errors.append("高压必须大于低压")
        except ValueError:
            pass  # 已经在上面报错了
    
    if errors:
        return False, "输入无效，请重新输入：" + "；".join(errors)
    
    return True, ""

@bp.route('/record', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        # 🔥 1. 先验证数据
        is_valid, error_msg = validate_health_data(request.form)
        if not is_valid:
            flash(error_msg)
            return redirect(url_for('record.index'))
        
        # 2. 验证日期格式
        date_str = request.form.get('date')
        try:
            record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            flash("输入无效，请重新输入：日期格式错误")
            return redirect(url_for('record.index'))

        # 3. 数据验证通过，创建记录
        try:
            new_record = HealthRecord(
                user_id=session['user_id'],
                date=record_date,
                weight=float(request.form.get('weight')),
                steps=int(request.form.get('steps') or 0),
                calories=int(request.form.get('calories') or 0),
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
            flash("记录已保存")
        except Exception as e:
            flash("输入无效，请重新输入：保存失败")
            return redirect(url_for('record.index'))
        
        return redirect(url_for('record.index'))

    user = User.query.get(session['user_id'])
    user_records = HealthRecord.query.filter_by(user_id=session['user_id']).order_by(HealthRecord.date.desc()).all()

    return render_template('health/record.html', nickname=session.get('nickname'), records=user_records, user=user, edit_record=None)

@bp.route('/record/edit/<int:record_id>')
@login_required
def edit_view(record_id):
    target_record = HealthRecord.query.get_or_404(record_id)
    if target_record.user_id != session['user_id']:
        flash("您无权编辑此记录")
        return redirect(url_for('record.index'))

    user = User.query.get(session['user_id'])
    user_records = HealthRecord.query.filter_by(user_id=session['user_id']).order_by(HealthRecord.date.desc()).all()

    return render_template('health/record.html', nickname=session.get('nickname'), records=user_records, user=user, edit_record=target_record)

@bp.route('/record/update/<int:record_id>', methods=['POST'])
@login_required
def update(record_id):
    record = HealthRecord.query.get_or_404(record_id)
    if record.user_id != session['user_id']: 
        return redirect(url_for('record.index'))

    # 1. 先验证数据
    is_valid, error_msg = validate_health_data(request.form)
    if not is_valid:
        flash(error_msg)
        return redirect(url_for('record.edit_view', record_id=record_id))

    try:
        # 2. 验证日期格式
        record.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        
        # 3. 更新数据
        record.weight = float(request.form.get('weight'))
        record.steps = int(request.form.get('steps') or 0)
        record.calories = int(request.form.get('calories') or 0)
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
        flash("修改已保存")
    except ValueError:
        flash("输入无效，请重新输入：日期格式错误")
        return redirect(url_for('record.edit_view', record_id=record_id))
    except Exception as e:
        flash("输入无效，请重新输入：保存失败")
        return redirect(url_for('record.edit_view', record_id=record_id))

    return redirect(url_for('record.index'))

@bp.route('/record/export')
@login_required
def export():
    records = HealthRecord.query.filter_by(user_id=session['user_id']).order_by(HealthRecord.date.desc()).all()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['日期', '体重(kg)', '体脂率(%)', '步数', '饮水量(ml)', '卡路里', '睡眠(h)', '血糖(mmol/L)', '心率(bpm)', '高压', '低压', '备注'])
    for r in records:
        cw.writerow([r.date, r.weight, r.body_fat, r.steps, r.water_intake, r.calories, r.sleep_hours, r.blood_glucose, r.heart_rate, r.blood_pressure_high, r.blood_pressure_low, r.note])
    output = make_response(si.getvalue().encode('utf-8-sig'))
    output.headers["Content-Disposition"] = "attachment; filename=health_data.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@bp.route('/record/delete/<int:record_id>')
@login_required
def delete(record_id):
    record = HealthRecord.query.get_or_404(record_id)
    if record.user_id != session['user_id']:
        flash("您无权删除此记录")
        return redirect(url_for('record.index'))
    db.session.delete(record)
    db.session.commit()
    flash("记录已删除")
    return redirect(url_for('record.index'))