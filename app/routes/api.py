from flask import Blueprint, jsonify, session
import random
from datetime import datetime

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/simulate_import', methods=['GET'])
def simulate_import():
    # 检查登录
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': '用户未登录'}), 401

    try:
        current_time = datetime.now().strftime('%H:%M')
        simulated_data = {
            'weight': round(random.uniform(55.0, 85.0), 1),
            'steps': random.randint(3000, 15000),
            'calories': random.randint(200, 800),
            'sleep_hours': round(random.uniform(5.5, 9.0), 1),
            'heart_rate': random.randint(60, 100),
            'bp_high': random.randint(110, 140),
            'bp_low': random.randint(70, 90),
            'note': f"数据来源：智能手表同步于 {current_time}"
        }
        return jsonify({'status': 'success', 'data': simulated_data, 'message': '同步成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500