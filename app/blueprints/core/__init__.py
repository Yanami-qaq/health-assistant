# app/blueprints/core/__init__.py

# 1. 从 main.py 导入 bp，并重命名为 main_bp (为了和外部引用保持一致)
from .main import bp as main_bp

# 2. 从 api.py 导入 api_bp
from .api import api_bp