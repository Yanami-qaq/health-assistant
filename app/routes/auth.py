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
            return '用户名已存在'

        new_user = User(
            username=username,
            password=generate_password_hash(password, method='pbkdf2:sha256'), 
            nickname=nickname
        )
        db.session.add(new_user)
        db.session.commit()
        return '注册成功！<a href="/login">去登录</a>'

    return render_template('register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        login_type = request.form.get('login_type') 

        user = User.query.filter_by(username=username).first()

        # 1. 基础验证
        if not user or not check_password_hash(user.password, password):
            return '登录失败：用户名或密码错误'

        # 2. 身份双向拦截
        if login_type == 'admin' and not user.is_admin:
            return '❌ 错误：该账号不是管理员，请切换到“普通用户登录”！'
        if login_type == 'user' and user.is_admin:
            return '🚫 错误：您是管理员，请点击上方的“管理员登录”切换入口！'

        # 3. 登录成功
        session['user_id'] = user.id
        session['nickname'] = user.nickname
        session['is_admin'] = user.is_admin

        if user.is_admin:
            return redirect(url_for('main.admin_dashboard'))
        else:
            return redirect(url_for('main.dashboard'))

    return render_template('login.html')

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))