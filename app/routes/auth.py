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
        login_type = request.form.get('login_type')  # 获取用户选的是 "user" 还是 "admin"

        user = User.query.filter_by(username=username).first()

        # 1. 基础验证：查无此人 或 密码错误
        if not user or not check_password_hash(user.password, password):
            flash('登录失败：用户名或密码错误')
            return redirect(url_for('auth.login'))

        # === 2. 新增：封禁检查 (必须放在密码验证之后) ===
        # 如果我们在 User 模型里加了 is_banned 字段，这里必须拦截
        if getattr(user, 'is_banned', False): # 使用 getattr 防止数据库还没更新报错
            flash('🚫 该账号已被封禁，无法登录！')
            return redirect(url_for('auth.login'))

        # === 3. 身份双向拦截 (防止走错门) ===
        # 情况 A：普通人想走管理员通道 -> 拦截
        if login_type == 'admin' and not user.is_admin:
            flash('❌ 错误：该账号不是管理员，请切换到“普通用户登录”！')
            return redirect(url_for('auth.login'))

        # 情况 B：管理员想走普通用户通道 -> 拦截 
        # (这步是可选的，看你是否允许管理员登录前台，通常分开比较好)
        if login_type == 'user' and user.is_admin:
            flash('🚫 错误：您是管理员，请点击上方的“管理员登录”切换入口！')
            return redirect(url_for('auth.login'))

        # 4. 登录成功，写入 Session
        session['user_id'] = user.id
        session['nickname'] = user.nickname
        session['is_admin'] = user.is_admin

        # 5. 根据身份跳转
        if user.is_admin:
            return redirect(url_for('main.admin_dashboard'))
        else:
            return redirect(url_for('main.dashboard'))

    # GET 请求：显示登录页面
    return render_template('login.html')

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))