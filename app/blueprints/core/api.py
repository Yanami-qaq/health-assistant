from flask import Blueprint, jsonify, session, request
from app.blueprints.health.service import RecordService
from app.extensions import db
from app.models import HealthRecord
from datetime import datetime

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/upload_data', methods=['POST'])
def upload_data():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': '请先登录'}), 401

    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': '未找到文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': '未选择文件'}), 400

    # 调用 Service
    result = RecordService.parse_csv(file.stream)

    if result['status'] == 'error':
        return jsonify(result), 400

    return jsonify(result)


@api_bp.route('/upload_health_data', methods=['POST'])
def upload_health_data():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': '请先登录'}), 401

    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': '没有接收到数据'}), 400

    # 获取今日日期
    today = datetime.now().date()

    # 查找今天是否已经有记录了？
    record = HealthRecord.query.filter_by(
        user_id=session['user_id'],
        date=today
    ).first()

    # 如果今天还没记录，就创建一个新的
    if not record:
        record = HealthRecord(user_id=session['user_id'], date=today)
        db.session.add(record)

    # 更新数据 (模拟从手表同步过来的数据)
    # 注意：这里我们只更新这三项，保留用户可能填写的其他项(比如备注)
    if 'steps' in data:
        record.steps = data['steps']
    if 'calories' in data:
        record.calories = data['calories']
    if 'sleep' in data:
        record.sleep_hours = data['sleep']

    try:
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': '✅ 智能设备数据同步成功！',
            'data': {
                'date': str(today),
                'steps': record.steps,
                'calories': record.calories,
                'sleep': record.sleep_hours
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500