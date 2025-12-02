from app import create_app

# 创建应用实例
app = create_app()

# 👇 这一段非常关键！必须要有！
if __name__ == '__main__':
    print("正在启动 Health Assistant...")  # 加这句方便调试
    app.run(debug=True)