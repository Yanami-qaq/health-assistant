import csv
import io


class RecordService:
    @staticmethod
    def parse_csv(file_stream):
        """
        解析上传的 CSV 文件流
        返回: {'status': 'success/error', 'data': ...}
        """
        try:
            bytes_content = file_stream.read()
            if not bytes_content:
                return {'status': 'error', 'message': '文件内容为空'}

            # 简单的防错检查
            if bytes_content.startswith(b'PK\x03\x04'):
                return {'status': 'error', 'message': '❌ 格式错误：请上传 CSV 文件'}

            text_content = None
            # 尝试不同的编码格式解码
            encodings = ['utf-8-sig', 'gbk', 'gb18030', 'big5']
            for enc in encodings:
                try:
                    text_content = bytes_content.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue

            if text_content is None:
                return {'status': 'error', 'message': '❌ 文件编码无法识别，请另存为 CSV UTF-8'}

            stream = io.StringIO(text_content, newline=None)
            reader = csv.DictReader(stream)

            if reader.fieldnames:
                # 去除表头可能的空格
                reader.fieldnames = [name.strip() for name in reader.fieldnames]

            rows = list(reader)
            if not rows:
                return {'status': 'error', 'message': '没有数据行'}

            # 取第一行数据作为回填示例
            target_row = rows[0]

            # 字段映射表：CSV中文名 -> 数据库字段名
            field_map = {
                '日期': 'date',
                '体重(kg)': 'weight',
                '体脂率(%)': 'body_fat',
                '步数': 'steps',
                '饮水量(ml)': 'water_intake',
                '卡路里': 'calories',
                '睡眠(h)': 'sleep_hours',
                '血糖(mmol/L)': 'blood_glucose',
                '心率(bpm)': 'heart_rate',
                '高压': 'bp_high',
                '低压': 'bp_low',
                '备注': 'note'
            }

            data = {}
            for csv_key, db_key in field_map.items():
                val = target_row.get(csv_key, '').strip()
                data[db_key] = val

            return {'status': 'success', 'data': data, 'message': '✅ 成功导入'}

        except Exception as e:
            return {'status': 'error', 'message': f'系统错误: {str(e)}'}