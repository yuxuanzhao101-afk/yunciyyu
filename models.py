# -*- coding: utf-8 -*-
"""
数据库模型和工具函数
"""

import sqlite3
import os
import shutil
import glob
from datetime import datetime, timedelta

DATABASE = 'schedule.db'
BACKUP_DIR = 'backups'
MAX_BACKUPS = 7


def backup_database():
    """备份数据库"""
    if not os.path.exists(DATABASE):
        return None
    
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'schedule_backup_{timestamp}.db'
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    shutil.copy2(DATABASE, backup_path)
    
    clean_old_backups()
    
    return backup_path


def clean_old_backups():
    """清理旧备份，保留最近 MAX_BACKUPS 个"""
    if not os.path.exists(BACKUP_DIR):
        return
    
    pattern = os.path.join(BACKUP_DIR, 'schedule_backup_*.db')
    backups = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    
    for old_backup in backups[MAX_BACKUPS:]:
        try:
            os.remove(old_backup)
        except:
            pass


def get_backup_list():
    """获取备份列表"""
    if not os.path.exists(BACKUP_DIR):
        return []
    
    pattern = os.path.join(BACKUP_DIR, 'schedule_backup_*.db')
    backups = glob.glob(pattern)
    
    result = []
    for backup in sorted(backups, key=os.path.getmtime, reverse=True):
        stat = os.stat(backup)
        result.append({
            'filename': os.path.basename(backup),
            'path': backup,
            'size': stat.st_size,
            'created_at': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return result


def restore_database(backup_filename):
    """从备份恢复数据库"""
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    if not os.path.exists(backup_path):
        return False
    
    if os.path.exists(DATABASE):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pre_restore_backup = f'{DATABASE}.pre_restore_{timestamp}'
        shutil.copy2(DATABASE, pre_restore_backup)
    
    shutil.copy2(backup_path, DATABASE)
    return True


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT,
            priority TEXT DEFAULT '普通',
            completed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
            color TEXT DEFAULT '#667eea',
            icon TEXT DEFAULT 'fa-tag',
            sort_order INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
            amount INTEGER NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            note TEXT,
            scene TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute("PRAGMA table_info(transactions)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'scene' not in columns:
        cursor.execute('ALTER TABLE transactions ADD COLUMN scene TEXT')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS first_times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            location TEXT,
            feeling TEXT,
            tags TEXT,
            image_path TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            source TEXT,
            tags TEXT,
            image_path TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quick_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            sort_order INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute("PRAGMA table_info(quick_tags)")
    if cursor.fetchone() is None:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quick_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                sort_order INTEGER DEFAULT 0
            )
        ''')
    
    default_quick_tags = [
        ('治愈', 1),
        ('感悟', 2),
        ('摘抄', 3),
        ('手写', 4),
        ('旅行', 5),
        ('读书', 6),
        ('电影', 7),
        ('生活', 8),
    ]
    
    cursor.execute('SELECT COUNT(*) FROM quick_tags')
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            'INSERT INTO quick_tags (name, sort_order) VALUES (?, ?)',
            default_quick_tags
        )
    
    default_categories = [
        ('餐饮', 'expense', '#f5576c', 'fa-utensils', 1),
        ('交通', 'expense', '#667eea', 'fa-car', 2),
        ('购物', 'expense', '#f093fb', 'fa-shopping-bag', 3),
        ('娱乐', 'expense', '#4facfe', 'fa-gamepad', 4),
        ('学习', 'expense', '#38ef7d', 'fa-book', 5),
        ('其他支出', 'expense', '#a8a8a8', 'fa-ellipsis-h', 6),
        ('工资', 'income', '#38ef7d', 'fa-wallet', 1),
        ('奖金', 'income', '#f093fb', 'fa-gift', 2),
        ('其他收入', 'income', '#667eea', 'fa-plus-circle', 3),
    ]
    
    cursor.execute('SELECT COUNT(*) FROM categories')
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            'INSERT INTO categories (name, type, color, icon, sort_order) VALUES (?, ?, ?, ?, ?)',
            default_categories
        )
    
    conn.commit()
    conn.close()


def get_stats():
    """获取统计数据（用于首页展示）"""
    conn = get_db()
    cursor = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute('SELECT COUNT(*) FROM schedules')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM schedules WHERE completed = 0')
    pending = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM schedules WHERE completed = 1')
    completed = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM schedules WHERE date = ? AND completed = 0', (today,))
    today_pending = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT id, content, date, time, priority, completed 
        FROM schedules 
        WHERE date = ? AND completed = 0 
        ORDER BY 
            CASE WHEN priority = '紧急' THEN 0 ELSE 1 END,
            time IS NULL, time
        LIMIT 10
    ''', (today,))
    
    today_items = []
    for row in cursor.fetchall():
        today_items.append({
            'id': row['id'],
            'content': row['content'],
            'date': row['date'],
            'time': row['time'],
            'priority': row['priority'],
            'completed': row['completed']
        })
    
    conn.close()
    
    return {
        'total': total,
        'pending': pending,
        'completed': completed,
        'today_pending': today_pending,
        'today_items': today_items
    }


def get_categories(type_filter=None):
    """获取分类列表"""
    conn = get_db()
    cursor = conn.cursor()
    
    if type_filter:
        cursor.execute(
            'SELECT * FROM categories WHERE type = ? ORDER BY sort_order',
            (type_filter,)
        )
    else:
        cursor.execute('SELECT * FROM categories ORDER BY type, sort_order')
    
    categories = []
    for row in cursor.fetchall():
        categories.append({
            'id': row['id'],
            'name': row['name'],
            'type': row['type'],
            'color': row['color'],
            'icon': row['icon'],
            'sort_order': row['sort_order']
        })
    
    conn.close()
    return categories


def add_transaction(type_, amount, category, date, note=None, scene=None):
    """添加交易记录"""
    conn = get_db()
    cursor = conn.cursor()
    
    amount_int = int(float(amount) * 100)
    
    cursor.execute('''
        INSERT INTO transactions (type, amount, category, date, note, scene)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (type_, amount_int, category, date, note, scene))
    
    conn.commit()
    transaction_id = cursor.lastrowid
    conn.close()
    
    return transaction_id


def get_transactions(date_from=None, date_to=None, category=None, type_filter=None, scene=None, limit=50):
    """获取交易记录列表"""
    conn = get_db()
    cursor = conn.cursor()
    
    query = '''
        SELECT t.* FROM transactions t
        WHERE 1=1
    '''
    params = []
    
    if date_from:
        query += ' AND t.date >= ?'
        params.append(date_from)
    
    if date_to:
        query += ' AND t.date <= ?'
        params.append(date_to)
    
    if category:
        query += ' AND t.category = ?'
        params.append(category)
    
    if type_filter:
        query += ' AND t.type = ?'
        params.append(type_filter)
    
    if scene:
        query += ' AND t.scene = ?'
        params.append(scene)
    
    query += ' ORDER BY t.date DESC, t.created_at DESC LIMIT ?'
    params.append(limit)
    
    cursor.execute(query, params)
    
    transactions = []
    for row in cursor.fetchall():
        transactions.append({
            'id': row['id'],
            'type': row['type'],
            'amount': row['amount'] / 100,
            'category': row['category'],
            'date': row['date'],
            'note': row['note'],
            'scene': row['scene'],
            'created_at': row['created_at']
        })
    
    conn.close()
    return transactions


def get_transaction_by_id(transaction_id):
    """获取单条交易记录"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM transactions WHERE id = ?', (transaction_id,))
    row = cursor.fetchone()
    
    conn.close()
    
    if row:
        return {
            'id': row['id'],
            'type': row['type'],
            'amount': row['amount'] / 100,
            'category': row['category'],
            'date': row['date'],
            'note': row['note'],
            'scene': row['scene'],
            'created_at': row['created_at']
        }
    
    return None


def delete_transaction(transaction_id):
    """删除交易记录"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
    
    conn.commit()
    conn.close()


def update_transaction(transaction_id, type_=None, amount=None, category=None, date=None, note=None, scene=None):
    """更新交易记录"""
    conn = get_db()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if type_:
        updates.append('type = ?')
        params.append(type_)
    
    if amount is not None:
        updates.append('amount = ?')
        params.append(int(float(amount) * 100))
    
    if category:
        updates.append('category = ?')
        params.append(category)
    
    if date:
        updates.append('date = ?')
        params.append(date)
    
    if note is not None:
        updates.append('note = ?')
        params.append(note)
    
    if scene is not None:
        updates.append('scene = ?')
        params.append(scene)
    
    if updates:
        params.append(transaction_id)
        cursor.execute(f'UPDATE transactions SET {", ".join(updates)} WHERE id = ?', params)
        conn.commit()
    
    conn.close()


def get_daily_summary(date=None):
    """获取每日消费总结"""
    conn = get_db()
    cursor = conn.cursor()
    
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) FROM transactions 
        WHERE type = 'expense' AND date = ?
    ''', (date,))
    total_expense = cursor.fetchone()[0] / 100
    
    cursor.execute('''
        SELECT category, SUM(amount) as total 
        FROM transactions 
        WHERE type = 'expense' AND date = ?
        GROUP BY category 
        ORDER BY total DESC
        LIMIT 1
    ''', (date,))
    
    top_category = cursor.fetchone()
    
    conn.close()
    
    if total_expense == 0:
        return "今天还没有支出记录"
    
    if top_category:
        category_name = top_category['category']
        category_amount = top_category['total'] / 100
        percentage = (category_amount / total_expense) * 100
        
        if percentage >= 50:
            return f"今天花了 {total_expense:.0f} 元，主要在{category_name}（{percentage:.0f}%）"
        else:
            return f"今天花了 {total_expense:.0f} 元，{category_name}最多（{percentage:.0f}%）"
    
    return f"今天花了 {total_expense:.0f} 元"


def get_monthly_transactions(year, month):
    """获取某月的交易记录，按日期分组"""
    conn = get_db()
    cursor = conn.cursor()
    
    month_str = f"{year}-{month:02d}"
    
    cursor.execute('''
        SELECT date, type, SUM(amount) as total, COUNT(*) as count
        FROM transactions 
        WHERE date LIKE ?
        GROUP BY date, type
        ORDER BY date
    ''', (f'{month_str}%',))
    
    daily_stats = {}
    for row in cursor.fetchall():
        date = row['date']
        if date not in daily_stats:
            daily_stats[date] = {'expense': 0, 'income': 0, 'count': 0}
        
        if row['type'] == 'expense':
            daily_stats[date]['expense'] = row['total'] / 100
        else:
            daily_stats[date]['income'] = row['total'] / 100
        daily_stats[date]['count'] += row['count']
    
    conn.close()
    
    return daily_stats


def get_finance_stats(date=None):
    """获取财务统计数据"""
    conn = get_db()
    cursor = conn.cursor()
    
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    month_start = date[:7] + '-01'
    month_end = date[:7] + '-31'
    
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) FROM transactions 
        WHERE type = 'expense' AND date = ?
    ''', (date,))
    today_expense = cursor.fetchone()[0] / 100
    
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) FROM transactions 
        WHERE type = 'income' AND date = ?
    ''', (date,))
    today_income = cursor.fetchone()[0] / 100
    
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) FROM transactions 
        WHERE type = 'expense' AND date >= ? AND date <= ?
    ''', (month_start, month_end))
    month_expense = cursor.fetchone()[0] / 100
    
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) FROM transactions 
        WHERE type = 'income' AND date >= ? AND date <= ?
    ''', (month_start, month_end))
    month_income = cursor.fetchone()[0] / 100
    
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) FROM transactions 
        WHERE type = 'expense'
    ''')
    total_expense = cursor.fetchone()[0] / 100
    
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) FROM transactions 
        WHERE type = 'income'
    ''')
    total_income = cursor.fetchone()[0] / 100
    
    total_balance = total_income - total_expense
    
    cursor.execute('''
        SELECT category, SUM(amount) as total 
        FROM transactions 
        WHERE type = 'expense' AND date >= ? AND date <= ?
        GROUP BY category 
        ORDER BY total DESC
        LIMIT 5
    ''', (month_start, month_end))
    
    category_stats = []
    for row in cursor.fetchall():
        category_stats.append({
            'category': row['category'],
            'amount': row['total'] / 100
        })
    
    cursor.execute('''
        SELECT * FROM transactions 
        WHERE date = ? 
        ORDER BY created_at DESC
    ''', (date,))
    
    today_transactions = []
    for row in cursor.fetchall():
        today_transactions.append({
            'id': row['id'],
            'type': row['type'],
            'amount': row['amount'] / 100,
            'category': row['category'],
            'date': row['date'],
            'note': row['note'],
            'created_at': row['created_at']
        })
    
    conn.close()
    
    return {
        'today_expense': today_expense,
        'today_income': today_income,
        'month_expense': month_expense,
        'month_income': month_income,
        'month_balance': month_income - month_expense,
        'total_balance': total_balance,
        'category_stats': category_stats,
        'today_transactions': today_transactions
    }


def get_all_scenes():
    """获取所有场景列表"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT scene FROM transactions 
        WHERE scene IS NOT NULL AND scene != ''
        ORDER BY scene
    ''')
    
    scenes = [row['scene'] for row in cursor.fetchall()]
    conn.close()
    
    return scenes


def get_scene_stats(date_from=None, date_to=None):
    """按场景统计支出"""
    conn = get_db()
    cursor = conn.cursor()
    
    query = '''
        SELECT scene, type, SUM(amount) as total, COUNT(*) as count
        FROM transactions 
        WHERE scene IS NOT NULL AND scene != ''
    '''
    params = []
    
    if date_from:
        query += ' AND date >= ?'
        params.append(date_from)
    
    if date_to:
        query += ' AND date <= ?'
        params.append(date_to)
    
    query += ' GROUP BY scene, type ORDER BY total DESC'
    
    cursor.execute(query, params)
    
    scene_stats = {}
    for row in cursor.fetchall():
        scene = row['scene']
        if scene not in scene_stats:
            scene_stats[scene] = {'expense': 0, 'income': 0, 'count': 0}
        
        if row['type'] == 'expense':
            scene_stats[scene]['expense'] = row['total'] / 100
        else:
            scene_stats[scene]['income'] = row['total'] / 100
        scene_stats[scene]['count'] += row['count']
    
    conn.close()
    
    return scene_stats


def init_quotes_table():
    """初始化文字摘抄表"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            source TEXT,
            tags TEXT,
            image_path TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()


def get_quotes(tag=None, keyword=None):
    """获取摘抄列表"""
    conn = get_db()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM quotes WHERE 1=1'
    params = []
    
    if tag:
        query += ' AND tags LIKE ?'
        params.append(f'%{tag}%')
    
    if keyword:
        query += ' AND (content LIKE ? OR source LIKE ? OR tags LIKE ?)'
        keyword_param = f'%{keyword}%'
        params.extend([keyword_param, keyword_param, keyword_param])
    
    query += ' ORDER BY created_at DESC'
    
    cursor.execute(query, params)
    
    quotes = []
    for row in cursor.fetchall():
        quotes.append({
            'id': row['id'],
            'content': row['content'],
            'source': row['source'] or '',
            'tags': row['tags'] or '',
            'image_path': row['image_path'] or '',
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        })
    
    conn.close()
    return quotes


def get_quote_by_id(quote_id):
    """获取单条摘抄"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM quotes WHERE id = ?', (quote_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row['id'],
            'content': row['content'],
            'source': row['source'] or '',
            'tags': row['tags'] or '',
            'image_path': row['image_path'] or ''
        }
    return None


def add_quote(content, source=None, tags=None):
    """添加摘抄"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO quotes (content, source, tags)
        VALUES (?, ?, ?)
    ''', (content, source, tags))
    
    quote_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return quote_id


def update_quote(quote_id, content=None, source=None, tags=None):
    """更新摘抄"""
    conn = get_db()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if content is not None:
        updates.append('content = ?')
        params.append(content)
    
    if source is not None:
        updates.append('source = ?')
        params.append(source)
    
    if tags is not None:
        updates.append('tags = ?')
        params.append(tags)
    
    if updates:
        updates.append('updated_at = CURRENT_TIMESTAMP')
        params.append(quote_id)
        cursor.execute(f'UPDATE quotes SET {", ".join(updates)} WHERE id = ?', params)
        conn.commit()
    
    conn.close()


def delete_quote(quote_id):
    """删除摘抄"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT image_path FROM quotes WHERE id = ?', (quote_id,))
    row = cursor.fetchone()
    
    cursor.execute('DELETE FROM quotes WHERE id = ?', (quote_id,))
    conn.commit()
    conn.close()
    
    return row['image_path'] if row else None


def get_quote_tags():
    """获取所有标签"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT DISTINCT tags FROM quotes WHERE tags IS NOT NULL AND tags != ""')
    
    tags_set = set()
    for row in cursor.fetchall():
        if row['tags']:
            for tag in row['tags'].split(','):
                tag = tag.strip()
                if tag:
                    tags_set.add(tag)
    
    conn.close()
    return sorted(list(tags_set))


def get_quick_tags():
    """获取常用标签列表"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT name FROM quick_tags ORDER BY sort_order, id')
    tags = [row['name'] for row in cursor.fetchall()]
    conn.close()
    
    return tags


def add_quick_tag(name):
    """添加常用标签"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT MAX(sort_order) FROM quick_tags')
        max_order = cursor.fetchone()[0] or 0
        
        cursor.execute('INSERT INTO quick_tags (name, sort_order) VALUES (?, ?)', (name, max_order + 1))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False


def delete_quick_tag(name):
    """删除常用标签"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM quick_tags WHERE name = ?', (name,))
    conn.commit()
    conn.close()
    
    return True


def update_quick_tags(tags):
    """更新常用标签列表"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM quick_tags')
    
    for i, tag in enumerate(tags):
        cursor.execute('INSERT INTO quick_tags (name, sort_order) VALUES (?, ?)', (tag, i + 1))
    
    conn.commit()
    conn.close()
    
    return True


def get_random_quote():
    """获取随机一条摘抄"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM quotes ORDER BY RANDOM() LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row['id'],
            'content': row['content'],
            'source': row['source'] or '',
            'tags': row['tags'] or '',
            'image_path': row['image_path'] or ''
        }
    return None


def get_quotes_count():
    """获取摘抄总数"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM quotes')
    count = cursor.fetchone()[0]
    conn.close()
    
    return count
