from flask import Blueprint, render_template, request, jsonify, session
from app.services.plan_service import PlanService
from app.decorators import login_required
from app.models import HealthPlan
from app.extensions import db
import json

# 定义 Blueprint
bp = Blueprint('plan', __name__)

@bp.route('/plan', methods=['GET'])
@login_required
def index():
    user_id = session['user_id']
    latest_plan = HealthPlan.query.filter_by(user_id=user_id).order_by(HealthPlan.created_at.desc()).first()
    return render_template('health/plan.html', nickname=session.get('nickname'), latest_plan=latest_plan)

@bp.route('/plan/chat', methods=['POST'])
@login_required
def chat():
    user_input = request.json.get('message')
    save_flag = request.json.get('save', False) or ("计划" in user_input)
    user_id = session['user_id']

    if not user_input: return jsonify({'status': 'error', 'message': '内容不能为空'})

    try:
        # 核心逻辑移入 Service
        result = PlanService.generate_health_plan(user_id, user_input, save_flag)
        return jsonify({'status': 'success', 'reply': result['reply'], 'updated_plan': result['updated_plan']})
    except Exception as e:
        print(f"AI Error: {e}")
        return jsonify({'status': 'error', 'reply': 'AI 暂时掉线了，请重试。'})

@bp.route('/plan/toggle_task', methods=['POST'])
@login_required
def toggle_task():
    plan_id = request.json.get('plan_id')
    task_idx = request.json.get('task_idx')
    plan = HealthPlan.query.get_or_404(plan_id)
    if plan.user_id != session['user_id']: return jsonify({'status': 'error'})

    tasks = plan.get_tasks()
    if 0 <= task_idx < len(tasks):
        tasks[task_idx]['done'] = not tasks[task_idx]['done']
        plan.tasks_json = json.dumps(tasks, ensure_ascii=False)
        db.session.commit()
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'})