# app/services/stats_service.py
from app.models import User, HealthRecord, HealthPlan
from datetime import datetime


class StatsService:
    @staticmethod
    def get_dashboard_data(user_id):
        """获取仪表盘所需的所有统计数据"""
        user = User.query.get(user_id)

        # 1. 获取最近 14 天记录
        recent_records = HealthRecord.query.filter_by(user_id=user_id) \
            .order_by(HealthRecord.date.desc()).limit(14).all()
        # 数据库查出来是倒序，转成正序给图表用
        records = recent_records[::-1]

        # 2. 提取图表数据
        chart_data = {
            "dates": [r.date.strftime('%m-%d') for r in records],
            "weights": [r.weight for r in records],
            "steps": [r.steps for r in records],
            # 处理 None 值，防止前端 Chart.js 报错
            "sleep_hours": [r.sleep_hours if r.sleep_hours else None for r in records],
            "heart_rates": [r.heart_rate if r.heart_rate else None for r in records],
            "body_fats": [r.body_fat if r.body_fat else None for r in records],
            "water_intakes": [r.water_intake if r.water_intake else None for r in records],
            "blood_glucoses": [r.blood_glucose if r.blood_glucose else None for r in records],
        }

        # 3. 最新计划
        latest_plan = HealthPlan.query.filter_by(user_id=user_id) \
            .order_by(HealthPlan.created_at.desc()).first()

        # 4. 计算活力值 & 连签
        today_score = StatsService._calculate_vitality_score(user, records)
        streak_days = StatsService._calculate_streak(user_id)  # 也可以传 records 进去算

        # 5. 热力图数据 (获取所有记录)
        heatmap_data = []
        all_records = HealthRecord.query.filter_by(user_id=user_id).all()
        for r in all_records:
            if r.steps:
                heatmap_data.append([r.date.strftime('%Y-%m-%d'), r.steps])

        return {
            "user": user,
            "chart_data": chart_data,
            "latest_plan": latest_plan,
            "today_score": today_score,
            "streak_days": streak_days,
            "heatmap_data": heatmap_data
        }

    @staticmethod
    def _calculate_vitality_score(user, records):
        """内部算法：计算今日活力值"""
        if not records: return 0
        last_rec = records[-1]  # 最近的一条

        # 运动分
        step_val = last_rec.steps or 0
        score_move = min((step_val / 10000) * 100, 100)

        # 睡眠分
        sleep_val = last_rec.sleep_hours or 0
        if 7 <= sleep_val <= 9:
            score_sleep = 100
        elif 6 <= sleep_val < 7 or 9 < sleep_val <= 10:
            score_sleep = 80
        else:
            score_sleep = 60

        # BMI 分
        score_body = 80
        if user.height and last_rec.weight:
            h_m = user.height / 100
            bmi = last_rec.weight / (h_m * h_m)
            if 18.5 <= bmi <= 24:
                score_body = 100
            elif 24 < bmi <= 28 or 17 <= bmi < 18.5:
                score_body = 80
            else:
                score_body = 60

        # 饮水加分
        water_val = last_rec.water_intake or 0
        bonus = 5 if water_val >= 2000 else 0

        return min(int(score_move * 0.5 + score_sleep * 0.3 + score_body * 0.2) + bonus, 100)

    @staticmethod
    def _calculate_streak(user_id):
        """内部算法：计算连续打卡天数"""
        # 注意：这里需要按日期倒序查所有记录，逻辑需要严谨
        records = HealthRecord.query.filter_by(user_id=user_id).order_by(HealthRecord.date.desc()).all()
        if not records: return 0

        streak = 0
        # 简单算法：检查最近一条是否是今天或昨天
        # (实际生产中建议用 SQL 窗口函数，这里维持 Python 逻辑)
        today = datetime.now().date()
        last_date = records[0].date

        if (today - last_date).days > 1:
            return 0  # 断签了

        streak = 1
        prev = last_date
        for r in records[1:]:
            diff = (prev - r.date).days
            if diff == 1:
                streak += 1
                prev = r.date
            elif diff == 0:
                continue  # 同一天多条记录，跳过
            else:
                break
        return streak