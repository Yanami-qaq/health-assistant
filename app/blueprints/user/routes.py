from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash  # 🔥 必须导入这两个
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models import User
from app.decorators import login_required
import os

bp = Blueprint('user', __name__)


@bp.route('/profile/setup', methods=['GET', 'POST'])
@login_required
def profile_setup():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        try:
            user.gender = request.form.get('gender')
            user.birth_year = int(request.form.get('birth_year'))
            user.height = float(request.form.get('height'))
            user.medical_history = request.form.get('medical_history')
            db.session.commit()
            flash('✅ 个人资料设置成功！')
            return redirect(url_for('main.dashboard'))
        except ValueError:
            flash('❌ 请输入有效的数字')
            return redirect(url_for('user.profile_setup'))

    return render_template('user/profile_setup.html', user=user)


@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        # 1. 更新普通资料
        user.nickname = request.form.get('nickname')
        user.gender = request.form.get('gender')

        try:
            # 处理可能为空的身高字段
            height_val = request.form.get('height')
            user.height = float(height_val) if height_val else None
        except ValueError:
            flash('❌ 身高必须是数字')
            return redirect(url_for('user.settings'))

        user.medical_history = request.form.get('medical_history')

        # 2. 处理头像上传
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                unique_filename = f"u{user.id}_{int(os.path.getmtime(os.getcwd()))}_{filename}"

                upload_folder = os.path.join(current_app.root_path, 'static/avatars')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)

                file.save(os.path.join(upload_folder, unique_filename))
                user.avatar = unique_filename

        db.session.commit()
        session['nickname'] = user.nickname
        flash('✅ 个人资料已更新！')
        return redirect(url_for('user.settings'))

    return render_template('user/settings.html', user=user)


# === 🔥 新增：修改密码路由 (解决报错的关键) ===
@bp.route('/update_password', methods=['POST'])
@login_required
def update_password():
    user = User.query.get(session['user_id'])

    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    # 1. 验证旧密码是否正确
    if not check_password_hash(user.password, old_password):
        flash('❌ 旧密码错误，无法修改')
        return redirect(url_for('user.settings'))

    # 2. 验证两次新密码是否一致
    if new_password != confirm_password:
        flash('❌ 两次输入的新密码不一致')
        return redirect(url_for('user.settings'))

    # 3. (可选) 可以在这里加密码强度校验，类似 auth 里的逻辑
    if len(new_password) < 6:
        flash('❌ 新密码太短，至少需要6位')
        return redirect(url_for('user.settings'))

    # 4. 更新密码
    user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
    db.session.commit()

    flash('✅ 密码修改成功！下次请使用新密码登录。')
    return redirect(url_for('user.settings'))