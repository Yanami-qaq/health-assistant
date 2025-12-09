from flask import Blueprint, render_template, request, redirect, url_for, session
from app.extensions import db
from app.models import HealthRecord
from app.decorators import login_required
from datetime import datetime

# 注意：这里 Blueprint 名字叫 'record'
bp = Blueprint('record', __name__)

@bp.route('/record', methods=['GET', 'POST'])
@login_required
def index():
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
        return redirect(url_for('record.index'))

    user_records = HealthRecord.query.filter_by(user_id=session['user_id']).order_by(HealthRecord.date.desc()).all()
    return render_template('record.html', nickname=session.get('nickname'), records=user_records)