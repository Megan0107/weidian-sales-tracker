"""
数据库模块 - 管理SQLite数据库操作
用于存储微店商品SKU销量历史数据
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import os

# 数据库文件路径
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'sales_data.db')

# 初始库存
INITIAL_STOCK = 25000

# SKU名称映射
SKU_NAMES = {
    1: "宇文良时",
    2: "言尚",
    3: "邢武",
    4: "诸葛玥",
    5: "林晏",
    6: "宋墨",
    7: "袁慎",
    8: "肖涵",
    9: "鸿奕",
    10: "陆一航",
    11: "陆星延",
    12: "高深",
    13: "庆安",
    14: "吴添翼",
    15: "慕正明",
    16: "慕正扬",
    17: "鄂顺",
    18: "伍朔漠"
}


def get_db_connection() -> sqlite3.Connection:
    """
    获取数据库连接
    
    Returns:
        sqlite3.Connection: 数据库连接对象
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # 使查询结果可以通过列名访问
    return conn


def init_database() -> None:
    """
    初始化数据库
    创建必要的表结构
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 创建SKU数据表 - 存储每个SKU的历史记录
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sku_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku_id INTEGER NOT NULL,
            sku_name TEXT NOT NULL,
            current_stock INTEGER NOT NULL,
            sales_count INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建索引 - 加速查询
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_sku_id ON sku_sales(sku_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp ON sku_sales(timestamp)
    ''')
    
    # 创建汇总表 - 存储每个时间点的总销量
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_sales INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("[Database] 数据库初始化完成")


def save_sku_data(sku_data: List[Dict]) -> bool:
    """
    保存SKU数据到数据库
    
    Args:
        sku_data: SKU数据列表，每个元素包含sku_id, sku_name, current_stock等
        
    Returns:
        bool: 保存成功返回True，否则返回False
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        total_sales = 0
        
        for sku in sku_data:
            sku_id = sku.get('sku_id')
            sku_name = sku.get('sku_name', SKU_NAMES.get(sku_id, f'SKU_{sku_id}'))
            current_stock = sku.get('current_stock', 0)
            sales_count = INITIAL_STOCK - current_stock
            total_sales += max(0, sales_count)
            
            cursor.execute('''
                INSERT INTO sku_sales (sku_id, sku_name, current_stock, sales_count, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (sku_id, sku_name, current_stock, sales_count, current_time))
        
        # 保存汇总数据
        cursor.execute('''
            INSERT INTO sales_summary (total_sales, timestamp)
            VALUES (?, ?)
        ''', (total_sales, current_time))
        
        conn.commit()
        conn.close()
        print(f"[Database] 数据保存成功 - 总销量: {total_sales}")
        return True
        
    except Exception as e:
        print(f"[Database] 保存数据失败: {str(e)}")
        return False


def get_current_sales() -> List[Dict]:
    """
    获取当前最新的销量数据
    
    Returns:
        List[Dict]: 每个SKU的最新销量数据
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取每个SKU的最新记录
        cursor.execute('''
            SELECT sku_id, sku_name, current_stock, sales_count, timestamp
            FROM sku_sales
            WHERE id IN (
                SELECT MAX(id) FROM sku_sales GROUP BY sku_id
            )
            ORDER BY sales_count DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            result.append({
                'sku_id': row['sku_id'],
                'sku_name': row['sku_name'],
                'current_stock': row['current_stock'],
                'sales_count': row['sales_count'],
                'timestamp': row['timestamp']
            })
        
        return result
        
    except Exception as e:
        print(f"[Database] 获取当前数据失败: {str(e)}")
        return []


def get_sales_history(hours: int = 24) -> Dict:
    """
    获取历史销量数据
    
    Args:
        hours: 查询多少小时的历史数据，默认24小时
        
    Returns:
        Dict: 包含时间序列和每个SKU的销量数据
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取指定时间范围内的数据
        cursor.execute('''
            SELECT sku_id, sku_name, sales_count, timestamp
            FROM sku_sales
            WHERE timestamp >= datetime('now', '-{} hours')
            ORDER BY timestamp ASC
        '''.format(hours))
        
        rows = cursor.fetchall()
        conn.close()
        
        # 组织数据格式
        timestamps = []
        sku_history = {sku_id: [] for sku_id in SKU_NAMES.keys()}
        
        # 按时间分组
        time_groups = {}
        for row in rows:
            ts = row['timestamp']
            if ts not in time_groups:
                time_groups[ts] = {}
            time_groups[ts][row['sku_id']] = {
                'sales_count': row['sales_count'],
                'sku_name': row['sku_name']
            }
        
        # 转换为前端需要的格式
        for ts in sorted(time_groups.keys()):
            timestamps.append(ts)
            for sku_id in SKU_NAMES.keys():
                if sku_id in time_groups[ts]:
                    sku_history[sku_id].append(time_groups[ts][sku_id]['sales_count'])
                else:
                    # 如果没有数据，使用上一个值或0
                    prev_value = sku_history[sku_id][-1] if sku_history[sku_id] else 0
                    sku_history[sku_id].append(prev_value)
        
        return {
            'timestamps': timestamps,
            'sku_data': sku_history,
            'sku_names': SKU_NAMES
        }
        
    except Exception as e:
        print(f"[Database] 获取历史数据失败: {str(e)}")
        return {'timestamps': [], 'sku_data': {}, 'sku_names': SKU_NAMES}


def get_total_sales() -> Dict:
    """
    获取总销量统计
    
    Returns:
        Dict: 包含总销量、更新时间等信息
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取最新汇总数据
        cursor.execute('''
            SELECT total_sales, timestamp FROM sales_summary
            ORDER BY id DESC LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'total_sales': row['total_sales'],
                'last_updated': row['timestamp']
            }
        else:
            return {
                'total_sales': 0,
                'last_updated': None
            }
            
    except Exception as e:
        print(f"[Database] 获取总销量失败: {str(e)}")
        return {'total_sales': 0, 'last_updated': None}


def get_ranking() -> List[Dict]:
    """
    获取销量排名
    
    Returns:
        List[Dict]: 按销量排序的SKU列表
    """
    current_data = get_current_sales()
    
    # 添加排名
    for i, item in enumerate(current_data, 1):
        item['rank'] = i
        
    return current_data


def cleanup_old_data(days: int = 7) -> bool:
    """
    清理旧数据，保留指定天数的数据
    
    Args:
        days: 保留多少天的数据，默认7天
        
    Returns:
        bool: 清理成功返回True
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 删除旧数据
        cursor.execute('''
            DELETE FROM sku_sales
            WHERE timestamp < datetime('now', '-{} days')
        '''.format(days))
        
        cursor.execute('''
            DELETE FROM sales_summary
            WHERE timestamp < datetime('now', '-{} days')
        '''.format(days))
        
        conn.commit()
        conn.close()
        print(f"[Database] 清理完成，保留{days}天数据")
        return True
        
    except Exception as e:
        print(f"[Database] 清理数据失败: {str(e)}")
        return False


# 初始化数据库
if __name__ == '__main__':
    init_database()
    print("数据库初始化完成！")
