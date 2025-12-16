# app/services/ai_service.py
from openai import OpenAI
from flask import current_app
import logging

# 配置 Logger
logger = logging.getLogger(__name__)

def call_deepseek_advisor(messages):
    """
    封装 DeepSeek API 底层调用逻辑
    :param messages: List[Dict], e.g. [{"role": "system", "content": "..."}, ...]
    """
    try:
        client = OpenAI(
            api_key=current_app.config['DEEPSEEK_API_KEY'],
            base_url=current_app.config['DEEPSEEK_BASE_URL']
        )

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,  # 🔥 核心修改：直接透传消息列表
            temperature=0.7,
            response_format={'type': 'json_object'} # 🔥 新增：如果模型支持，强制 JSON 模式（可选，DeepSeek 目前主要靠 Prompt 约束）
        )
        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"AI Service Error: {e}", exc_info=True)
        return None  # 返回 None 让上层处理错误，而不是返回一段文本