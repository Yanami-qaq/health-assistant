# app/services/ai_service.py
from openai import OpenAI
from flask import current_app

def call_deepseek_advisor(system_prompt, user_prompt):
    """
    封装 DeepSeek API 底层调用逻辑
    """
    try:
        # 从配置读取 Key
        client = OpenAI(
            api_key=current_app.config['DEEPSEEK_API_KEY'],
            base_url=current_app.config['DEEPSEEK_BASE_URL']
        )

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content

    except Exception as e:
        # 建议换成 logger.error
        print(f"❌ AI Service Error: {e}")
        return f"连接 AI 失败，请检查网络或配置。\n错误信息: {e}"