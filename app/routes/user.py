from flask import Blueprint, render_template, request, redirect, url_for, session
from app.extensions import db
from app.models import User
from app.decorators import login_required

bp = Blueprint('user', __name__)

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
        return redirect(url_for('user.settings'))
        
    return render_template('settings.html', user=user)