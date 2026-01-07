from flask import Blueprint, jsonify, session, request
from app.blueprints.health.service import RecordService
from app.extensions import db
from app.models import HealthRecord, User
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
    """模拟智能设备健康数据同步接口"""
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': '请先登录'}), 401

    try:
        data = request.json
        if not data:
            return jsonify({
                'status': 'error', 
                'message': '数据获取失败，请稍后再试'
            }), 400

        # 验证数据格式和范围
        errors = []
        
        # 验证步数
        if 'steps' in data:
            try:
                steps_val = int(data['steps'])
                if steps_val < 0 or steps_val > 100000:
                    errors.append('步数数据异常')
            except (ValueError, TypeError):
                errors.append('步数格式错误')
        
        # 体重不需要验证，因为会直接从数据库的user表读取
        
        # 验证体脂率
        if 'body_fat' in data:
            try:
                bf_val = float(data['body_fat'])
                if bf_val < 3 or bf_val > 60:
                    errors.append('体脂率数据异常')
            except (ValueError, TypeError):
                errors.append('体脂率格式错误')
        
        # 验证血糖
        if 'blood_glucose' in data:
            try:
                bg_val = float(data['blood_glucose'])
                if bg_val < 2 or bg_val > 30:
                    errors.append('血糖数据异常')
            except (ValueError, TypeError):
                errors.append('血糖格式错误')
        
        # 验证卡路里
        if 'calories' in data:
            try:
                cal_val = int(data['calories'])
                if cal_val < 0 or cal_val > 10000:
                    errors.append('卡路里数据异常')
            except (ValueError, TypeError):
                errors.append('卡路里格式错误')
        
        # 验证睡眠
        if 'sleep' in data:
            try:
                sleep_val = float(data['sleep'])
                if sleep_val < 0 or sleep_val > 24:
                    errors.append('睡眠时长数据异常')
            except (ValueError, TypeError):
                errors.append('睡眠时长格式错误')
        
        # 验证心率
        if 'heart_rate' in data:
            try:
                hr_val = int(data['heart_rate'])
                if hr_val < 30 or hr_val > 250:
                    errors.append('心率数据异常')
            except (ValueError, TypeError):
                errors.append('心率格式错误')
        
        # 验证血压高压
        if 'blood_pressure_high' in data:
            try:
                bp_high = int(data['blood_pressure_high'])
                if bp_high < 60 or bp_high > 250:
                    errors.append('高压数据异常')
            except (ValueError, TypeError):
                errors.append('高压格式错误')
        
        # 验证血压低压
        if 'blood_pressure_low' in data:
            try:
                bp_low = int(data['blood_pressure_low'])
                if bp_low < 40 or bp_low > 150:
                    errors.append('低压数据异常')
            except (ValueError, TypeError):
                errors.append('低压格式错误')
        
        # 验证血压逻辑关系
        if 'blood_pressure_high' in data and 'blood_pressure_low' in data:
            try:
                if int(data['blood_pressure_high']) <= int(data['blood_pressure_low']):
                    errors.append('血压数据异常：高压必须大于低压')
            except (ValueError, TypeError):
                pass  # 已经在上面报错了
        
        # 如果有验证错误，返回异常提示
        if errors:
            return jsonify({
                'status': 'error',
                'message': '获取的数据异常，请检查设备或稍后重试',
                'details': errors
            }), 400

        # 获取用户信息，检查是否设置了体重
        user = User.query.get(session['user_id'])
        if not user or not user.weight:
            return jsonify({
                'status': 'error',
                'message': '无法获取健康数据，请检查设置',
                'details': '请在账户设置页面设置您的体重'
            }), 400

        # 获取今日日期
        today = datetime.now().date()

        # 查找今天是否已经有记录
        record = HealthRecord.query.filter_by(
            user_id=session['user_id'],
            date=today
        ).first()

        # 如果今天还没记录，就创建一个新的
        if not record:
            record = HealthRecord(user_id=session['user_id'], date=today)
            db.session.add(record)

        # 更新数据（模拟从智能设备同步）
        # 注意：智能设备可以同步步数、卡路里、睡眠、心率、血压、体脂、血糖
        # 体重直接从数据库的user表读取，不从前端模拟数据中获取
        if 'steps' in data:
            record.steps = int(data['steps'])
        if 'calories' in data:
            record.calories = int(data['calories'])
        if 'sleep' in data:
            record.sleep_hours = float(data['sleep'])
        if 'heart_rate' in data:
            record.heart_rate = int(data['heart_rate'])
        if 'blood_pressure_high' in data:
            record.blood_pressure_high = int(data['blood_pressure_high'])
        if 'blood_pressure_low' in data:
            record.blood_pressure_low = int(data['blood_pressure_low'])
        # 体重直接从用户设置中读取，不从前端模拟数据中获取
        record.weight = user.weight
        if 'body_fat' in data:
            record.body_fat = float(data['body_fat'])
        if 'blood_glucose' in data:
            record.blood_glucose = float(data['blood_glucose'])

        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '智能设备数据同步成功',
            'data': {
                'date': str(today),
                'weight': record.weight,
                'body_fat': record.body_fat,
                'blood_glucose': record.blood_glucose,
                'steps': record.steps,
                'calories': record.calories,
                'sleep': record.sleep_hours,
                'heart_rate': record.heart_rate,
                'blood_pressure_high': record.blood_pressure_high,
                'blood_pressure_low': record.blood_pressure_low
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': '无法获取数据，请检查网络连接'
        }), 500