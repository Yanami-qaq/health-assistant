from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from datetime import datetime
from app.extensions import db
from app.models import User, HealthRecord, HealthPlan, Post, PostLike, Comment
from app.services.ai_service import call_deepseek_advisor

bp = Blueprint('main', __name__)

# --- 辅助装饰器：登录检查 ---
def login_required(func):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@bp.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@bp.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']

    # 1. 获取最近的健康记录 (优化点：只取最近14天，防止图表太挤)
    # 先倒序取前14条，再反转回正序
    recent_records = HealthRecord.query.filter_by(user_id=user_id) \
        .order_by(HealthRecord.date.desc()) \
        .limit(14) \
        .all()
    records = recent_records[::-1]

    # 2. 提取图表数据 (增加专业体征数据)
    dates = [r.date.strftime('%m-%d') for r in records]
    # 基础数据
    weights = [r.weight for r in records]
    steps = [r.steps for r in records]
    # === 新增：专业数据 (处理空值，如果没有数据则给 None，Chart.js 会自动断开连线) ===
    sleep_hours = [r.sleep_hours if r.sleep_hours else None for r in records]
    heart_rates = [r.heart_rate if r.heart_rate else None for r in records]
    bp_highs = [r.blood_pressure_high if r.blood_pressure_high else None for r in records]
    bp_lows = [r.blood_pressure_low if r.blood_pressure_low else None for r in records]

    # 3. 获取最新的 AI 计划
    latest_plan = HealthPlan.query.filter_by(user_id=user_id).order_by(HealthPlan.created_at.desc()).first()

    # 4. 计算今日活力值 (升级版：三维健康评分)
    today_score = 0
    if records:
        last_rec = records[-1]  # 获取最新一条记录
        user = User.query.get(user_id)  # 获取用户资料以计算 BMI

        # --- 维度 A: 运动得分 (50%) ---
        # 逻辑：目标 10000 步，按比例得分，最高 100
        step_val = last_rec.steps or 0
        score_move = min((step_val / 10000) * 100, 100)

        # --- 维度 B: 睡眠得分 (30%) ---
        # 逻辑：7-9小时满分(100)，6-7或9-10小时及格(80)，其他不及格(60)
        sleep_val = last_rec.sleep_hours or 0
        if 7 <= sleep_val <= 9:
            score_sleep = 100
        elif 6 <= sleep_val < 7 or 9 < sleep_val <= 10:
            score_sleep = 80
        else:
            score_sleep = 60

        # --- 维度 C: BMI 健康分 (20%) ---
        # 逻辑：BMI 在 18.5~24 之间得满分。如果用户没填身高，给个平均分 80。
        score_body = 80  # 默认分
        if user.height and last_rec.weight:
            # BMI = 体重(kg) / 身高(m)^2
            height_m = user.height / 100
            bmi = last_rec.weight / (height_m * height_m)

            if 18.5 <= bmi <= 24:
                score_body = 100
            elif 24 < bmi <= 28 or 17 <= bmi < 18.5:
                score_body = 80  # 微胖或偏瘦
            else:
                score_body = 60  # 肥胖或过瘦

        # --- 综合加权计算 ---
        today_score = int(score_move * 0.5 + score_sleep * 0.3 + score_body * 0.2)

    # 5. 计算连续打卡天数 (Gamification)
    streak_days = 0
    if records:
        # 取出所有日期并倒序（从最新开始查）
        all_dates = [r.date for r in records]
        all_dates.reverse()

        # 检查最新一条是否是今天或昨天（否则算断签）
        check_date = all_dates[0]
        # 注意：这里需要 datetime 模块，文件头部已导入
        if (datetime.now().date() - check_date).days <= 1:
            streak_days = 1
            previous_date = check_date

            # 遍历剩下的日期
            for d in all_dates[1:]:
                if (previous_date - d).days == 1:  # 如果刚好差1天
                    streak_days += 1
                    previous_date = d
                else:
                    break  # 断签停止
        else:
            streak_days = 0

    return render_template('dashboard.html',
                           nickname=session.get('nickname'),
                           dates=dates,
                           weights=weights,
                           steps=steps,
                           sleep_hours=sleep_hours,
                           heart_rates=heart_rates,
                           bp_highs=bp_highs,
                           bp_lows=bp_lows,
                           latest_plan=latest_plan,
                           today_score=today_score,
                           streak_days=streak_days)  # 传入新参数

@bp.route('/record', methods=['GET', 'POST'])
@login_required
def record():
    if request.method == 'POST':
        date_str = request.form.get('date')
        try:
            record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            return "日期格式错误"

        new_record = HealthRecord(
            user_id=session['user_id'],
            date=record_date,
            weight=float(request.form.get('weight') or 0),
            steps=int(request.form.get('steps') or 0),
            calories=int(request.form.get('calories') or 0),
            note=request.form.get('note'),
            sleep_hours=float(request.form.get('sleep_hours') or 0) if request.form.get('sleep_hours') else None,
            heart_rate=int(request.form.get('heart_rate') or 0) if request.form.get('heart_rate') else None,
            blood_pressure_high=int(request.form.get('bp_high') or 0) if request.form.get('bp_high') else None,
            blood_pressure_low=int(request.form.get('bp_low') or 0) if request.form.get('bp_low') else None
        )
        db.session.add(new_record)
        db.session.commit()
        return redirect(url_for('main.record'))

    user_records = HealthRecord.query.filter_by(user_id=session['user_id']).order_by(HealthRecord.date.desc()).all()
    return render_template('record.html', nickname=session.get('nickname'), records=user_records)


@bp.route('/plan', methods=['GET', 'POST'])
@login_required
def plan():
    # 1. 获取当前登录用户
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        # 2. 获取用户在网页上输入的目标 (例如："我想在一个月内减重 2kg")
        user_goal = request.form.get('goal')

        # 3. 获取用户最近的一次身体数据 (为了告诉 AI 用户现在的状态)
        last_record = HealthRecord.query.filter_by(user_id=user.id).order_by(HealthRecord.date.desc()).first()

        # --- 数据预处理 (防止数据为空导致报错) ---
        current_weight = str(last_record.weight) if last_record and last_record.weight else "未知"
        # 算出年龄
        age = (datetime.now().year - user.birth_year) if user.birth_year else "未知"
        # 获取病史 (非常重要，防止 AI 给出危险建议)
        medical = user.medical_history if user.medical_history else "无明显病史"

        # 4. 🔥 核心逻辑：构造“超强”提示词 (Prompt)
        # 我们把用户的“档案”和“目标”拼接在一起发给 DeepSeek
        system_prompt = """
        你是一位经验丰富的三甲医院健康管理师和专业健身教练。
        请根据用户的【个人档案】和【健康目标】，制定一份科学、可执行的【每日健康计划】。

        计划必须包含以下模块：
        1. 🥗 **饮食建议**：推荐早餐、午餐、晚餐的搭配原则（不需要具体食谱，要原则）。
        2. 🏃 **运动方案**：具体的运动类型、时长和心率区间建议。
        3. ⚠️ **风险规避**：结合用户的病史（如果有），指出需要避免的运动或食物。

        请使用 Markdown 格式排版，语气亲切、专业、充满鼓励。
        """

        user_prompt = f"""
        【用户档案】
        - 性别: {user.gender or '未知'}
        - 年龄: {age} 岁
        - 身高: {user.height or '未知'} cm
        - 当前体重: {current_weight} kg
        - 既往病史: {medical}

        【用户的核心目标】
        {user_goal}

        (请根据以上信息，为我量身定制计划)
        """

        # 5. 调用 AI 服务 (这个函数在 services/ai_service.py 里)
        # 注意：这里可能会因为网络延迟卡几秒，是正常的
        ai_content = call_deepseek_advisor(system_prompt, user_prompt)

        # 6. 保存结果到数据库 (这样用户下次还能看到，不用重新生成)
        new_plan = HealthPlan(
            user_id=user.id,
            goal=user_goal,
            content=ai_content
        )
        db.session.add(new_plan)
        db.session.commit()

        # 刷新页面显示结果
        return redirect(url_for('main.plan'))

    # GET 请求：查询最新的计划展示给用户
    latest_plan = HealthPlan.query.filter_by(user_id=user.id).order_by(HealthPlan.created_at.desc()).first()
    return render_template('plan.html', nickname=session.get('nickname'), latest_plan=latest_plan)

@bp.route('/community', methods=['GET', 'POST'])
@login_required
def community():
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        # === 改动 1: 禁言拦截 (管理员拥有豁免权) ===
        # 逻辑：如果不是管理员，且被禁言了，才拦截
        if not user.is_admin and not user.can_post:
            flash("🚫 您已被管理员禁言，无法发布新内容！")
            return redirect(url_for('main.community'))

        # 获取数据
        title = request.form.get('title')
        content = request.form.get('content')

        if not title or not content:
            flash("标题和内容不能为空")
            return redirect(url_for('main.community'))

        # === 改动 2: 处理公告标记 (仅限管理员) ===
        is_announcement = False
        if user.is_admin:
            # Checkbox 如果被勾选，值为 'on'；没勾选则为 None
            is_announcement = (request.form.get('is_announcement') == 'on')

        new_post = Post(
            user_id=user.id,
            title=title,
            content=content,
            is_announcement=is_announcement # 写入数据库
        )
        db.session.add(new_post)
        db.session.commit()
        
        if is_announcement:
            flash("📢 公告发布成功！")
        else:
            flash("发布成功！")
        
        return redirect(url_for('main.community'))

    # === 展示帖子列表 (GET) ===
    # 优化排序：公告置顶 (is_announcement desc)，然后按时间倒序
    # desc() 表示 True 在前 (在 MySQL 中 True=1, False=0)
    all_posts = Post.query.order_by(Post.is_announcement.desc(), Post.created_at.desc()).all()
    
    return render_template('community.html', 
                           nickname=user.nickname, 
                           posts=all_posts, 
                           user=user,
                           current_user=user)

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        user.nickname = request.form.get('nickname')
        user.gender = request.form.get('gender')
        user.height = float(request.form.get('height') or 0) if request.form.get('height') else None
        user.medical_history = request.form.get('medical_history')
        
        db.session.commit()
        session['nickname'] = user.nickname
        return redirect(url_for('main.settings'))
        
    return render_template('settings.html', user=user)

# === 新增功能 1: 点赞/取消点赞接口 ===
@bp.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    user_id = session['user_id']
    post = Post.query.get_or_404(post_id)
    
    # 检查是否已经点过赞
    existing_like = PostLike.query.filter_by(user_id=user_id, post_id=post_id).first()
    
    liked = False
    if existing_like:
        # 如果已点赞，就取消 (删除记录)
        db.session.delete(existing_like)
        liked = False
    else:
        # 如果没点赞，就添加
        new_like = PostLike(user_id=user_id, post_id=post_id)
        db.session.add(new_like)
        liked = True
        
    db.session.commit()
    
    # 返回 JSON 给前端 JS 更新界面，不用刷新网页
    return jsonify({
        'status': 'success',
        'liked': liked,
        'count': post.likes.count()
    })

# === 新增功能 2: 发表评论接口 ===
@bp.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    content = request.form.get('content')
    if not content:
        flash("评论内容不能为空")
        return redirect(url_for('main.community'))
        
    new_comment = Comment(
        user_id=session['user_id'],
        post_id=post_id,
        content=content
    )
    db.session.add(new_comment)
    db.session.commit()
    
    return redirect(url_for('main.community'))

# --- 管理员路由 ---
@bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not session.get('is_admin'):
        return "🚫 权限不足"
    users = User.query.all()
    return render_template('admin_dashboard.html', users=users)

# === 新增功能 1: 设置/取消管理员 ===
@bp.route('/admin/toggle_admin/<int:user_id>')
@login_required
def toggle_admin(user_id):
    # 权限检查
    if not session.get('is_admin'):
        return "🚫 权限不足"
    
    user = User.query.get_or_404(user_id)
    
    # 保护机制：不能取消自己的管理员权限
    if user.id == session['user_id']:
        flash("不能取消自己的管理员权限")
        return redirect(url_for('main.admin_dashboard'))

    user.is_admin = not user.is_admin # 取反：是变否，否变是
    db.session.commit()
    
    action = "设为管理员" if user.is_admin else "降为普通用户"
    flash(f"已将用户 {user.nickname} {action}")
    return redirect(url_for('main.admin_dashboard'))

# === 新增功能 2: 封禁/解封用户 ===
@bp.route('/admin/toggle_ban/<int:user_id>')
@login_required
def toggle_ban(user_id):
    if not session.get('is_admin'):
        return "🚫 权限不足"
        
    user = User.query.get_or_404(user_id)
    
    if user.id == session['user_id']:
        flash("不能封禁自己")
        return redirect(url_for('main.admin_dashboard'))
        
    user.is_banned = not user.is_banned
    db.session.commit()
    
    action = "封禁" if user.is_banned else "解封"
    flash(f"已{action}用户 {user.nickname}")
    return redirect(url_for('main.admin_dashboard'))

# === 功能 3: 删除用户 (确保这个函数存在) ===
@bp.route('/admin/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if not session.get('is_admin'):
        return "权限不足"
        
    user = User.query.get_or_404(user_id)
    
    if user.id == session['user_id']:
        flash("不能删除自己")
        return redirect(url_for('main.admin_dashboard'))

    # 级联删除所有相关数据
    HealthRecord.query.filter_by(user_id=user_id).delete()
    HealthPlan.query.filter_by(user_id=user_id).delete()
    Post.query.filter_by(user_id=user_id).delete()
    Comment.query.filter_by(user_id=user_id).delete() # 记得删评论
    PostLike.query.filter_by(user_id=user_id).delete() # 记得删点赞
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f"已彻底删除用户 {user.nickname}")
    return redirect(url_for('main.admin_dashboard'))

# === 新增功能 4: 禁言/解除禁言 ===
@bp.route('/admin/toggle_posting/<int:user_id>')
@login_required
def toggle_posting(user_id):
    if not session.get('is_admin'):
        return "🚫 权限不足"
    
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash("无法禁言管理员")
        return redirect(url_for('main.admin_dashboard'))
        
    user.can_post = not user.can_post # 取反
    db.session.commit()
    
    status = "解除禁言" if user.can_post else "禁言"
    flash(f"已对用户 {user.nickname} {status}")
    return redirect(url_for('main.admin_dashboard'))

# === 新增功能 5: 管理员删帖 ===
@bp.route('/admin/delete_post/<int:post_id>')
@login_required
def delete_post(post_id):
    if not session.get('is_admin'):
        return "🚫 权限不足"
        
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    
    flash("帖子已强制删除")
    return redirect(url_for('main.community'))