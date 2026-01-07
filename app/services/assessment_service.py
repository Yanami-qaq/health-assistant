# app/services/assessment_service.py
from app.models import User, HealthRecord, HealthAssessment
from app.services.ai_service import call_deepseek_advisor
from app.extensions import db
from datetime import datetime
import json
import re

class AssessmentService:
    @staticmethod
    def generate_health_assessment(user_id):
        """
        生成健康状态评估报告
        返回: {
            "health_score": 85,
            "assessments": {...},
            "suggestions": [...],
            "status": "success" or "error"
        }
        """
        user = User.query.get(user_id)
        if not user:
            return {"status": "error", "message": "用户不存在"}
        
        # 获取最新健康记录
        last_record = HealthRecord.query.filter_by(user_id=user_id) \
            .order_by(HealthRecord.date.desc()).first()
        
        # 检查数据完整性
        if not last_record:
            return {
                "status": "incomplete",
                "message": "健康数据不完整，请先记录或同步健康数据",
                "health_score": 0
            }
        
        # 检查必要数据
        missing_fields = []
        if not user.height:
            missing_fields.append("身高")
        if not last_record.weight:
            missing_fields.append("体重")
        
        if missing_fields:
            return {
                "status": "incomplete",
                "message": f"健康数据不完整，请补充：{', '.join(missing_fields)}",
                "health_score": 0,
                "missing_fields": missing_fields
            }
        
        # 检查数据有效性（异常事件流3：数据来源异常）
        data_errors = AssessmentService._validate_data_quality(user, last_record)
        if data_errors:
            return {
                "status": "data_error",
                "message": "数据异常，请检查健康数据来源",
                "health_score": 0,
                "errors": data_errors,
                "suggestion": "建议重新连接健康应用或设备，或手动检查数据"
            }
        
        # 构建用户健康档案
        profile_text = AssessmentService._build_health_profile(user, last_record)
        
        # 构建AI提示词
        system_prompt = f"""
你是一位资深的健康评估专家。请根据用户的健康数据，进行全面的健康状态评估。

【用户健康档案】
{profile_text}

【评估要求】
1. 计算综合健康分数（0-100分），考虑以下维度：
   - 身体成分（BMI、体脂率）：30%
   - 运动能力（步数、卡路里）：25%
   - 心血管健康（心率、血压）：20%
   - 代谢健康（血糖）：15%
   - 生活习惯（睡眠、饮水）：10%

2. 对各项指标进行评估，给出等级（优秀/良好/需改善/异常）
   - 评估时必须充分考虑用户的既往病史和健康备注
   - 如果用户有特定疾病或健康问题，需要在相关指标的comment中提及，并给出相应的注意事项

3. 提供3-5条针对性的健康改善建议
   - 建议必须结合用户的既往病史和健康备注
   - 如果用户有特定疾病（如高血压、糖尿病、过敏等），建议必须避开相关风险，并针对性地提供安全可行的改善方案
   - 如果用户有运动限制或饮食禁忌，建议必须严格遵守这些限制

4. 在评估总结中，如果用户有既往病史，需要特别说明如何结合病史进行健康管理

【输出格式要求】
请务必返回严格的 JSON 格式，不要包含 ```json 代码块标记。格式如下：
{{
    "health_score": 85,
    "assessments": {{
        "bmi": {{"value": 22.5, "level": "良好", "comment": "BMI在正常范围内"}},
        "body_fat": {{"value": 20.5, "level": "良好", "comment": "体脂率适中"}},
        "steps": {{"value": 8500, "level": "需改善", "comment": "建议增加日常活动量"}},
        "heart_rate": {{"value": 72, "level": "优秀", "comment": "静息心率正常"}},
        "blood_pressure": {{"value": "120/80", "level": "良好", "comment": "血压正常"}},
        "blood_glucose": {{"value": 5.2, "level": "良好", "comment": "血糖正常"}},
        "sleep": {{"value": 7.5, "level": "良好", "comment": "睡眠时长充足"}},
        "water": {{"value": 1500, "level": "需改善", "comment": "建议增加饮水量"}}
    }},
    "suggestions": [
        "建议每天增加2000ml饮水量，少量多次饮用",
        "建议每天步数达到10000步，保持身体活力",
        "保持规律作息，确保7-9小时充足睡眠"
    ],
    "summary": "您的整体健康状况良好，建议继续保持规律运动，并注意增加饮水量。"
}}
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请对我的健康状况进行全面评估，并给出改善建议。"}
        ]
        
        # 调用AI服务
        ai_response_text = call_deepseek_advisor(messages)
        if not ai_response_text:
            return {
                "status": "error",
                "message": "健康评估失败，请稍后重试",
                "health_score": 0
            }
        
        # 解析AI响应
        assessment_data = AssessmentService._parse_ai_response(ai_response_text)
        if not assessment_data:
            return {
                "status": "error",
                "message": "健康评估失败，请稍后重试",
                "health_score": 0
            }
        
        assessment_data["status"] = "success"
        
        # 保存评估结果到数据库
        AssessmentService._save_assessment_to_db(user_id, assessment_data)
        
        return assessment_data
    
    @staticmethod
    def _save_assessment_to_db(user_id, assessment_data):
        """保存评估结果到数据库"""
        try:
            # 查找用户是否已有评估记录
            existing_assessment = HealthAssessment.query.filter_by(user_id=user_id).first()
            
            if existing_assessment:
                # 更新现有记录
                existing_assessment.health_score = assessment_data.get('health_score', 0)
                existing_assessment.assessments = json.dumps(assessment_data.get('assessments', {}), ensure_ascii=False)
                existing_assessment.suggestions = json.dumps(assessment_data.get('suggestions', []), ensure_ascii=False)
                existing_assessment.summary = assessment_data.get('summary', '')
                existing_assessment.updated_at = datetime.utcnow()
            else:
                # 创建新记录
                new_assessment = HealthAssessment(
                    user_id=user_id,
                    health_score=assessment_data.get('health_score', 0),
                    assessments=json.dumps(assessment_data.get('assessments', {}), ensure_ascii=False),
                    suggestions=json.dumps(assessment_data.get('suggestions', []), ensure_ascii=False),
                    summary=assessment_data.get('summary', '')
                )
                db.session.add(new_assessment)
            
            db.session.commit()
        except Exception as e:
            print(f"Save Assessment Error: {e}")
            db.session.rollback()
            # 保存失败不影响评估结果的返回
    
    @staticmethod
    def get_latest_assessment(user_id):
        """获取用户最新的评估结果"""
        try:
            assessment = HealthAssessment.query.filter_by(user_id=user_id).first()
            if assessment:
                return assessment.to_dict()
            return None
        except Exception as e:
            print(f"Get Assessment Error: {e}")
            return None
    
    @staticmethod
    def _build_health_profile(user, record):
        """构建用户健康档案文本"""
        h_m = (user.height / 100) if user.height else None
        bmi = None
        if h_m and record.weight:
            bmi = round(record.weight / (h_m ** 2), 1)
        
        profile = f"""
基本信息：
- 性别：{user.gender or '未填写'}
- 年龄：{datetime.now().year - user.birth_year if user.birth_year else '未知'}岁
- 身高：{user.height or '未填写'} cm
- 体重：{record.weight or '未填写'} kg
- BMI：{bmi or '无法计算'}

身体成分：
- 体脂率：{record.body_fat or '未测量'} %

运动数据：
- 步数：{record.steps or 0} 步
- 卡路里消耗：{record.calories or 0} kcal

心血管指标：
- 静息心率：{record.heart_rate or '未测量'} bpm
- 血压：{record.blood_pressure_high or '--'}/{record.blood_pressure_low or '--'} mmHg

代谢指标：
- 血糖：{record.blood_glucose or '未测量'} mmol/L

生活习惯：
- 睡眠时长：{record.sleep_hours or '未记录'} 小时
- 饮水量：{record.water_intake or 0} ml

病史：{user.medical_history or '无'}
"""
        return profile
    
    @staticmethod
    def _parse_ai_response(full_text):
        """解析AI返回的JSON响应"""
        try:
            # 尝试直接解析
            data = json.loads(full_text)
        except json.JSONDecodeError:
            # 清理可能的代码块标记
            clean_text = re.sub(r'^```json\s*|\s*```$', '', full_text, flags=re.MULTILINE | re.DOTALL).strip()
            try:
                data = json.loads(clean_text)
            except json.JSONDecodeError:
                # 如果还是失败，尝试提取JSON部分
                json_match = re.search(r'\{.*\}', clean_text, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                    except:
                        return None
                else:
                    return None
        
        # 验证必要字段
        if "health_score" not in data:
            return None
        
        return data
    
    @staticmethod
    def _validate_data_quality(user, record):
        """
        验证数据有效性
        返回: 错误列表，如果为空则表示数据正常
        """
        errors = []
        
        # 验证步数 (0-100000)
        if record.steps is not None:
            if record.steps < 0 or record.steps > 100000:
                errors.append(f"步数数据异常：{record.steps}（正常范围：0-100000）")
        
        # 验证卡路里 (0-10000)
        if record.calories is not None:
            if record.calories < 0 or record.calories > 10000:
                errors.append(f"卡路里数据异常：{record.calories}（正常范围：0-10000）")
        
        # 验证心率 (30-250 bpm)
        if record.heart_rate is not None:
            if record.heart_rate < 30 or record.heart_rate > 250:
                errors.append(f"心率数据异常：{record.heart_rate} bpm（正常范围：30-250）")
        
        # 验证血压
        if record.blood_pressure_high is not None:
            if record.blood_pressure_high < 60 or record.blood_pressure_high > 250:
                errors.append(f"血压高压异常：{record.blood_pressure_high} mmHg（正常范围：60-250）")
        
        if record.blood_pressure_low is not None:
            if record.blood_pressure_low < 40 or record.blood_pressure_low > 150:
                errors.append(f"血压低压异常：{record.blood_pressure_low} mmHg（正常范围：40-150）")
        
        # 验证血压逻辑关系
        if record.blood_pressure_high is not None and record.blood_pressure_low is not None:
            if record.blood_pressure_high <= record.blood_pressure_low:
                errors.append(f"血压数据异常：高压({record.blood_pressure_high})必须大于低压({record.blood_pressure_low})")
        
        # 验证体重 (20-300 kg)
        if record.weight is not None:
            if record.weight < 20 or record.weight > 300:
                errors.append(f"体重数据异常：{record.weight} kg（正常范围：20-300）")
        
        # 验证体脂率 (3-60%)
        if record.body_fat is not None:
            if record.body_fat < 3 or record.body_fat > 60:
                errors.append(f"体脂率数据异常：{record.body_fat}%（正常范围：3-60）")
        
        # 验证血糖 (2-30 mmol/L)
        if record.blood_glucose is not None:
            if record.blood_glucose < 2 or record.blood_glucose > 30:
                errors.append(f"血糖数据异常：{record.blood_glucose} mmol/L（正常范围：2-30）")
        
        # 验证睡眠 (0-24 小时)
        if record.sleep_hours is not None:
            if record.sleep_hours < 0 or record.sleep_hours > 24:
                errors.append(f"睡眠时长异常：{record.sleep_hours} 小时（正常范围：0-24）")
        
        # 验证饮水量 (0-10000 ml)
        if record.water_intake is not None:
            if record.water_intake < 0 or record.water_intake > 10000:
                errors.append(f"饮水量异常：{record.water_intake} ml（正常范围：0-10000）")
        
        return errors

