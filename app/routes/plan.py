from flask import Blueprint, render_template, request, jsonify, session
from app.models import User, HealthRecord, HealthPlan
from app.services.ai_service import call_deepseek_advisor
from app.decorators import login_required
from app.extensions import db
from datetime import datetime
import json

bp = Blueprint('plan', __name__)


@bp.route('/plan', methods=['GET'])
@login_required
def index():
    user_id = session['user_id']
    latest_plan = HealthPlan.query.filter_by(user_id=user_id).order_by(HealthPlan.created_at.desc()).first()
    return render_template('plan.html', nickname=session.get('nickname'), latest_plan=latest_plan)


@bp.route('/plan/chat', methods=['POST'])
@login_required
def chat():
    user_input = request.json.get('message')
    save_as_plan = request.json.get('save', False) or ("计划" in user_input)

    if not user_input: return jsonify({'status': 'error', 'message': '内容不能为空'})

    user = User.query.get(session['user_id'])
    # 获取最新的一条健康记录
    last_record = HealthRecord.query.filter_by(user_id=user.id).order_by(HealthRecord.date.desc()).first()

    # === 🔥 核心升级：全维度的健康画像 ===
    profile = {
        "昵称": user.nickname,
        "性别": user.gender or "未知",
        "年龄": (datetime.now().year - user.birth_year) if user.birth_year else "未知",
        "身高": f"{user.height}cm" if user.height else "未知",

        # 基础数据
        "体重": f"{last_record.weight}kg" if (last_record and last_record.weight) else "未知",
        "BMI": "未知",
        "最近步数": f"{last_record.steps}步" if (last_record and last_record.steps) else "未知",

        # 进阶数据 (新增)
        "体脂率": f"{last_record.body_fat}%" if (last_record and last_record.body_fat) else "未知",
        "饮水量": f"{last_record.water_intake}ml" if (last_record and last_record.water_intake) else "未知",
        "空腹血糖": f"{last_record.blood_glucose}mmol/L" if (last_record and last_record.blood_glucose) else "未知",

        # 备注
        "病史": user.medical_history or "无"
    }

    # 计算 BMI
    if user.height and last_record and last_record.weight:
        h_m = user.height / 100
        profile['BMI'] = round(last_record.weight / (h_m * h_m), 1)

    # === 🔥 升级提示词：让 AI 像医生一样思考 ===
    system_prompt = f"""
    你是一位资深的私人健康管理专家。用户【{profile['昵称']}】正在咨询。

    【用户全维档案】
    1. 基础信息: {profile['性别']}, {profile['年龄']}岁, BMI: {profile['BMI']}
    2. 身体成分: 体重 {profile['体重']}, 体脂率 {profile['体脂率']}
    3. 代谢指标: 空腹血糖 {profile['空腹血糖']}, 日常饮水 {profile['饮水量']}
    4. 运动状态: 最近单日步数 {profile['最近步数']}
    5. 风险禁忌: {profile['病史']}

    【深度分析逻辑】
    1. **必须结合数据**：
       - 如果血糖 > 6.1 mmol/L，必须在建议中强调“低GI饮食”和“控糖”。
       - 如果体脂率高（男>25%, 女>30%），重点放在“减脂”而非单纯减重。
       - 如果饮水 < 1500ml，必须提醒补水对代谢的重要性。
    2. **目标导向**：根据用户的问题意图，结合上述数据给出个性化方案。

    【输出格式要求】
    1. 语气亲切、专业、有条理（使用 Markdown）。
    2. 如果用户的意图是“制定计划”或“如何做”，请在回答的**最后**，生成一个【每日打卡清单】。
    3. 清单格式：
       - 必须以 `---TASKS---` 单独一行作为分割线。
       - 分割线下方列出 3-5 个具体的、该用户每天能做的小任务。
       - 任务要纯文本，不要加 Markdown 符号。

    示例输出：
    (针对血糖和体脂的深度分析...)
    ### 饮食建议
    ...
    ### 运动建议
    ...

    ---TASKS---
    早餐把白粥换成燕麦牛奶
    午餐后散步15分钟
    喝够2000ml温水
    23点前放下手机睡觉
    """

    try:
        full_response = call_deepseek_advisor(system_prompt, user_input)

        # 解析任务
        content_part = full_response
        tasks_list = []

        if "---TASKS---" in full_response:
            parts = full_response.split("---TASKS---")
            content_part = parts[0].strip()
            raw_tasks = parts[1].strip().split('\n')
            for t in raw_tasks:
                t = t.strip().replace('- ', '').replace('1. ', '')
                if t: tasks_list.append({"title": t, "done": False})

        if tasks_list or save_as_plan:
            new_plan = HealthPlan(
                user_id=user.id,
                goal="AI 深度定制计划",
                content=content_part,
                tasks_json=json.dumps(tasks_list, ensure_ascii=False)
            )
            db.session.add(new_plan)
            db.session.commit()
            return jsonify({'status': 'success', 'reply': content_part, 'updated_plan': True})

        return jsonify({'status': 'success', 'reply': content_part})

    except Exception as e:
        print(f"AI Error: {e}")
        return jsonify({'status': 'error', 'reply': 'AI 暂时掉线了，请重试。'})


# Toggle 接口保持不变，为了完整性我这里省略了，之前的不用删
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