from flask import Blueprint, render_template, request, jsonify, session
from app.services.plan_service import PlanService
from app.decorators import login_required
from app.models import HealthPlan, PlanTask  # 🔥 引入了新的 PlanTask 模型
from app.extensions import db
import json

# 定义 Blueprint
bp = Blueprint('plan', __name__)


@bp.route('/plan', methods=['GET'])
@login_required
def index():
    user_id = session['user_id']
    # 获取最新的计划
    # 模板中如果使用 latest_plan.tasks，现在访问的是数据库关联对象列表
    latest_plan = HealthPlan.query.filter_by(user_id=user_id).order_by(HealthPlan.created_at.desc()).first()
    return render_template('health/plan.html', nickname=session.get('nickname'), latest_plan=latest_plan)


@bp.route('/plan/chat', methods=['POST'])
@login_required
def chat():
    # 获取 JSON 数据
    data = request.get_json()
    user_input = data.get('message')

    # 🔥 1. 获取前端传来的历史记录 (Step 1 功能)
    history = data.get('history', [])

    # 自动判断意图
    save_flag = data.get('save', False) or ("计划" in user_input)
    user_id = session['user_id']

    if not user_input:
        return jsonify({'status': 'error', 'message': '内容不能为空'})

    try:
        # 调用 Service，透传 history
        result = PlanService.generate_health_plan(
            user_id=user_id,
            user_message=user_input,
            history=history,
            save_as_plan=save_flag
        )

        return jsonify({
            'status': 'success',
            'reply': result['reply'],
            'updated_plan': result['updated_plan']
        })
    except Exception as e:
        print(f"AI Service Error: {e}")
        return jsonify({'status': 'error', 'reply': 'AI 助手暂时有点累，请稍后再试。'})


@bp.route('/plan/toggle_task', methods=['POST'])
@login_required
def toggle_task():
    """
    🔥 2. 原子化更新任务状态 (Step 2 功能)
    前端必须发送 task_id，不再使用数组索引 task_idx
    """
    task_id = request.json.get('task_id')

    if not task_id:
        return jsonify({'status': 'error', 'message': 'Missing task_id'})

    # 直接查询 PlanTask 表
    task = PlanTask.query.get_or_404(task_id)

    # 权限校验：通过 task -> plan -> user_id 链条验证是否属于当前用户
    if task.plan.user_id != session['user_id']:
        return jsonify({'status': 'error', 'message': 'Unauthorized'})

    # 原子操作：翻转状态并提交
    task.is_done = not task.is_done
    db.session.commit()

    return jsonify({
        'status': 'success',
        'task_id': task.id,
        'new_state': task.is_done
    })