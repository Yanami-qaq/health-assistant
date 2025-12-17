from flask_mail import Message
from flask import current_app, render_template, url_for
from app.extensions import mail
from threading import Thread
import logging

# 配置 Logger，确保错误能被记录下来
logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_async_email(app, msg):
        """后台线程：发送邮件"""
        with app.app_context():
            try:
                mail.send(msg)
                logger.info(f"✅ 邮件已成功发送给: {msg.recipients}")
            except Exception as e:
                # 使用 logger.error 记录详细堆栈信息
                logger.error(f"❌ 邮件发送失败: {e}", exc_info=True)

    @staticmethod
    def send_welcome_email(user):
        """发送注册欢迎邮件"""
        if not user.email:
            return

        app = current_app._get_current_object()

        try:
            # 🔥 核心修改：使用 render_template 渲染 HTML 文件
            # 这样不仅代码整洁，而且在模板中使用的 url_for(..., _external=True) 会自动生成正确的域名链接
            html_body = render_template('email/welcome.html', user=user)

            msg = Message(
                subject="🎉 欢迎加入 Health Assistant！",
                recipients=[user.email],
                html=html_body
            )

            thread = Thread(target=EmailService.send_async_email, args=(app, msg))
            thread.start()
        except Exception as e:
            logger.error(f"构建欢迎邮件失败: {e}", exc_info=True)

    @staticmethod
    def send_password_reset_email(user, token):
        """发送重置密码邮件"""
        if not user.email:
            return

        app = current_app._get_current_object()

        try:
            # 🔥 核心修改：传入 token，由模板负责生成链接
            html_body = render_template('email/reset_password.html', user=user, token=token)

            msg = Message(
                subject="🔒 重置您的密码 - Health Assistant",
                recipients=[user.email],
                html=html_body
            )

            thread = Thread(target=EmailService.send_async_email, args=(app, msg))
            thread.start()
        except Exception as e:
            logger.error(f"构建重置密码邮件失败: {e}", exc_info=True)