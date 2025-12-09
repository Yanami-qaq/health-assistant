from flask import Blueprint, render_template, redirect, url_for, session, flash
from app.extensions import db
from app.models import User, Post, HealthRecord, HealthPlan, Comment, PostLike
from app.decorators import login_required

bp = Blueprint('admin', __name__)

# 中间件：检查管理员权限
@bp.before_request
def check_admin():
    if not session.get('is_admin'):
        return "🚫 权限不足"

@bp.route('/admin/dashboard')
@login_required
def dashboard():
    users = User.query.all()
    return render_template('admin_dashboard.html', users=users)

@bp.route('/admin/toggle_admin/<int:user_id>')
@login_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == session['user_id']:
        flash("不能取消自己的权限")
    else:
        user.is_admin = not user.is_admin
        db.session.commit()
    return redirect(url_for('admin.dashboard'))

@bp.route('/admin/toggle_ban/<int:user_id>')
@login_required
def toggle_ban(user_id):
    user = User.query.get_or_404(user_id)
    if user.id != session['user_id']:
        user.is_banned = not user.is_banned
        db.session.commit()
    return redirect(url_for('admin.dashboard'))

@bp.route('/admin/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id != session['user_id']:
        # 级联删除
        HealthRecord.query.filter_by(user_id=user_id).delete()
        HealthPlan.query.filter_by(user_id=user_id).delete()
        Post.query.filter_by(user_id=user_id).delete()
        Comment.query.filter_by(user_id=user_id).delete()
        PostLike.query.filter_by(user_id=user_id).delete()
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('admin.dashboard'))

@bp.route('/admin/toggle_posting/<int:user_id>')
@login_required
def toggle_posting(user_id):
    user = User.query.get_or_404(user_id)
    if not user.is_admin:
        user.can_post = not user.can_post
        db.session.commit()
    return redirect(url_for('admin.dashboard'))

@bp.route('/admin/delete_post/<int:post_id>')
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    # 注意：这里删除完跳回社区，还是跳回管理后台？通常跳回来源页。这里简单跳回社区。
    return redirect(url_for('community.index'))