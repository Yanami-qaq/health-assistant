# migrate_tasks.py
from app import create_app, db
from app.models import HealthPlan, PlanTask
import json

app = create_app()


def migrate():
    with app.app_context():
        print("🚀 开始迁移数据...")

        # 1. 查询所有计划
        plans = HealthPlan.query.all()
        count = 0

        for plan in plans:
            # 如果该计划已经在新表里有任务了，跳过（防止重复迁移）
            if plan.tasks:
                continue

            # 2. 读取旧的 JSON 数据
            if not plan.tasks_json:
                continue

            try:
                tasks_data = json.loads(plan.tasks_json)

                # 3. 遍历 JSON，插入到新表
                if isinstance(tasks_data, list):
                    for task_dict in tasks_data:
                        # 兼容处理：有时候存的是字符串，有时候是字典
                        title = ""
                        is_done = False

                        if isinstance(task_dict, dict):
                            title = task_dict.get('title', '未命名任务')
                            is_done = task_dict.get('done', False)
                        elif isinstance(task_dict, str):
                            title = task_dict
                            is_done = False

                        if title:
                            new_task = PlanTask(
                                plan_id=plan.id,
                                title=title,
                                is_done=is_done,
                                created_at=plan.created_at  # 使用计划的时间
                            )
                            db.session.add(new_task)
                            count += 1
            except Exception as e:
                print(f"❌ 计划 ID {plan.id} 解析失败: {e}")

        # 4. 提交更改
        db.session.commit()
        print(f"✅ 迁移完成！共迁移了 {count} 个任务。")
        print("现在你可以删除此脚本，并重启 Flask 应用了。")


if __name__ == '__main__':
    migrate()