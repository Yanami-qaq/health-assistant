from flask import Blueprint, render_template, request, jsonify, session
from app.services.plan_service import PlanService
from app.services.assessment_service import AssessmentService
from app.decorators import login_required
from app.models import HealthPlan, PlanTask, User  # 🔥 引入了新的 PlanTask 模型和 User
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
    user = User.query.get(user_id)
    return render_template('health/plan.html', nickname=session.get('nickname'), latest_plan=latest_plan, user=user)


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


@bp.route('/plan/assessment', methods=['GET'])
@login_required
def get_assessment():
    """获取健康状态评估（先检查数据库，如果没有则生成新的）"""
    user_id = session['user_id']
    try:
        # 先尝试从数据库获取已保存的评估
        saved_assessment = AssessmentService.get_latest_assessment(user_id)
        if saved_assessment:
            return jsonify(saved_assessment)
        
        # 如果没有保存的评估，生成新的
        assessment = AssessmentService.generate_health_assessment(user_id)
        return jsonify(assessment)
    except Exception as e:
        print(f"Assessment Error: {e}")
        return jsonify({
            'status': 'error',
            'message': '健康评估失败，请稍后重试',
            'health_score': 0
        }), 500


@bp.route('/plan/assessment/regenerate', methods=['POST'])
@login_required
def regenerate_assessment():
    """重新生成健康状态评估（强制生成新的评估）"""
    user_id = session['user_id']
    try:
        assessment = AssessmentService.generate_health_assessment(user_id)
        return jsonify(assessment)
    except Exception as e:
        print(f"Regenerate Assessment Error: {e}")
        return jsonify({
            'status': 'error',
            'message': '健康评估失败，请稍后重试',
            'health_score': 0
        }), 500


@bp.route('/plan/save_goal', methods=['POST'])
@login_required
def save_goal():
    """保存用户健康目标"""
    user_id = session['user_id']
    data = request.get_json()
    goal_type = data.get('goal_type')
    
    if goal_type not in ['weight_loss', 'muscle_gain', 'maintain']:
        return jsonify({'status': 'error', 'message': '无效的目标类型'}), 400
    
    try:
        user = User.query.get(user_id)
        user.goal_type = goal_type
        db.session.commit()
        return jsonify({'status': 'success', 'message': '目标已保存'})
    except Exception as e:
        db.session.rollback()
        print(f"Save Goal Error: {e}")
        return jsonify({'status': 'error', 'message': '保存失败，请稍后重试'}), 500


@bp.route('/plan/generate_quick', methods=['POST'])
@login_required
def generate_quick_plan():
    """根据用户目标快速生成计划"""
    user_id = session['user_id']
    try:
        from app.models import HealthRecord
        
        user = User.query.get(user_id)
        goal_type = user.goal_type or 'maintain'
        
        # 检查健康数据完整性
        last_record = HealthRecord.query.filter_by(user_id=user_id) \
            .order_by(HealthRecord.date.desc()).first()
        
        # 异常事件流1：无法获取健康数据
        missing_data = []
        if not last_record:
            missing_data.append('健康记录')
        else:
            if not user.height:
                missing_data.append('身高')
            if not last_record.weight:
                missing_data.append('体重')
        
        if missing_data:
            return jsonify({
                'status': 'data_missing',
                'message': '无法获取健康数据，请检查设置',
                'missing_data': missing_data,
                'suggestion': '建议补充数据或重新连接应用'
            }), 400
        
        # 根据目标类型生成不同的提示词
        goal_messages = {
            'weight_loss': '请根据我的健康数据，制定一个科学有效的减肥计划，包括饮食建议和运动安排。',
            'muscle_gain': '请根据我的健康数据，制定一个增肌计划，包括营养搭配和力量训练建议。',
            'maintain': '请根据我的健康数据，制定一个维持健康体重的计划，包括均衡饮食和适量运动建议。'
        }
        
        user_message = goal_messages.get(goal_type, goal_messages['maintain'])
        
        # 调用PlanService生成计划
        result = PlanService.generate_health_plan(
            user_id=user_id,
            user_message=user_message,
            history=None,
            save_as_plan=True  # 强制保存为计划
        )
        
        if result.get('updated_plan'):
            return jsonify({
                'status': 'success',
                'message': '计划生成成功',
                'reply': result.get('reply', '')
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '计划生成失败，请稍后重试'
            }), 500
            
    except Exception as e:
        print(f"Generate Quick Plan Error: {e}")
        return jsonify({
            'status': 'error',
            'message': '计划生成失败，请稍后重试'
        }), 500


@bp.route('/plan/add_task', methods=['POST'])
@login_required
def add_task():
    """添加新任务"""
    user_id = session['user_id']
    data = request.get_json()
    title = data.get('title', '').strip()
    
    if not title:
        return jsonify({'status': 'error', 'message': '任务内容不能为空'}), 400
    
    try:
        # 获取用户最新的计划
        latest_plan = HealthPlan.query.filter_by(user_id=user_id).order_by(HealthPlan.created_at.desc()).first()
        
        if not latest_plan:
            # 如果没有计划，创建一个新计划
            latest_plan = HealthPlan(
                user_id=user_id,
                goal="用户自定义计划",
                content=""
            )
            db.session.add(latest_plan)
            db.session.flush()
        
        # 创建新任务
        new_task = PlanTask(
            plan_id=latest_plan.id,
            title=title,
            is_done=False
        )
        db.session.add(new_task)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '任务添加成功',
            'task': {
                'id': new_task.id,
                'title': new_task.title,
                'done': new_task.is_done
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"Add Task Error: {e}")
        return jsonify({'status': 'error', 'message': '添加任务失败，请稍后重试'}), 500


@bp.route('/plan/update_task', methods=['POST'])
@login_required
def update_task():
    """更新任务内容"""
    user_id = session['user_id']
    data = request.get_json()
    task_id = data.get('task_id')
    title = data.get('title', '').strip()
    
    if not task_id:
        return jsonify({'status': 'error', 'message': '任务ID不能为空'}), 400
    
    if not title:
        return jsonify({'status': 'error', 'message': '任务内容不能为空'}), 400
    
    try:
        task = PlanTask.query.get_or_404(task_id)
        
        # 权限校验
        if task.plan.user_id != user_id:
            return jsonify({'status': 'error', 'message': '无权限修改此任务'}), 403
        
        task.title = title
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '任务更新成功',
            'task': {
                'id': task.id,
                'title': task.title,
                'done': task.is_done
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"Update Task Error: {e}")
        return jsonify({'status': 'error', 'message': '更新任务失败，请稍后重试'}), 500


@bp.route('/plan/delete_task', methods=['POST'])
@login_required
def delete_task():
    """删除任务"""
    user_id = session['user_id']
    data = request.get_json()
    task_id = data.get('task_id')
    
    if not task_id:
        return jsonify({'status': 'error', 'message': '任务ID不能为空'}), 400
    
    try:
        task = PlanTask.query.get_or_404(task_id)
        
        # 权限校验
        if task.plan.user_id != user_id:
            return jsonify({'status': 'error', 'message': '无权限删除此任务'}), 403
        
        db.session.delete(task)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '任务删除成功'
        })
    except Exception as e:
        db.session.rollback()
        print(f"Delete Task Error: {e}")
        return jsonify({'status': 'error', 'message': '删除任务失败，请稍后重试'}), 500