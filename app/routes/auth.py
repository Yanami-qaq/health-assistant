from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from app.extensions import db

bp = Blueprint('auth', __name__)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        nickname = request.form.get('nickname')

        if User.query.filter_by(username=username).first():
            flash('用户名已存在')
            return redirect(url_for('auth.register'))

        new_user = User(
            username=username,
            password=generate_password_hash(password, method='pbkdf2:sha256'),
            nickname=nickname
        )
        db.session.add(new_user)
        db.session.commit()
        flash('注册成功！请登录')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        login_type = request.form.get('login_type')

        user = User.query.filter_by(username=username).first()

        # 1. 验证账号密码
        if not user or not check_password_hash(user.password, password):
            flash('登录失败：用户名或密码错误')
            return redirect(url_for('auth.login'))

        # 2. 封禁检查
        if user.is_banned:
            flash('🚫 该账号已被封禁，无法登录！')
            return redirect(url_for('auth.login'))

        # 3. 身份入口检查
        if login_type == 'admin' and not user.is_admin:
            flash('❌ 错误：该账号不是管理员')
            return redirect(url_for('auth.login'))
        if login_type == 'user' and user.is_admin:
            flash('🚫 错误：管理员请切换入口')
            return redirect(url_for('auth.login'))

        # 4. 写入 Session
        session['user_id'] = user.id
        session['nickname'] = user.nickname
        session['is_admin'] = user.is_admin

        # 5. 跳转逻辑
        if user.is_admin:
            return redirect(url_for('admin.dashboard'))
        else:
            # === 🔥 核心修改：检查资料完整度 ===
            # 如果是普通用户，且身高为空（说明是新用户没填过资料），强制跳转去填资料
            if not user.height or not user.birth_year:
                return redirect(url_for('user.profile_setup'))

            # 资料齐全，才让进仪表盘
            return redirect(url_for('main.dashboard'))

    return render_template('login.html')


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))