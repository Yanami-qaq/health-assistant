# app/services/plan_service.py
from app.models import User, HealthRecord, HealthPlan
from app.extensions import db
from app.services.ai_service import call_deepseek_advisor
from datetime import datetime
import json


class PlanService:
    @staticmethod
    def generate_health_plan(user_id, user_message, save_as_plan=False):
        """
        处理用户消息，调用 AI，并在需要时保存为计划
        """
        user = User.query.get(user_id)
        last_record = HealthRecord.query.filter_by(user_id=user.id) \
            .order_by(HealthRecord.date.desc()).first()

        # 1. 构建用户画像 (Profile)
        profile_text = PlanService._build_profile_text(user, last_record)

        # 2. 构建 Prompt
        system_prompt = f"""
        你是一位资深的私人健康管理专家。用户【{user.nickname}】正在咨询。
        【用户全维档案】
        {profile_text}

        【输出格式要求】
        1. 语气亲切、专业。
        2. 如果包含计划，请在回答最后，以 `---TASKS---` 分割线列出 3-5 个纯文本任务。
        """

        # 3. 调用 AI 接口
        # 注意：这里可能会阻塞，生产环境建议放入 Celery 任务队列
        ai_response = call_deepseek_advisor(system_prompt, user_message)

        # 4. 解析结果
        content_part, tasks_list = PlanService._parse_ai_response(ai_response)

        # 5. 保存逻辑
        updated_plan = False
        if tasks_list or save_as_plan:
            new_plan = HealthPlan(
                user_id=user.id,
                goal="AI 深度定制计划",
                content=content_part,
                tasks_json=json.dumps(tasks_list, ensure_ascii=False)
            )
            db.session.add(new_plan)
            db.session.commit()
            updated_plan = True

        return {
            "reply": content_part,
            "updated_plan": updated_plan
        }

    @staticmethod
    def _build_profile_text(user, record):
        """辅助方法：构建 Prompt 用的档案文本"""
        if not record:
            return "暂无详细体征数据"

        # 这里放置原本 plan.py 里复杂的字符串拼接逻辑
        h_m = (user.height / 100) if user.height else 1.75
        bmi = round(record.weight / (h_m ** 2), 1) if record.weight else "未知"

        return f"""
        1. 基础: {user.gender or '未知'}, BMI: {bmi}
        2. 体重: {record.weight}kg, 体脂: {record.body_fat or '未知'}%
        3. 状态: 步数 {record.steps or 0}, 血糖 {record.blood_glucose or '未知'}
        4. 病史: {user.medical_history or '无'}
        """

    @staticmethod
    def _parse_ai_response(full_text):
        """辅助方法：解析 ---TASKS--- 分割线"""
        content = full_text
        tasks = []

        if "---TASKS---" in full_text:
            parts = full_text.split("---TASKS---")
            content = parts[0].strip()
            raw_tasks = parts[1].strip().split('\n')
            for t in raw_tasks:
                clean_t = t.strip().replace('- ', '').replace('1. ', '')
                if clean_t:
                    tasks.append({"title": clean_t, "done": False})

        return content, tasks