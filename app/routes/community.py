from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.extensions import db
from app.models import User, Post, PostLike, Comment
from app.decorators import login_required

bp = Blueprint('community', __name__)

@bp.route('/community', methods=['GET', 'POST'])
@login_required
def index():
    user = User.query.get(session['user_id'])
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
            
        return redirect(url_for('community.index'))

    all_posts = Post.query.order_by(Post.is_announcement.desc(), Post.created_at.desc()).all()
    return render_template('community.html', nickname=user.nickname, posts=all_posts, user=user, current_user=user)

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