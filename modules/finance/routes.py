# -*- coding: utf-8 -*-
"""
记账模块
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from models import (
    get_categories, add_transaction, get_transactions, 
    get_transaction_by_id, delete_transaction, update_transaction,
    get_finance_stats, get_daily_summary, get_monthly_transactions,
    get_db, get_all_scenes, get_scene_stats
)
from datetime import datetime
import calendar

finance_bp = Blueprint('finance', __name__, url_prefix='/finance', template_folder='../../templates/finance')


@finance_bp.route('/')
def index():
    """记账首页"""
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    stats = get_finance_stats(date)
    categories = get_categories()
    recent_transactions = get_transactions(limit=20)
    daily_summary = get_daily_summary(date)
    
    return render_template('finance/index.html', 
                          stats=stats, 
                          categories=categories,
                          recent_transactions=recent_transactions,
                          current_date=date,
                          daily_summary=daily_summary)


@finance_bp.route('/calendar')
def calendar_view():
    """日历视图"""
    today = datetime.now()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)
    
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1
    
    daily_stats = get_monthly_transactions(year, month)
    
    total_expense = sum(day.get('expense', 0) for day in daily_stats.values())
    total_income = sum(day.get('income', 0) for day in daily_stats.values())
    total_balance = total_income - total_expense
    
    return render_template('finance/calendar.html',
                          year=year,
                          month=month - 1,
                          today=today.strftime('%Y-%m-%d'),
                          daily_stats=daily_stats,
                          monthly_summary={'expense': total_expense, 'income': total_income, 'balance': total_balance})


@finance_bp.route('/add', methods=['GET', 'POST'])
def add():
    """添加记录页面"""
    if request.method == 'POST':
        type_ = request.form.get('type', 'expense')
        amount = request.form.get('amount')
        category = request.form.get('category')
        date = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
        note = request.form.get('note', '')
        scene = request.form.get('scene', '')
        
        if amount and category:
            add_transaction(type_, amount, category, date, note, scene or None)
            return redirect(url_for('finance.index'))
    
    categories = get_categories()
    scenes = get_all_scenes()
    today = datetime.now().strftime('%Y-%m-%d')
    
    return render_template('finance/add.html', 
                          categories=categories,
                          scenes=scenes,
                          today=today)


@finance_bp.route('/edit/<int:transaction_id>', methods=['GET', 'POST'])
def edit(transaction_id):
    """编辑记录页面"""
    transaction = get_transaction_by_id(transaction_id)
    if not transaction:
        return redirect(url_for('finance.index'))
    
    if request.method == 'POST':
        type_ = request.form.get('type', 'expense')
        amount = request.form.get('amount')
        category = request.form.get('category')
        date = request.form.get('date')
        note = request.form.get('note', '')
        scene = request.form.get('scene', '')
        
        update_transaction(transaction_id, type_, amount, category, date, note, scene or None)
        return redirect(url_for('finance.index'))
    
    categories = get_categories()
    scenes = get_all_scenes()
    
    return render_template('finance/edit.html', 
                          transaction=transaction, 
                          categories=categories,
                          scenes=scenes)


@finance_bp.route('/api/add', methods=['POST'])
def api_add():
    """API: 添加记录"""
    data = request.get_json()
    
    type_ = data.get('type', 'expense')
    amount = data.get('amount')
    category = data.get('category')
    date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    note = data.get('note', '')
    scene = data.get('scene', '')
    
    if not amount or not category:
        return jsonify({'success': False, 'message': '金额和分类不能为空'})
    
    try:
        transaction_id = add_transaction(type_, amount, category, date, note, scene or None)
        return jsonify({'success': True, 'id': transaction_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@finance_bp.route('/api/quick-add', methods=['POST'])
def api_quick_add():
    """API: 快速添加（支持 "午饭 30" 格式：备注在前，金额在后）"""
    data = request.get_json()
    text = data.get('text', '').strip()
    date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    scene = data.get('scene', '')
    
    if not text:
        return jsonify({'success': False, 'message': '请输入内容'})
    
    parts = text.rsplit(None, 1)
    if len(parts) < 2:
        return jsonify({'success': False, 'message': '格式：备注 金额，如 "午饭 30"'})
    
    note = parts[0]
    try:
        amount = float(parts[1])
    except ValueError:
        return jsonify({'success': False, 'message': '金额格式错误，请用 "备注 金额" 格式'})
    
    type_ = 'expense'
    if any(kw in note for kw in ['工资', '奖金', '收入', '红包', '退款']):
        type_ = 'income'
    
    category_keywords = {
        '餐饮': ['饭', '餐', '吃', '外卖', '早餐', '午餐', '晚餐', '奶茶', '咖啡', '零食', '夜宵', '水果'],
        '交通': ['打车', '地铁', '公交', '油', '停车', '出行', '滴滴', '出租', '高铁', '火车', '飞机'],
        '购物': ['买', '购', '淘宝', '京东', '超市', '衣服', '鞋', '网购', '快递'],
        '娱乐': ['电影', '游戏', 'KTV', '唱歌', '玩', '视频', '会员', '音乐'],
        '学习': ['书', '课', '学习', '培训', '考试', '教材'],
    }
    
    category = '其他支出' if type_ == 'expense' else '其他收入'
    for cat, keywords in category_keywords.items():
        if any(kw in note for kw in keywords):
            category = cat
            break
    
    try:
        transaction_id = add_transaction(type_, abs(amount), category, date, note, scene or None)
        return jsonify({
            'success': True, 
            'id': transaction_id,
            'parsed': {
                'amount': abs(amount),
                'category': category,
                'type': type_,
                'note': note,
                'scene': scene or None
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@finance_bp.route('/api/edit/<int:transaction_id>', methods=['POST'])
def api_edit(transaction_id):
    """API: 编辑记录"""
    data = request.get_json()
    
    try:
        update_transaction(
            transaction_id,
            type_=data.get('type'),
            amount=data.get('amount'),
            category=data.get('category'),
            date=data.get('date'),
            note=data.get('note'),
            scene=data.get('scene')
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@finance_bp.route('/api/delete/<int:transaction_id>', methods=['POST'])
def api_delete(transaction_id):
    """API: 删除记录"""
    try:
        delete_transaction(transaction_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@finance_bp.route('/api/stats')
def api_stats():
    """API: 获取统计数据"""
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    stats = get_finance_stats(date)
    return jsonify(stats)


@finance_bp.route('/api/daily-summary')
def api_daily_summary():
    """API: 获取每日总结"""
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    summary = get_daily_summary(date)
    return jsonify({'summary': summary})


@finance_bp.route('/api/categories')
def api_categories():
    """API: 获取分类列表"""
    type_filter = request.args.get('type')
    categories = get_categories(type_filter)
    return jsonify(categories)


@finance_bp.route('/api/transaction/<int:transaction_id>')
def api_get_transaction(transaction_id):
    """API: 获取单条记录"""
    transaction = get_transaction_by_id(transaction_id)
    if transaction:
        return jsonify(transaction)
    return jsonify({'error': 'Not found'}), 404


@finance_bp.route('/api/transactions-by-date')
def api_transactions_by_date():
    """API: 获取指定日期的交易记录"""
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, type, amount, category, note, date, scene
        FROM transactions
        WHERE date = ?
        ORDER BY created_at DESC
    ''', (date,))
    
    transactions = []
    total_expense = 0
    total_income = 0
    
    for row in cursor.fetchall():
        amount = row['amount'] / 100
        transactions.append({
            'id': row['id'],
            'type': row['type'],
            'amount': amount,
            'category': row['category'],
            'note': row['note'],
            'date': row['date'],
            'scene': row['scene']
        })
        
        if row['type'] == 'expense':
            total_expense += amount
        else:
            total_income += amount
    
    conn.close()
    
    return jsonify({
        'success': True,
        'transactions': transactions,
        'stats': {
            'expense': total_expense,
            'income': total_income
        }
    })


@finance_bp.route('/api/monthly-stats')
def api_monthly_stats():
    """API: 获取指定月份的每日统计数据"""
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    
    daily_stats = get_monthly_transactions(year, month)
    
    total_expense = sum(day.get('expense', 0) for day in daily_stats.values())
    total_income = sum(day.get('income', 0) for day in daily_stats.values())
    total_balance = total_income - total_expense
    
    return jsonify({
        'success': True,
        'year': year,
        'month': month,
        'daily_stats': daily_stats,
        'monthly_summary': {
            'expense': total_expense,
            'income': total_income,
            'balance': total_balance
        }
    })


@finance_bp.route('/api/scenes')
def api_scenes():
    """API: 获取所有场景列表"""
    scenes = get_all_scenes()
    return jsonify({'success': True, 'scenes': scenes})


@finance_bp.route('/api/scene-stats')
def api_scene_stats():
    """API: 获取场景统计数据"""
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    stats = get_scene_stats(date_from, date_to)
    return jsonify({'success': True, 'stats': stats})
