from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from app.models import User
from app.extensions import db
from app.services.email_service import EmailService

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        nickname = request.form.get('nickname')
        email = request.form.get('email')

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('用户名或邮箱已存在')
            return redirect(url_for('auth.register'))

        new_user = User(
            username=username,
            password=generate_password_hash(password, method='pbkdf2:sha256'),
            nickname=nickname,
            email=email
        )
        db.session.add(new_user)
        db.session.commit()

        # 发送欢迎邮件
        EmailService.send_welcome_email(new_user)

        flash('注册成功！欢迎邮件已发送，请登录')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        login_type = request.form.get('login_type')

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password, password):
            flash('登录失败：用户名或密码错误')
            return redirect(url_for('auth.login'))

        if user.is_banned:
            flash('🚫 该账号已被封禁，无法登录！')
            return redirect(url_for('auth.login'))

        if login_type == 'admin' and not user.is_admin:
            flash('❌ 错误：该账号不是管理员')
            return redirect(url_for('auth.login'))
        if login_type == 'user' and user.is_admin:
            flash('🚫 错误：管理员请切换入口')
            return redirect(url_for('auth.login'))

        session['user_id'] = user.id
        session['nickname'] = user.nickname
        session['is_admin'] = user.is_admin

        if user.is_admin:
            return redirect(url_for('admin.dashboard'))
        else:
            if not user.height or not user.birth_year:
                return redirect(url_for('user.profile_setup'))
            return redirect(url_for('main.dashboard'))

    return render_template('auth/login.html')


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


# === 🔥 新增：忘记密码路由 ===
@bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()

        if user:
            # 生成 Token
            s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            token = s.dumps(user.email, salt='recover-key')
            # 发送邮件
            EmailService.send_password_reset_email(user, token)

        flash('📩 如果该邮箱已注册，重置邮件已发送，请检查收件箱。')
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html')


# === 🔥 新增：重置密码路由 ===
@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        # 验证 Token，15分钟有效 (900秒)
        email = s.loads(token, salt='recover-key', max_age=900)
    except SignatureExpired:
        flash('❌ 链接已过期，请重新申请重置。')
        return redirect(url_for('auth.forgot_password'))
    except BadSignature:
        flash('❌ 无效的重置链接。')
        return redirect(url_for('auth.forgot_password'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('❌ 用户不存在。')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('❌ 两次输入的密码不一致')
            return redirect(url_for('auth.reset_password', token=token))

        user.password = generate_password_hash(password, method='pbkdf2:sha256')
        db.session.commit()

        flash('✅ 密码重置成功！请使用新密码登录。')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)