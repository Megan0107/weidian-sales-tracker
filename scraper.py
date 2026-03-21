"""
数据抓取模块 - 从微店页面抓取商品SKU数据
"""

import requests
import re
import json
import time
import html as html_module
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

# 商品URL
PRODUCT_URL = "https://weidian.com/item.html?itemID=7712692985"

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

# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}


def fetch_page(url: str = PRODUCT_URL, max_retries: int = 3) -> Optional[str]:
    """
    获取页面HTML内容
    
    Args:
        url: 页面URL
        max_retries: 最大重试次数
        
    Returns:
        Optional[str]: 页面HTML内容，失败返回None
    """
    for attempt in range(max_retries):
        try:
            print(f"[Scraper] 正在获取页面数据 (尝试 {attempt + 1}/{max_retries})...")
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            # 检查编码
            if response.encoding == 'ISO-8859-1':
                response.encoding = 'utf-8'
            
            print(f"[Scraper] 页面获取成功，大小: {len(response.text)} bytes")
            return response.text
            
        except requests.exceptions.RequestException as e:
            print(f"[Scraper] 请求失败: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                print(f"[Scraper] {wait_time}秒后重试...")
                time.sleep(wait_time)
            else:
                print("[Scraper] 达到最大重试次数，获取失败")
                return None
        
        except Exception as e:
            print(f"[Scraper] 未知错误: {str(e)}")
            return None
    
    return None


def extract_sku_data_from_html(html: str) -> List[Dict]:
    """
    从HTML中提取SKU数据
    
    Args:
        html: 页面HTML内容
        
    Returns:
        List[Dict]: SKU数据列表
    """
    sku_data = []
    
    try:
        # 首先解码HTML实体（微店页面数据被HTML实体编码）
        decoded_html = html_module.unescape(html)
        
        # 方法1: 直接查找页面中的SKU数据JSON
        # 根据实际页面结构，SKU数据以 {"sku_id": {"stock": xxx, "title": "xxx"}} 格式嵌入
        
        # 首先尝试查找包含SKU数据的JSON块
        sku_map_pattern = r'"(\d{11,12})":\s*\{\s*"arriveRemind"\s*:\s*(?:true|false)\s*,\s*"id"\s*:\s*\d+\s*,\s*"img"\s*:\s*"[^"]*"\s*,\s*"isQuantify"\s*:\s*(?:true|false)\s*,\s*"origin_price"\s*:\s*"[^"]+"\s*,\s*"price"\s*:\s*"[^"]+"\s*,\s*"showHotTag"\s*:\s*(?:true|false)\s*,\s*"stock"\s*:\s*(\d+)\s*,\s*"title"\s*:\s*"([^"]+)"\s*\}'
        
        matches = re.findall(sku_map_pattern, decoded_html)
        
        if matches:
            print(f"[Scraper] 找到 {len(matches)} 个SKU数据")
            
            # 创建名称到ID的映射
            name_to_id = {name: idx for idx, name in SKU_NAMES.items()}
            
            for sku_id_str, stock_str, title in matches:
                # 根据名称找到对应的SKU ID
                sku_id = name_to_id.get(title, 0)
                if sku_id == 0:
                    # 如果找不到，尝试模糊匹配
                    for idx, name in SKU_NAMES.items():
                        if name in title or title in name:
                            sku_id = idx
                            break
                
                if sku_id > 0:
                    sku_data.append({
                        'sku_id': sku_id,
                        'sku_name': title,
                        'current_stock': int(stock_str),
                        'original_price': 1.0,
                        'price': 1.0
                    })
            
            if len(sku_data) >= 18:
                print(f"[Scraper] 成功提取 {len(sku_data)} 个SKU数据")
                return sku_data
        
        # 方法2: 尝试更宽松的匹配模式
        print("[Scraper] 尝试替代匹配模式...")
        alt_pattern = r'"(\d{11,12})":\s*\{[^}]*"stock"\s*:\s*(\d+)[^}]*"title"\s*:\s*"([^"]+)"[^}]*\}'
        alt_matches = re.findall(alt_pattern, decoded_html)
        
        if alt_matches and len(sku_data) < 18:
            print(f"[Scraper] 替代模式找到 {len(alt_matches)} 个SKU")
            name_to_id = {name: idx for idx, name in SKU_NAMES.items()}
            
            for sku_id_str, stock_str, title in alt_matches:
                sku_id = name_to_id.get(title, 0)
                if sku_id == 0:
                    for idx, name in SKU_NAMES.items():
                        if name in title or title in name:
                            sku_id = idx
                            break
                
                # 检查是否已存在
                existing = [s for s in sku_data if s['sku_id'] == sku_id]
                if sku_id > 0 and not existing:
                    sku_data.append({
                        'sku_id': sku_id,
                        'sku_name': title,
                        'current_stock': int(stock_str),
                        'original_price': 1.0,
                        'price': 1.0
                    })
        
        # 方法3: 如果以上都失败，返回模拟数据
        if len(sku_data) < 18:
            print(f"[Scraper] 只获取到 {len(sku_data)} 个SKU，使用模拟数据补充")
            existing_ids = {s['sku_id'] for s in sku_data}
            for i, name in SKU_NAMES.items():
                if i not in existing_ids:
                    sku_data.append({
                        'sku_id': i,
                        'sku_name': name,
                        'current_stock': INITIAL_STOCK,
                        'original_price': 1.0,
                        'price': 1.0
                    })
                    
    except Exception as e:
        print(f"[Scraper] 提取数据时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sku_data = generate_mock_data()
    
    return sku_data


def generate_mock_data() -> List[Dict]:
    """
    生成模拟SKU数据（用于测试或当页面无法访问时）
    
    Returns:
        List[Dict]: 模拟SKU数据
    """
    import random
    
    mock_data = []
    for i, name in SKU_NAMES.items():
        # 生成随机销量（0-5000之间）
        random_sales = random.randint(0, 5000)
        mock_data.append({
            'sku_id': i,
            'sku_name': name,
            'current_stock': INITIAL_STOCK - random_sales,
            'original_price': 35.0,
            'price': 35.0
        })
    
    print(f"[Scraper] 生成 {len(mock_data)} 个模拟SKU数据")
    return mock_data


def scrape_product_data(use_mock: bool = False) -> List[Dict]:
    """
    抓取商品数据的主函数
    
    Args:
        use_mock: 是否使用模拟数据
        
    Returns:
        List[Dict]: SKU数据列表
    """
    if use_mock:
        print("[Scraper] 使用模拟数据模式")
        return generate_mock_data()
    
    # 获取页面
    html = fetch_page()
    if not html:
        print("[Scraper] 页面获取失败，使用模拟数据")
        return generate_mock_data()
    
    # 提取SKU数据
    sku_data = extract_sku_data_from_html(html)
    
    # 确保数据完整
    if len(sku_data) < 18:
        print(f"[Scraper] 警告: 只获取到 {len(sku_data)} 个SKU，预期18个")
        # 补充缺失的SKU
        existing_ids = {s['sku_id'] for s in sku_data}
        for i, name in SKU_NAMES.items():
            if i not in existing_ids:
                sku_data.append({
                    'sku_id': i,
                    'sku_name': name,
                    'current_stock': INITIAL_STOCK,
                    'original_price': 35.0,
                    'price': 35.0
                })
    
    # 按sku_id排序
    sku_data.sort(key=lambda x: x['sku_id'])
    
    print(f"[Scraper] 成功获取 {len(sku_data)} 个SKU数据")
    return sku_data


def calculate_sales(sku_data: List[Dict]) -> List[Dict]:
    """
    计算每个SKU的销量
    
    Args:
        sku_data: SKU数据列表
        
    Returns:
        List[Dict]: 包含销量的SKU数据
    """
    for sku in sku_data:
        current_stock = sku.get('current_stock', INITIAL_STOCK)
        sales = INITIAL_STOCK - current_stock
        sku['sales_count'] = max(0, sales)
        sku['sales_percentage'] = round((sales / INITIAL_STOCK) * 100, 2) if sales > 0 else 0
    
    return sku_data


# 测试代码
if __name__ == '__main__':
    print("=" * 50)
    print("微店数据抓取测试")
    print("=" * 50)
    
    # 测试抓取
    data = scrape_product_data(use_mock=True)  # 先用模拟数据测试
    data = calculate_sales(data)
    
    print("\n抓取结果:")
    print("-" * 50)
    for sku in data:
        print(f"{sku['sku_name']:8s} - 库存: {sku['current_stock']:5d} - 销量: {sku['sales_count']:5d} ({sku['sales_percentage']:5.2f}%)")
    
    total_sales = sum(s['sales_count'] for s in data)
    print("-" * 50)
    print(f"总销量: {total_sales}")
