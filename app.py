# -*- coding: utf-8 -*-
"""
yunicyyu 个人网站主应用
模块化架构，支持扩展更多功能
"""

import socket
import os
from flask import Flask, render_template, jsonify, request, send_file
from models import (
    init_db, get_stats, get_finance_stats, get_daily_summary,
    backup_database, get_backup_list, restore_database, BACKUP_DIR
)
from modules.schedule import schedule_bp
from modules.finance import finance_bp
from modules.first_times import first_times_bp
from modules.quotes import quotes_bp

app = Flask(__name__, static_folder='static')

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

init_db()

startup_backup = backup_database()
if startup_backup:
    print(f'[OK] 数据库已自动备份: {startup_backup}')

app.register_blueprint(schedule_bp)
app.register_blueprint(finance_bp)
app.register_blueprint(first_times_bp)
app.register_blueprint(quotes_bp)


@app.route('/')
def index():
    """首页 - 个人主页"""
    stats = get_stats()
    finance_stats = get_finance_stats()
    daily_summary = get_daily_summary()
    return render_template('index.html', stats=stats, finance_stats=finance_stats, daily_summary=daily_summary)


@app.route('/api/backup', methods=['POST'])
def api_backup():
    """API: 手动备份"""
    backup_path = backup_database()
    if backup_path:
        filename = os.path.basename(backup_path)
        return jsonify({'success': True, 'filename': filename})
    return jsonify({'success': False, 'message': '备份失败'})


@app.route('/api/backups')
def api_get_backups():
    """API: 获取备份列表"""
    backups = get_backup_list()
    return jsonify({'success': True, 'backups': backups})


@app.route('/api/restore/<filename>', methods=['POST'])
def api_restore(filename):
    """API: 恢复备份"""
    if restore_database(filename):
        return jsonify({'success': True, 'message': '恢复成功，请重启应用'})
    return jsonify({'success': False, 'message': '恢复失败'})


@app.route('/api/backup/download/<filename>')
def api_download_backup(filename):
    """API: 下载备份文件"""
    backup_path = os.path.join(BACKUP_DIR, filename)
    if os.path.exists(backup_path):
        return send_file(backup_path, as_attachment=True)
    return jsonify({'success': False, 'message': '文件不存在'}), 404


@app.route('/api/backup/delete/<filename>', methods=['POST'])
def api_delete_backup(filename):
    """API: 删除备份"""
    backup_path = os.path.join(BACKUP_DIR, filename)
    if os.path.exists(backup_path):
        os.remove(backup_path)
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': '文件不存在'}), 404


def is_port_available(port):
    """检查端口是否可用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
            return True
    except OSError:
        return False


def find_available_port(start_port=212, max_attempts=10):
    """从指定端口开始寻找可用端口"""
    for port in range(start_port, start_port + max_attempts):
        if is_port_available(port):
            return port
    return start_port


if __name__ == '__main__':
    port = find_available_port(212)
    
    print('=' * 50)
    print('yunicyyu 个人网站启动中...')
    print(f'请在浏览器中访问: http://127.0.0.1:{port}')
    print('按 Ctrl+C 停止服务器')
    print('=' * 50)
    
    app.run(debug=True, port=port, use_reloader=True)
