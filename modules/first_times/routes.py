# -*- coding: utf-8 -*-
"""
人生第一次记录模块路由
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app
from werkzeug.utils import secure_filename
from models import get_db
from datetime import datetime
import os

first_times_bp = Blueprint('first_times', __name__, url_prefix='/first-times', template_folder='../../templates/first_times')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@first_times_bp.route('/')
def index():
    """人生第一次记录首页"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM first_times')
    total_count = cursor.fetchone()[0]
    
    conn.close()
    
    return render_template('first_times/index.html', total_count=total_count)


@first_times_bp.route('/api/list')
def api_list():
    """API: 获取记录列表"""
    year = request.args.get('year')
    tag = request.args.get('tag')
    keyword = request.args.get('keyword', '').strip()
    
    conn = get_db()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM first_times WHERE 1=1'
    params = []
    
    if year:
        query += ' AND strftime("%Y", date) = ?'
        params.append(year)
    
    if tag:
        query += ' AND tags LIKE ?'
        params.append(f'%{tag}%')
    
    if keyword:
        query += ' AND (title LIKE ? OR location LIKE ? OR feeling LIKE ?)'
        keyword_param = f'%{keyword}%'
        params.extend([keyword_param, keyword_param, keyword_param])
    
    query += ' ORDER BY date DESC, created_at DESC'
    
    cursor.execute(query, params)
    records = []
    for row in cursor.fetchall():
        records.append({
            'id': row['id'],
            'title': row['title'],
            'date': row['date'],
            'location': row['location'] or '',
            'feeling': row['feeling'] or '',
            'tags': row['tags'] or '',
            'image_path': row['image_path'] or '',
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        })
    
    conn.close()
    
    return jsonify({'success': True, 'records': records})


@first_times_bp.route('/api/years')
def api_years():
    """API: 获取所有年份列表"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT strftime('%Y', date) as year 
        FROM first_times 
        ORDER BY year DESC
    ''')
    
    years = [row['year'] for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'success': True, 'years': years})


@first_times_bp.route('/api/tags')
def api_tags():
    """API: 获取所有标签列表"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT DISTINCT tags FROM first_times WHERE tags IS NOT NULL AND tags != ""')
    
    tags_set = set()
    for row in cursor.fetchall():
        if row['tags']:
            for tag in row['tags'].split(','):
                tag = tag.strip()
                if tag:
                    tags_set.add(tag)
    
    conn.close()
    
    return jsonify({'success': True, 'tags': sorted(list(tags_set))})


@first_times_bp.route('/api/add', methods=['POST'])
def api_add():
    """API: 添加记录"""
    data = request.get_json()
    
    title = data.get('title', '').strip()
    date = data.get('date')
    location = data.get('location', '').strip()
    feeling = data.get('feeling', '').strip()
    tags = data.get('tags', '').strip()
    
    if not title or not date or not feeling:
        return jsonify({'success': False, 'message': '事件名称、日期和心情感受为必填项'})
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO first_times (title, date, location, feeling, tags)
        VALUES (?, ?, ?, ?, ?)
    ''', (title, date, location, feeling, tags))
    
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'id': record_id})


@first_times_bp.route('/api/edit/<int:record_id>', methods=['POST'])
def api_edit(record_id):
    """API: 编辑记录"""
    data = request.get_json()
    
    title = data.get('title', '').strip()
    date = data.get('date')
    location = data.get('location', '').strip()
    feeling = data.get('feeling', '').strip()
    tags = data.get('tags', '').strip()
    
    if not title or not date or not feeling:
        return jsonify({'success': False, 'message': '事件名称、日期和心情感受为必填项'})
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE first_times 
        SET title = ?, date = ?, location = ?, feeling = ?, tags = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (title, date, location, feeling, tags, record_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})


@first_times_bp.route('/api/delete/<int:record_id>', methods=['POST'])
def api_delete(record_id):
    """API: 删除记录"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT image_path FROM first_times WHERE id = ?', (record_id,))
    row = cursor.fetchone()
    
    if row and row['image_path']:
        try:
            image_full_path = os.path.join(current_app.root_path, 'static', row['image_path'])
            if os.path.exists(image_full_path):
                os.remove(image_full_path)
        except:
            pass
    
    cursor.execute('DELETE FROM first_times WHERE id = ?', (record_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})


@first_times_bp.route('/api/upload-image/<int:record_id>', methods=['POST'])
def api_upload_image(record_id):
    """API: 上传配图"""
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': '没有选择文件'})
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'})
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': '不支持的文件格式'})
    
    upload_dir = os.path.join(current_app.root_path, 'static', 'first_images')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = secure_filename(f'{record_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}.{ext}')
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)
    
    relative_path = f'first_images/{filename}'
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT image_path FROM first_times WHERE id = ?', (record_id,))
    row = cursor.fetchone()
    
    if row and row['image_path']:
        try:
            old_path = os.path.join(current_app.root_path, 'static', row['image_path'])
            if os.path.exists(old_path):
                os.remove(old_path)
        except:
            pass
    
    cursor.execute('UPDATE first_times SET image_path = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                   (relative_path, record_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'image_path': relative_path})


@first_times_bp.route('/api/record/<int:record_id>')
def api_get_record(record_id):
    """API: 获取单条记录"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM first_times WHERE id = ?', (record_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify({
            'success': True,
            'record': {
                'id': row['id'],
                'title': row['title'],
                'date': row['date'],
                'location': row['location'] or '',
                'feeling': row['feeling'] or '',
                'tags': row['tags'] or '',
                'image_path': row['image_path'] or ''
            }
        })
    
    return jsonify({'success': False, 'message': '记录不存在'})
