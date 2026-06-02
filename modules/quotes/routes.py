# -*- coding: utf-8 -*-
"""
文字摘抄模块路由
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.utils import secure_filename
from models import (
    get_quotes, get_quote_by_id, add_quote, update_quote, 
    delete_quote, get_quote_tags, get_random_quote, get_quotes_count,
    get_quick_tags, add_quick_tag, delete_quick_tag, update_quick_tags
)
from datetime import datetime
import os

quotes_bp = Blueprint('quotes', __name__, url_prefix='/quotes', template_folder='../../templates/quotes')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@quotes_bp.route('/')
def index():
    """文字摘抄首页"""
    quotes = get_quotes()
    tags = get_quote_tags()
    count = get_quotes_count()
    return render_template('quotes/index.html', quotes=quotes, tags=tags, count=count)


@quotes_bp.route('/api/list')
def api_list():
    """API: 获取摘抄列表"""
    tag = request.args.get('tag')
    keyword = request.args.get('keyword', '').strip()
    
    quotes = get_quotes(tag=tag, keyword=keyword)
    
    return jsonify({'success': True, 'quotes': quotes})


@quotes_bp.route('/api/tags')
def api_tags():
    """API: 获取所有标签"""
    tags = get_quote_tags()
    return jsonify({'success': True, 'tags': tags})


@quotes_bp.route('/api/random')
def api_random():
    """API: 获取随机一条摘抄"""
    quote = get_random_quote()
    if quote:
        return jsonify({'success': True, 'quote': quote})
    return jsonify({'success': False, 'message': '暂无摘抄'})


@quotes_bp.route('/api/count')
def api_count():
    """API: 获取摘抄总数"""
    count = get_quotes_count()
    return jsonify({'success': True, 'count': count})


@quotes_bp.route('/api/add', methods=['POST'])
def api_add():
    """API: 添加摘抄"""
    data = request.get_json()
    
    content = data.get('content', '').strip()
    source = data.get('source', '').strip()
    tags = data.get('tags', '').strip()
    
    if not content:
        return jsonify({'success': False, 'message': '内容不能为空'})
    
    quote_id = add_quote(content, source or None, tags or None)
    
    return jsonify({'success': True, 'id': quote_id})


@quotes_bp.route('/api/edit/<int:quote_id>', methods=['POST'])
def api_edit(quote_id):
    """API: 编辑摘抄"""
    data = request.get_json()
    
    content = data.get('content', '').strip()
    source = data.get('source', '').strip()
    tags = data.get('tags', '').strip()
    
    if not content:
        return jsonify({'success': False, 'message': '内容不能为空'})
    
    update_quote(quote_id, content, source or None, tags or None)
    
    return jsonify({'success': True})


@quotes_bp.route('/api/delete/<int:quote_id>', methods=['POST'])
def api_delete(quote_id):
    """API: 删除摘抄"""
    image_path = delete_quote(quote_id)
    
    if image_path:
        try:
            full_path = os.path.join(current_app.root_path, 'static', image_path)
            if os.path.exists(full_path):
                os.remove(full_path)
        except:
            pass
    
    return jsonify({'success': True})


@quotes_bp.route('/api/record/<int:quote_id>')
def api_get_record(quote_id):
    """API: 获取单条摘抄"""
    quote = get_quote_by_id(quote_id)
    
    if quote:
        return jsonify({'success': True, 'quote': quote})
    
    return jsonify({'success': False, 'message': '摘抄不存在'})


@quotes_bp.route('/api/upload-image/<int:quote_id>', methods=['POST'])
def api_upload_image(quote_id):
    """API: 上传配图"""
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': '没有选择文件'})
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'})
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': '不支持的文件格式'})
    
    upload_dir = os.path.join(current_app.root_path, 'static', 'quote_images')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = secure_filename(f'{quote_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}.{ext}')
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)
    
    relative_path = f'quote_images/{filename}'
    
    quote = get_quote_by_id(quote_id)
    if quote and quote.get('image_path'):
        try:
            old_path = os.path.join(current_app.root_path, 'static', quote['image_path'])
            if os.path.exists(old_path):
                os.remove(old_path)
        except:
            pass
    
    from models import get_db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE quotes SET image_path = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                   (relative_path, quote_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'image_path': relative_path})


@quotes_bp.route('/api/quick-tags')
def api_quick_tags():
    """API: 获取常用标签列表"""
    tags = get_quick_tags()
    return jsonify({'success': True, 'tags': tags})


@quotes_bp.route('/api/quick-tags/add', methods=['POST'])
def api_add_quick_tag():
    """API: 添加常用标签"""
    data = request.get_json()
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({'success': False, 'message': '标签名不能为空'})
    
    if add_quick_tag(name):
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': '标签已存在'})


@quotes_bp.route('/api/quick-tags/delete', methods=['POST'])
def api_delete_quick_tag():
    """API: 删除常用标签"""
    data = request.get_json()
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({'success': False, 'message': '标签名不能为空'})
    
    delete_quick_tag(name)
    return jsonify({'success': True})


@quotes_bp.route('/api/quick-tags/update', methods=['POST'])
def api_update_quick_tags():
    """API: 更新常用标签列表"""
    data = request.get_json()
    tags = data.get('tags', [])
    
    update_quick_tags(tags)
    return jsonify({'success': True})
