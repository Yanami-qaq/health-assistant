from flask import Blueprint, jsonify, session, request
import csv
import io
from datetime import datetime

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/upload_data', methods=['POST'])
def upload_data():
    if 'user_id' not in session: return jsonify({'status': 'error', 'message': '请先登录'}), 401
    if 'file' not in request.files: return jsonify({'status': 'error', 'message': '未找到文件'}), 400

    file = request.files['file']
    if file.filename == '': return jsonify({'status': 'error', 'message': '未选择文件'}), 400

    try:
        bytes_content = file.stream.read()
        if not bytes_content: return jsonify({'status': 'error', 'message': '文件内容为空'}), 400

        if bytes_content.startswith(b'PK\x03\x04'):
            return jsonify({'status': 'error', 'message': '❌ 格式错误：请上传 CSV 文件'})

        text_content = None
        encodings = ['utf-8-sig', 'gbk', 'gb18030', 'big5']
        for enc in encodings:
            try:
                text_content = bytes_content.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if text_content is None: return jsonify(
            {'status': 'error', 'message': '❌ 文件编码无法识别，请另存为 CSV UTF-8'}), 400

        stream = io.StringIO(text_content, newline=None)
        reader = csv.DictReader(stream)

        if reader.fieldnames:
            reader.fieldnames = [name.strip() for name in reader.fieldnames]

        rows = list(reader)
        if not rows: return jsonify({'status': 'error', 'message': '没有数据行'}), 400

        target_row = rows[0]

        # === 🔥 更新字段映射 ===
        field_map = {
            '日期': 'date',
            '体重(kg)': 'weight',
            '体脂率(%)': 'body_fat',  # 新增
            '步数': 'steps',
            '饮水量(ml)': 'water_intake',  # 新增
            '卡路里': 'calories',
            '睡眠(h)': 'sleep_hours',
            '血糖(mmol/L)': 'blood_glucose',  # 新增
            '心率(bpm)': 'heart_rate',
            '高压': 'bp_high',
            '低压': 'bp_low',
            '备注': 'note'
        }

        data = {}
        for csv_key, db_key in field_map.items():
            val = target_row.get(csv_key, '').strip()
            data[db_key] = val

        return jsonify({'status': 'success', 'data': data, 'message': '✅ 成功导入'})

    except Exception as e:
        print(f"System Error: {e}")
        return jsonify({'status': 'error', 'message': f'系统错误: {str(e)}'}), 500


@bp.route('/simulate_import', methods=['GET'])
def simulate_import():
    return jsonify({'status': 'error', 'message': '请使用文件导入功能'})