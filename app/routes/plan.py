from flask import Blueprint, render_template, request, redirect, url_for, session
from app.extensions import db
from app.models import User, HealthRecord, HealthPlan
from app.services.ai_service import call_deepseek_advisor
from app.decorators import login_required
from datetime import datetime

bp = Blueprint('plan', __name__)

@bp.route('/plan', methods=['GET', 'POST'])
@login_required
def index():
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        user_goal = request.form.get('goal')
        last_record = HealthRecord.query.filter_by(user_id=user.id).order_by(HealthRecord.date.desc()).first()
        
        current_weight = str(last_record.weight) if last_record and last_record.weight else "未知"
        age = (datetime.now().year - user.birth_year) if user.birth_year else "未知"
        medical = user.medical_history if user.medical_history else "无明显病史"
        
        system_prompt = """你是一位经验丰富的三甲医院健康管理师...（此处省略，保持原Prompt）"""
        user_prompt = f"""【用户档案】性别: {user.gender or '未知'}, 年龄: {age}, 身高: {user.height or '未知'}cm, 体重: {current_weight}kg, 病史: {medical}\n【目标】{user_goal}"""

        ai_content = call_deepseek_advisor(system_prompt, user_prompt)

        new_plan = HealthPlan(user_id=user.id, goal=user_goal, content=ai_content)
        db.session.add(new_plan)
        db.session.commit()
        return redirect(url_for('plan.index'))

    latest_plan = HealthPlan.query.filter_by(user_id=user.id).order_by(HealthPlan.created_at.desc()).first()
    return render_template('plan.html', nickname=session.get('nickname'), latest_plan=latest_plan)