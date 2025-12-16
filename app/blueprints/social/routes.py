from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, abort
from app.extensions import db
from app.models import User, Post, PostLike, Comment
from app.decorators import login_required
from sqlalchemy import or_  # 🔥 引入 or_ 用于组合查询条件

bp = Blueprint('community', __name__)


@bp.route('/community', methods=['GET', 'POST'])
@login_required
def index():
    user = User.query.get(session['user_id'])

    # === 处理发帖逻辑 ===
    if request.method == 'POST':
        if not user.is_admin and not user.can_post:
            flash("🚫 您已被管理员禁言！")
            return redirect(url_for('community.index'))

        title = request.form.get('title')
        content = request.form.get('content')
        is_announcement = (request.form.get('is_announcement') == 'on') if user.is_admin else False

        if title and content:
            new_post = Post(user_id=user.id, title=title, content=content, is_announcement=is_announcement)
            db.session.add(new_post)
            db.session.commit()
            flash('✅ 发布成功！')

        return redirect(url_for('community.index'))

    # === 🔥 修改点：搜索与分页逻辑 ===
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()  # 获取搜索关键词
    per_page = 10

    # 1. 建立基础查询对象
    query = Post.query

    # 2. 如果有搜索词，增加过滤条件 (标题 或 内容 包含关键词)
    if search_query:
        query = query.filter(
            or_(
                Post.title.ilike(f'%{search_query}%'),  # ilike 表示忽略大小写
                Post.content.ilike(f'%{search_query}%')
            )
        )

    # 3. 执行排序和分页
    # 排序：先按是否公告(置顶)降序，再按时间降序
    pagination = query.order_by(Post.is_announcement.desc(), Post.created_at.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)

    posts = pagination.items

    return render_template('social/community.html',
                           nickname=user.nickname,
                           posts=posts,
                           pagination=pagination,
                           user=user,
                           current_user=user,
                           search_query=search_query)  # 🔥 把搜索词传回前端，用于回显


@bp.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    user_id = session['user_id']
    post = Post.query.get_or_404(post_id)
    existing_like = PostLike.query.filter_by(user_id=user_id, post_id=post_id).first()

    liked = False
    if existing_like:
        db.session.delete(existing_like)
    else:
        db.session.add(PostLike(user_id=user_id, post_id=post_id))
        liked = True
    db.session.commit()
    return jsonify({'status': 'success', 'liked': liked, 'count': post.likes.count()})


@bp.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    content = request.form.get('content')
    if content:
        db.session.add(Comment(user_id=session['user_id'], post_id=post_id, content=content))
        db.session.commit()
    return redirect(url_for('community.index'))


@bp.route('/post/<int:post_id>/delete')
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_id != session['user_id'] and not session.get('is_admin'):
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('🗑️ 帖子已删除')
    return redirect(url_for('community.index'))


@bp.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_id != session['user_id']:
        abort(403)
    if request.method == 'POST':
        post.title = request.form.get('title')
        post.content = request.form.get('content')
        db.session.commit()
        flash('✅ 帖子修改成功！')
        return redirect(url_for('community.index'))
    return render_template('social/edit_post.html', post=post)


@bp.route('/post/<int:post_id>/toggle_pin')
@login_required
def toggle_pin(post_id):
    if not session.get('is_admin'):
        abort(403)
    post = Post.query.get_or_404(post_id)
    post.is_announcement = not post.is_announcement
    db.session.commit()
    msg = '📌 已置顶该帖' if post.is_announcement else '⬇️ 已取消置顶'
    flash(msg)
    return redirect(url_for('community.index'))