from flask import Blueprint, jsonify, session, request
# ✅ 确保这一行是精确导入
from app.blueprints.health.service import RecordService

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