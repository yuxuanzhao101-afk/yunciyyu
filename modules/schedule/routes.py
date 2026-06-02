# -*- coding: utf-8 -*-
"""
日程管理模块 - Flask Blueprint
"""

from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
from models import get_db

schedule_bp = Blueprint('schedule', __name__, url_prefix='/schedule')


@schedule_bp.route('/')
def index():
    """日程管理页面"""
    return render_template('schedule/index.html')


@schedule_bp.route('/api/schedules', methods=['GET'])
def get_schedules():
    """获取所有日程"""
    conn = get_db()
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute('''
        SELECT * FROM schedules 
        ORDER BY date ASC, time ASC, created_at ASC
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    schedules = []
    for row in rows:
        schedules.append({
            'id': row['id'],
            'content': row['content'],
            'date': row['date'],
            'time': row['time'],
            'priority': row['priority'],
            'completed': bool(row['completed']),
            'created_at': row['created_at']
        })
    
    return jsonify({
        'schedules': schedules,
        'today': today
    })


@schedule_bp.route('/api/schedules/<int:schedule_id>', methods=['GET'])
def get_schedule(schedule_id):
    """获取单个日程"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'success': False, 'message': '日程不存在'}), 404
    
    return jsonify({
        'success': True,
        'schedule': {
            'id': row['id'],
            'content': row['content'],
            'date': row['date'],
            'time': row['time'],
            'priority': row['priority'],
            'completed': bool(row['completed'])
        }
    })


@schedule_bp.route('/api/schedules', methods=['POST'])
def add_schedule():
    """添加日程"""
    data = request.get_json()
    
    content = data.get('content', '').strip()
    date = data.get('date', '')
    time = data.get('time', '')
    priority = data.get('priority', '普通')
    
    if not content or not date:
        return jsonify({'success': False, 'message': '内容和日期不能为空'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO schedules (content, date, time, priority)
        VALUES (?, ?, ?, ?)
    ''', (content, date, time, priority))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '添加成功',
        'id': new_id
    })


@schedule_bp.route('/api/schedules/<int:schedule_id>', methods=['PUT'])
def update_schedule(schedule_id):
    """编辑日程"""
    data = request.get_json()
    
    content = data.get('content', '').strip()
    date = data.get('date', '')
    time = data.get('time', '')
    priority = data.get('priority', '普通')
    
    if not content or not date:
        return jsonify({'success': False, 'message': '内容和日期不能为空'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM schedules WHERE id = ?', (schedule_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'success': False, 'message': '日程不存在'}), 404
    
    cursor.execute('''
        UPDATE schedules 
        SET content = ?, date = ?, time = ?, priority = ?
        WHERE id = ?
    ''', (content, date, time, priority, schedule_id))
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '更新成功'
    })


@schedule_bp.route('/api/schedules/<int:schedule_id>/complete', methods=['PUT'])
def toggle_complete(schedule_id):
    """切换完成状态"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT completed FROM schedules WHERE id = ?', (schedule_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return jsonify({'success': False, 'message': '日程不存在'}), 404
    
    new_status = 0 if row['completed'] else 1
    
    cursor.execute('UPDATE schedules SET completed = ? WHERE id = ?', (new_status, schedule_id))
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '状态已更新',
        'completed': bool(new_status)
    })


@schedule_bp.route('/api/schedules/<int:schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """删除日程"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '删除成功'
    })
