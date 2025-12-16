from app.models import User, HealthRecord, HealthPlan, PlanTask # 引入新模型
from app.extensions import db
from app.services.ai_service import call_deepseek_advisor
from datetime import datetime
import json
import re

class PlanService:
    @staticmethod
    def generate_health_plan(user_id, user_message, history=None, save_as_plan=False):
        user = User.query.get(user_id)
        last_record = HealthRecord.query.filter_by(user_id=user.id) \
            .order_by(HealthRecord.date.desc()).first()

        # 1. 构建画像 (保持不变)
        profile_text = PlanService._build_profile_text(user, last_record)

        # 2. 构建 Prompt (保持不变)
        system_prompt = f"""
        你是一位资深的私人健康管理专家。用户【{user.nickname}】正在咨询。
        【用户全维档案】
        {profile_text}

        【输出格式要求】
        请务必返回严格的 JSON 格式，不要包含 ```json 代码块标记。格式如下：
        {{
            "reply": "这里写给用户的回复...",
            "tasks": [
                {{"title": "建议任务1", "done": false}},
                {{"title": "建议任务2", "done": false}}
            ]
        }}
        如果不需要生成具体任务，tasks 数组请留空。
        """

        # 3. 组装消息 (保持不变)
        messages = [{"role": "system", "content": system_prompt}]
        if history and isinstance(history, list):
            valid_history = [h for h in history[-6:] if h.get('role') in ['user', 'assistant']]
            messages.extend(valid_history)
        messages.append({"role": "user", "content": user_message})

        # 4. 调用 AI (保持不变)
        ai_response_text = call_deepseek_advisor(messages)
        if not ai_response_text:
            return {"reply": "服务繁忙，请稍后再试。", "updated_plan": False}

        # 5. 解析结果 (保持不变)
        content_part, tasks_list = PlanService._parse_ai_response(ai_response_text)

        # 6. 保存逻辑 (🔥 重大修改：关系型存储)
        updated_plan = False
        if (tasks_list and len(tasks_list) > 0) or save_as_plan:
            # 6.1 先创建主计划
            new_plan = HealthPlan(
                user_id=user.id,
                goal="AI 深度定制计划",
                content=content_part
                # tasks_json 留空或存个备份均可
            )
            db.session.add(new_plan)
            # 6.2 Flush 以获取 new_plan.id (此时还没提交事务)
            db.session.flush()

            # 6.3 循环创建子任务
            for t_data in tasks_list:
                # 确保解析出的 title 存在
                title = t_data.get('title') if isinstance(t_data, dict) else str(t_data)
                if title:
                    new_task = PlanTask(
                        plan_id=new_plan.id,
                        title=title,
                        is_done=False
                    )
                    db.session.add(new_task)

            # 6.4 统一提交
            db.session.commit()
            updated_plan = True

        return {
            "reply": content_part,
            "updated_plan": updated_plan
        }

    # ... _build_profile_text 和 _parse_ai_response 辅助方法保持不变 ...
    @staticmethod
    def _build_profile_text(user, record):
        if not record: return "暂无详细体征数据"
        h_m = (user.height / 100) if user.height else 1.75
        bmi = round(record.weight / (h_m ** 2), 1) if record.weight else "未知"
        return f"性别:{user.gender}, BMI:{bmi}, 体重:{record.weight}kg, 步数:{record.steps}, 病史:{user.medical_history}"

    @staticmethod
    def _parse_ai_response(full_text):
        try:
            data = json.loads(full_text)
        except json.JSONDecodeError:
            clean_text = re.sub(r'^```json\s*|\s*```$', '', full_text, flags=re.MULTILINE | re.DOTALL).strip()
            try:
                data = json.loads(clean_text)
            except json.JSONDecodeError:
                return full_text, []

        reply = data.get("reply", "无法解析回复内容")
        tasks = data.get("tasks", [])
        return reply, tasks