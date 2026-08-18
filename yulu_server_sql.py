from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import sqlite3
import os
import sys
import logging
from datetime import datetime

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 允许所有跨域请求

# 删除/清空操作鉴权 token，从环境变量读取，默认回退到 yulu_server
DELETE_TOKEN = os.getenv('DELETE_TOKEN', 'yulu_server')

# 数据库文件路径
DB_FILE = os.getenv('DB_FILE', 'quotes.db')

def init_db():
    """初始化数据库"""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_client_id
            ON quotes(client_id)
        ''')
        conn.commit()
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()

@app.route('/quotes', methods=['GET', 'POST'])
def handle_quotes():
    """处理语录请求"""
    try:
        # 解析JSON数据
        if request.method == 'POST':
            request_data = request.get_json()
        else:
            # GET 请求可以从查询参数获取数据
            request_data = request.args.to_dict()

        # 从请求中获取类型和ID
        request_type = request_data.get('type')
        client_id = request_data.get('id', 'default')  # 提供默认id

        if request_type == "get":
            result, code = send_message(client_id)
            return jsonify(result), code
        elif request_type == "upload":
            message = request_data.get('message')
            result, code = save_message(client_id, message)
            return jsonify(result), code
        elif request_type == "delete":
            # 删除操作需要 token 鉴权
            token = request_data.get('token')
            if token != DELETE_TOKEN:
                return jsonify({"error": "无权限执行删除操作"}), 403
            quote_id = request_data.get('quote_id')
            if quote_id is None:
                return jsonify({"error": "缺少 quote_id 参数"}), 400
            try:
                quote_id = int(quote_id)
            except (ValueError, TypeError):
                return jsonify({"error": "quote_id 必须是整数"}), 400
            result, code = delete_message(client_id, quote_id)
            return jsonify(result), code
        elif request_type == "clear":
            # 清空操作需要 token 鉴权
            token = request_data.get('token')
            if token != DELETE_TOKEN:
                return jsonify({"error": "无权限执行清空操作"}), 403
            result, code = clear_messages(client_id)
            return jsonify(result), code
        else:
            # 返回错误响应
            return jsonify({"error": "未知请求类型"}), 400

    except Exception as e:
        logger.exception("处理请求时出错")
        return jsonify({"error": str(e)}), 500

def send_message(client_id):
    """获取指定客户端的语录列表"""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, message, created_at FROM quotes WHERE client_id = ? ORDER BY created_at DESC',
            (client_id,)
        )
        quotes = []
        for row in cursor.fetchall():
            quotes.append({
                'id': row[0],
                'message': row[1],
                'created_at': row[2]
            })
        return quotes, 200
    except Exception as e:
        logger.exception("获取语录失败")
        return {"error": "获取语录失败"}, 500
    finally:
        if conn:
            conn.close()

def save_message(client_id, message):
    """保存语录到数据库"""
    if not message or not message.strip():
        return {"error": "语录内容不能为空"}, 400

    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO quotes (client_id, message, created_at) VALUES (?, ?, ?)',
            (client_id, message.strip(), datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        conn.commit()
        return {
            "status": "success",
            "message": "语录保存成功",
            "quote_id": cursor.lastrowid
        }, 200
    except Exception as e:
        logger.exception("保存语录失败")
        return {"error": "保存语录失败"}, 500
    finally:
        if conn:
            conn.close()

def delete_message(client_id, quote_id):
    """删除指定语录"""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM quotes WHERE id = ? AND client_id = ?',
            (quote_id, client_id)
        )
        conn.commit()
        if cursor.rowcount > 0:
            return {"status": "success", "message": "语录删除成功"}, 200
        else:
            return {"error": "语录不存在或无权限删除"}, 404
    except Exception as e:
        logger.exception("删除语录失败")
        return {"error": "删除语录失败"}, 500
    finally:
        if conn:
            conn.close()

def clear_messages(client_id):
    """清空指定客户端的所有语录"""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM quotes WHERE client_id = ?',
            (client_id,)
        )
        conn.commit()
        return {"status": "success", "message": "语录清空成功"}, 200
    except Exception as e:
        logger.exception("清空语录失败")
        return {"error": "清空语录失败"}, 500
    finally:
        if conn:
            conn.close()

@app.route('/stats', methods=['GET'])
def get_stats():
    """获取统计信息"""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # 获取总语录数
        cursor.execute('SELECT COUNT(*) FROM quotes')
        total_quotes = cursor.fetchone()[0]

        # 获取客户端数量
        cursor.execute('SELECT COUNT(DISTINCT client_id) FROM quotes')
        total_clients = cursor.fetchone()[0]

        # 获取最近添加的语录
        cursor.execute('''
            SELECT client_id, message, created_at
            FROM quotes
            ORDER BY created_at DESC
            LIMIT 5
        ''')
        recent_quotes = []
        for row in cursor.fetchall():
            recent_quotes.append({
                'client_id': row[0],
                'message': row[1],
                'created_at': row[2]
            })

        return jsonify({
            'total_quotes': total_quotes,
            'total_clients': total_clients,
            'recent_quotes': recent_quotes
        })
    except Exception as e:
        logger.exception("获取统计信息失败")
        return jsonify({"error": "获取统计信息失败"}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # 初始化数据库
    init_db()
    logger.info("数据库初始化完成")
    logger.info("启动ing...")

    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 6673))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')

    app.run(host=host, port=port, debug=debug)
