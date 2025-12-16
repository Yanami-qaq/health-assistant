from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models import User
from app.decorators import login_required
from app.blueprints.user import bp

@bp.route('/profile/setup', methods=['GET', 'POST'])
@login_required
def profile_setup():
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        user.gender = request.form.get('gender')
        user.birth_year = request.form.get('birth_year')
        user.height = float(request.form.get('height'))
        user.medical_history = request.form.get('medical_history')
        db.session.commit()
        flash('🎉 档案建立成功！欢迎使用 Health Assistant')
        return redirect(url_for('main.dashboard'))

    return render_template('user/profile_setup.html', user=user)

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        user.nickname = request.form.get('nickname')
        user.gender = request.form.get('gender')
        height_val = request.form.get('height')
        user.height = float(height_val) if height_val else None
        user.medical_history = request.form.get('medical_history')
        db.session.commit()
        session['nickname'] = user.nickname
        flash('✅ 个人资料已更新！')
        return redirect(url_for('user.settings'))

    return render_template('user/settings.html', user=user)

@bp.route('/settings/password', methods=['POST'])
@login_required
def update_password():
    user = User.query.get(session['user_id'])
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not check_password_hash(user.password, old_password):
        flash('❌ 旧密码错误')
        return redirect(url_for('user.settings'))

    if new_password != confirm_password:
        flash('❌ 两次新密码不一致')
        return redirect(url_for('user.settings'))

    user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
    db.session.commit()
    session.clear()
    flash('✅ 密码修改成功，请重新登录')
    return redirect(url_for('auth.login'))