import pymysql
from sqlalchemy import create_engine, text  # <--- 1. 这里加了 text
from sqlalchemy.orm import sessionmaker
from app import create_app, db
from app.models import User, HealthRecord, HealthPlan, Post, PostLike, Comment

# === 配置旧的本地数据库连接 ===
# 这是您原来在 config.py 里的配置，用于读取旧数据
LOCAL_DB_URI = 'mysql+pymysql://root:324215@localhost/health_assistant'

def migrate():
    print("🚀 准备开始数据迁移...")
    
    # --- 步骤 A: 连接本地旧数据库 ---
    print("1. 正在连接本地旧数据库...")
    try:
        local_engine = create_engine(LOCAL_DB_URI)
        LocalSession = sessionmaker(bind=local_engine)
        local_session = LocalSession()
        # 2. 修复点：SQLAlchemy 2.0 必须用 text() 包裹 SQL 语句
        local_session.execute(text("SELECT 1")) 
    except Exception as e:
        print(f"❌ 本地数据库连接失败: {e}")
        print("请检查您的本地 MySQL 是否已启动。")
        return

    # --- 步骤 B: 连接云端新数据库 ---
    print("2. 正在连接云端新数据库...")
    app = create_app() # 这里会自动读取 config.py 连接云数据库

    # --- 步骤 C: 开始搬运数据 ---
    with app.app_context():
        # 定义搬运顺序 (重要！必须先搬用户，再搬帖子，否则会报错找不到主人)
        models = [
            (User, "用户表"),
            (Post, "社区帖子"),
            (HealthRecord, "健康记录"),
            (HealthPlan, "AI计划"),
            (Comment, "评论"),
            (PostLike, "点赞记录")
        ]

        for ModelClass, name in models:
            print(f"--- 正在处理: {name} ---")
            
            # 1. 从本地查出所有数据
            try:
                local_items = local_session.query(ModelClass).all()
            except Exception as e:
                print(f"   ⚠️  跳过 (本地可能没这张表): {e}")
                continue
            
            if not local_items:
                print("   (空表，无需迁移)")
                continue

            count = 0
            for item in local_items:
                # 2. “克隆”数据对象
                data = {c.name: getattr(item, c.name) for c in item.__table__.columns}
                new_item = ModelClass(**data)
                
                # 3. 放入云端数据库 (使用 merge 防止 ID 重复)
                db.session.merge(new_item)
                count += 1
            
            # 4. 提交保存
            try:
                db.session.commit()
                print(f"   ✅ 成功迁移 {count} 条数据！")
            except Exception as e:
                db.session.rollback()
                print(f"   ❌ 写入失败: {e}")

    print("\n🎉 恭喜！所有数据已成功从本地迁移到云端！")

if __name__ == '__main__':
    migrate()