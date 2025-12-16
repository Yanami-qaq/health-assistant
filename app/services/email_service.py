from flask_mail import Message
from flask import current_app, url_for
from app.extensions import mail
from threading import Thread


class EmailService:
    @staticmethod
    def send_async_email(app, msg):
        """后台线程：发送邮件"""
        with app.app_context():
            try:
                mail.send(msg)
                print(f"✅ 邮件已发送给: {msg.recipients}")
            except Exception as e:
                print(f"❌ 邮件发送失败: {e}")

    @staticmethod
    def send_welcome_email(user):
        """发送注册欢迎邮件"""
        if not user.email:
            return

        app = current_app._get_current_object()

        msg = Message(
            subject="🎉 欢迎加入 Health Assistant！",
            recipients=[user.email],
            html=f"""
            <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                <h2 style="color: #11998e;">你好，{user.nickname}！</h2>
                <p>感谢注册 Health Assistant。我们很高兴能陪伴你开启健康之旅！</p>
                <p>你可以点击下方链接登录你的账户：</p>
                <a href="http://127.0.0.1:5000/auth/login" style="background-color: #11998e; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">立即登录</a>
                <br><br>
                <hr style="border: 0; border-top: 1px solid #eee;">
                <small style="color: #999;">此邮件由系统自动发送，请勿回复。<br>Health Assistant 团队</small>
            </div>
            """
        )

        thread = Thread(target=EmailService.send_async_email, args=(app, msg))
        thread.start()

    @staticmethod
    def send_password_reset_email(user, token):
        """发送重置密码邮件"""
        if not user.email:
            return

        app = current_app._get_current_object()

        # 生成完整链接
        reset_url = url_for('auth.reset_password', token=token, _external=True)

        msg = Message(
            subject="🔒 重置您的密码 - Health Assistant",
            recipients=[user.email],
            html=f"""
            <div style="font-family: 'Segoe UI', Arial, sans-serif; padding: 20px; color: #333; max-width: 600px;">
                <h3 style="color: #11998e;">重置密码请求</h3>
                <p>您好 {user.nickname}，</p>
                <p>我们收到了重置您 Health Assistant 账户密码的请求。</p>
                <p>请点击下方按钮设置新密码（15分钟内有效）：</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" style="background-color: #11998e; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">立即重置密码</a>
                </div>
                <p>或者将以下链接复制到浏览器中打开：</p>
                <p style="word-break: break-all; color: #666; font-size: 12px;">{reset_url}</p>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #999; font-size: 12px;">如果您没有请求重置密码，请忽略此邮件，您的账户是安全的。</p>
            </div>
            """
        )

        thread = Thread(target=EmailService.send_async_email, args=(app, msg))
        thread.start()