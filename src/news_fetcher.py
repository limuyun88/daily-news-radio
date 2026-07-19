"""
新闻抓取模块 - 从 RSS 源获取新闻并过滤时间范围
"""
import feedparser
import pytz
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import List
import time
import re

from config import RSS_FEEDS


@dataclass
class NewsItem:
    """新闻数据结构"""
    title: str
    summary: str
    link: str
    published: datetime
    source: str
    category: str
    weight: float = 1.0
    score: float = 0.0  # 筛选评分

    def __repr__(self):
        return f"<News: {self.title[:30]}... [{self.source}]>"


def clean_html(text: str) -> str:
    """清除 HTML 标签，提取纯文本"""
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    clean = soup.get_text(strip=True)
    # 清理多余空白
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def parse_pub_date(entry) -> datetime:
    """解析 RSS 条目的发布时间"""
    # 尝试多种时间字段
    for field in ('published_parsed', 'updated_parsed', 'created_parsed'):
        t = getattr(entry, field, None)
        if t:
            try:
                dt = datetime(*t[:6], tzinfo=timezone.utc)
                return dt
            except Exception:
                continue

    # 尝试解析字符串
    for field in ('published', 'updated', 'created'):
        raw = getattr(entry, field, None)
        if raw:
            try:
                parsed = feedparser._parse_date(raw)
                if parsed:
                    return datetime(*parsed[:6], tzinfo=timezone.utc)
            except Exception:
                continue

    # 如果都解析不了，返回当前时间
    return datetime.now(timezone.utc)


def fetch_single_feed(feed_config: dict, timeout: int = 15) -> List[NewsItem]:
    """抓取单个 RSS 源"""
    items = []
    try:
        feed = feedparser.parse(
            feed_config["url"],
            request_headers={"User-Agent": "Mozilla/5.0 (compatible; DailyNewsBot/1.0)"},
        )

        if feed.bozo and not feed.entries:
            print(f"  ⚠️  {feed_config['name']} 解析失败: {feed.bozo_exception}")
            return items

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            if not title:
                continue

            summary = clean_html(entry.get("summary", "") or entry.get("description", ""))
            link = entry.get("link", "")
            pub_date = parse_pub_date(entry)

            items.append(NewsItem(
                title=title,
                summary=summary,
                link=link,
                published=pub_date,
                source=feed_config["name"],
                category=feed_config["category"],
                weight=feed_config["weight"],
            ))

        print(f"  ✅ {feed_config['name']}: 获取 {len(items)} 条")

    except Exception as e:
        print(f"  ❌ {feed_config['name']} 抓取异常: {e}")

    return items


def filter_by_time_range(items: List[NewsItem], hours: int = 48) -> List[NewsItem]:
    """
    过滤指定时间范围内的新闻
    默认取过去48小时，宽松一些避免漏新闻
    """
    if not items:
        return items

    shanghai_tz = pytz.timezone("Asia/Shanghai")
    now = datetime.now(shanghai_tz)

    # 计算时间范围：过去 hours 小时
    start = now - timedelta(hours=hours)
    end = now

    filtered = []
    for item in items:
        try:
            # 转换为上海时区比较
            if item.published.tzinfo is None:
                item.published = item.published.replace(tzinfo=timezone.utc)
            pub_shanghai = item.published.astimezone(shanghai_tz)
            if start <= pub_shanghai <= end:
                filtered.append(item)
        except Exception:
            # 时间解析失败的也保留
            filtered.append(item)

    # 如果过滤后太少，放宽到全部（RSS本身通常只返回最近的内容）
    if len(filtered) < 10:
        print(f"  ⚠️  时间过滤后仅 {len(filtered)} 条，放宽到全部原始数据")
        filtered = items

    return filtered


def deduplicate(items: List[NewsItem]) -> List[NewsItem]:
    """按标题去重（保留首次出现的）"""
    seen = set()
    unique = []
    for item in items:
        # 标准化标题用于比较
        key = re.sub(r'[^\w\u4e00-\u9fff]', '', item.title.lower())
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def fetch_all_news(max_retries: int = 2) -> List[NewsItem]:
    """抓取所有 RSS 源的新闻"""
    all_items = []

    print("📡 开始抓取新闻...")
    for feed_config in RSS_FEEDS:
        for attempt in range(max_retries):
            items = fetch_single_feed(feed_config)
            if items:
                all_items.extend(items)
                break
            if attempt < max_retries - 1:
                time.sleep(2)

    print(f"\n📊 共抓取 {len(all_items)} 条原始新闻")

    # 去重
    all_items = deduplicate(all_items)
    print(f"📊 去重后 {len(all_items)} 条")

    # 时间过滤（过去48小时，宽松一些避免漏新闻）
    all_items = filter_by_time_range(all_items, hours=48)
    print(f"📊 时间过滤后 {len(all_items)} 条")

    return all_items


if __name__ == "__main__":
    # 测试
    news = fetch_all_news()
    for n in news[:5]:
        print(f"  - [{n.category}] {n.title}")
