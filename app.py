"""
Flask主应用 - 微店销量监控网站
提供API接口和前端页面服务
"""

from flask import Flask, jsonify, render_template
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit
import os
from datetime import datetime

# 导入自定义模块
from database import (
    init_database, save_sku_data, get_current_sales, 
    get_sales_history, get_total_sales, get_ranking, cleanup_old_data
)
from scraper import scrape_product_data, calculate_sales

# 创建Flask应用
app = Flask(__name__)

# 启用CORS跨域支持
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# 配置
app.config['JSON_AS_ASCII'] = False  # 支持中文JSON输出
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# 全局变量 - 存储最新数据
latest_data = {
    'sku_data': [],
    'last_update': None,
    'total_sales': 0
}

# 是否使用模拟数据（开发测试时设为True）
USE_MOCK_DATA = False


def update_data():
    """
    更新数据的后台任务
    每1分钟执行一次（降低频率提高稳定性）
    """
    global latest_data
    
    try:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始更新数据...")
        
        # 抓取数据
        sku_data = scrape_product_data(use_mock=USE_MOCK_DATA)
        
        # 计算销量
        sku_data = calculate_sales(sku_data)
        
        # 保存到数据库
        save_sku_data(sku_data)
        
        # 更新全局变量
        latest_data['sku_data'] = sku_data
        latest_data['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        latest_data['total_sales'] = sum(s['sales_count'] for s in sku_data)
        
        print(f"[Scheduler] 数据更新完成 - 总销量: {latest_data['total_sales']}")
        
        # 每周清理一次旧数据
        if datetime.now().hour == 0 and datetime.now().minute == 0:
            cleanup_old_data(days=7)
            
    except Exception as e:
        print(f"[Scheduler] 更新数据失败: {str(e)}")


# ============ API路由 ============

@app.route('/')
def index():
    """
    主页 - 返回前端页面
    """
    return render_template('index.html')


@app.route('/api/current')
def api_current():
    """
    获取当前所有SKU的销量数据
    
    Returns:
        JSON: {
            "success": true,
            "data": [...],
            "total_sales": 12345,
            "last_update": "2024-01-01 12:00:00"
        }
    """
    try:
        # 从数据库获取最新数据
        data = get_current_sales()
        
        # 按销量排序
        data.sort(key=lambda x: x['sales_count'], reverse=True)
        
        # 添加排名
        for i, item in enumerate(data, 1):
            item['rank'] = i
        
        total = sum(d['sales_count'] for d in data)
        
        return jsonify({
            'success': True,
            'data': data,
            'total_sales': total,
            'last_update': latest_data['last_update'] or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'sku_count': len(data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '获取当前数据失败'
        }), 500


@app.route('/api/history')
def api_history():
    """
    获取历史销量数据（用于图表）
    
    Query参数:
        hours: 查询多少小时的数据，默认24
    
    Returns:
        JSON: {
            "success": true,
            "data": {
                "timestamps": [...],
                "sku_data": {...},
                "sku_names": {...}
            }
        }
    """
    try:
        from flask import request
        hours = request.args.get('hours', 24, type=int)
        
        # 限制最大查询范围
        if hours > 168:  # 最多7天
            hours = 168
        
        data = get_sales_history(hours=hours)
        
        return jsonify({
            'success': True,
            'data': data,
            'hours': hours
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '获取历史数据失败'
        }), 500


@app.route('/api/ranking')
def api_ranking():
    """
    获取销量排名
    
    Returns:
        JSON: {
            "success": true,
            "data": [...]
        }
    """
    try:
        data = get_ranking()
        
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '获取排名失败'
        }), 500


@app.route('/api/summary')
def api_summary():
    """
    获取汇总统计
    
    Returns:
        JSON: {
            "success": true,
            "data": {
                "total_sales": 12345,
                "last_updated": "...",
                "sku_count": 18
            }
        }
    """
    try:
        summary = get_total_sales()
        current = get_current_sales()
        
        return jsonify({
            'success': True,
            'data': {
                'total_sales': summary['total_sales'],
                'last_updated': summary['last_updated'],
                'sku_count': len(current),
                'top_seller': current[0] if current else None
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '获取汇总数据失败'
        }), 500


@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    """
    手动刷新数据
    
    Returns:
        JSON: 刷新结果
    """
    try:
        update_data()
        
        return jsonify({
            'success': True,
            'message': '数据刷新成功',
            'last_update': latest_data['last_update'],
            'total_sales': latest_data['total_sales']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '数据刷新失败'
        }), 500


@app.route('/api/status')
def api_status():
    """
    获取系统状态
    
    Returns:
        JSON: 系统状态信息
    """
    return jsonify({
        'success': True,
        'status': 'running',
        'last_update': latest_data['last_update'],
        'total_sales': latest_data['total_sales'],
        'sku_count': len(latest_data['sku_data']),
        'use_mock': USE_MOCK_DATA
    })


# ============ 错误处理 ============

@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({
        'success': False,
        'error': 'Not Found',
        'message': '请求的资源不存在'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return jsonify({
        'success': False,
        'error': 'Internal Server Error',
        'message': '服务器内部错误'
    }), 500


# ============ 启动配置 ============

def start_scheduler():
    """
    启动定时任务调度器
    """
    scheduler = BackgroundScheduler()
    
    # 每5分钟执行一次数据更新（降低频率提高稳定性）
    scheduler.add_job(
        func=update_data,
        trigger=IntervalTrigger(minutes=1),
        id='update_sales_data',
        name='更新销量数据',
        replace_existing=True
    )
    
    scheduler.start()
    print("[Scheduler] 定时任务已启动，每1分钟更新一次数据")
    
    # 注册关闭钩子
    atexit.register(lambda: scheduler.shutdown())
    
    return scheduler


def init_app():
    """
    初始化应用
    """
    print("=" * 60)
    print("微店销量监控系统启动")
    print("=" * 60)
    
    # 初始化数据库
    init_database()
    
    # 首次数据更新
    print("\n[Init] 执行首次数据更新...")
    update_data()
    
    # 启动定时任务
    start_scheduler()
    
    print("\n[Init] 应用初始化完成！")
    print("=" * 60)


# ============ 生产环境初始化 ============
# 当使用gunicorn启动时，这里会执行
init_app()

# ============ 主入口 ============

if __name__ == '__main__':
    # 启动Flask服务器
    # host='0.0.0.0' 允许外部访问
    # debug=False 生产环境关闭调试模式
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=False,
        threaded=True
    )
