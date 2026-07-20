"""
天行数据新闻 API 抓取模块 - 作为 RSS 的补充新闻源

天行数据提供分类新闻API，免费100次/天
注册地址: https://www.tianapi.com/signup.html
申请接口后在控制台获取 API Key
"""
import os
import requests
import pytz
from datetime import datetime, timedelta, timezone
from typing import List
from news_fetcher import NewsItem
from config import TIANAPI_KEY, TIANAPI_CONFIG

# API 端点
TIANAPI_BASE = "https://apis.tianapi.com"

# 新闻分类对应的接口和频道
TIANAPI_CHANNELS = [
    {
        "name": "天行-国内",
        "endpoint": "/generalnews/index",  # 综合新闻接口
        "params": {"word": "国内"},
        "category": "domestic",
        "weight": 0.9,
    },
    {
        "name": "天行-国际",
        "endpoint": "/generalnews/index",
        "params": {"word": "国际"},
        "category": "international",
        "weight": 0.9,
    },
    {
        "name": "天行-科技",
        "endpoint": "/generalnews/index",
        "params": {"word": "科技"},
        "category": "tech",
        "weight": 0.8,
    },
    {
        "name": "天行-社会",
        "endpoint": "/generalnews/index",
        "params": {"word": "社会"},
        "category": "society",
        "weight": 0.8,
    },
]


def parse_tianapi_date(date_str: str) -> datetime:
    """解析天行API的日期格式（如 2025-07-20 06:30:00）"""
    if not date_str:
        return datetime.now(timezone.utc)
    try:
        # 天行返回的时间通常是北京时间字符串，没有时区信息
        shanghai_tz = pytz.timezone("Asia/Shanghai")
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return shanghai_tz.localize(dt)
    except Exception:
        try:
            # 尝试 ISO 格式
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt
        except Exception:
            return datetime.now(timezone.utc)


def fetch_tianapi_channel(channel: dict, api_key: str) -> List[NewsItem]:
    """抓取天行数据单个频道的新闻"""
    items = []

    if not api_key:
        return items

    params = {
        "key": api_key,
        "num": TIANAPI_CONFIG.get("num_per_channel", 20),
        "rand": 1,  # 随机排序
    }
    params.update(channel["params"])

    try:
        url = TIANAPI_BASE + channel["endpoint"]
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()

        if data.get("code") != 200:
            print(f"  ⚠️  {channel['name']} API返回错误: {data.get('msg', '未知错误')}")
            return items

        news_list = data.get("result", {}).get("list", [])

        for entry in news_list:
            title = entry.get("title", "").strip()
            if not title:
                continue

            summary = entry.get("description", "") or entry.get("digest", "")
            link = entry.get("url", "")
            pub_date = parse_tianapi_date(entry.get("ctime", ""))
            source = entry.get("source", channel["name"])

            items.append(NewsItem(
                title=title,
                summary=summary,
                link=link,
                published=pub_date,
                source=f"天行-{source}" if source else channel["name"],
                category=channel["category"],
                weight=channel["weight"],
            ))

        print(f"  ✅ {channel['name']}: 获取 {len(items)} 条")

    except requests.exceptions.ConnectionError:
        print(f"  ⚠️  {channel['name']} 网络连接失败（沙箱环境限制）")
    except Exception as e:
        print(f"  ❌ {channel['name']} 抓取异常: {e}")

    return items


def fetch_tianapi_news(api_key: str = None) -> List[NewsItem]:
    """
    从天行数据API获取新闻

    Args:
        api_key: 天行数据API Key（默认从环境变量读取）

    Returns:
        List[NewsItem]: 新闻列表
    """
    key = api_key or TIANAPI_KEY

    if not key:
        print("  ℹ️  未配置天行数据API Key（TIANAPI_KEY），跳过API新闻抓取")
        print("     如需启用，请访问 https://www.tianapi.com 注册获取")
        return []

    print("📡 天行数据API抓取中...")
    all_items = []

    for channel in TIANAPI_CHANNELS:
        items = fetch_tianapi_channel(channel, key)
        all_items.extend(items)

    print(f"  📊 天行API共获取 {len(all_items)} 条")
    return all_items


if __name__ == "__main__":
    # 测试
    news = fetch_tianapi_news()
    for n in news[:3]:
        print(f"  - [{n.category}] {n.title}")
