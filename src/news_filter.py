"""
新闻筛选模块 - 按热度评分排序选出 TOP10
"""
from datetime import datetime, timezone, timedelta
from typing import List
from news_fetcher import NewsItem
from config import NEWS_FILTER

# 上海时区
SHANGHAI_TZ = timedelta(hours=8)


def calculate_score(item: NewsItem) -> float:
    """计算新闻的热度评分"""
    score = 0.0
    title = item.title
    summary = item.summary

    # 1. 关键词命中加分
    for keyword, weight in NEWS_FILTER["hot_keywords"].items():
        if keyword in title:
            score += weight * 2  # 标题命中权重更高
        if keyword in summary:
            score += weight

    # 2. 来源权重
    score *= item.weight

    # 3. 国际新闻基础分（保证国际新闻有最低数量）
    if item.category == "international":
        score += 1.0
    elif item.category == "domestic":
        score += 0.8

    # 4. 时间新鲜度加分（越新分越高）
    now = datetime.now(timezone.utc)
    try:
        hours_ago = (now - item.published).total_seconds() / 3600
        if hours_ago < 6:
            score += 2.0
        elif hours_ago < 12:
            score += 1.0
        elif hours_ago < 24:
            score += 0.5
    except Exception:
        pass

    # 5. 惩罚：标题过短或无摘要
    if len(title) < 8:
        score -= 2.0
    if not summary or len(summary) < 10:
        score -= 1.0

    # 6. 惩罚：广告/推广类内容
    spam_words = ["广告", "推广", "优惠", "折扣", "免费领", "点击购买"]
    for word in spam_words:
        if word in title:
            score -= 5.0
            break

    return score


def filter_top_news(items: List[NewsItem]) -> List[NewsItem]:
    """筛选 TOP N 新闻，保证国内外平衡"""
    if not items:
        return []

    top_n = NEWS_FILTER["top_n"]

    # 计算评分
    for item in items:
        item.score = calculate_score(item)

    # 按分数排序
    items.sort(key=lambda x: x.score, reverse=True)

    # 分类确保平衡
    min_intl = NEWS_FILTER.get("min_international", 3)
    min_dom = NEWS_FILTER.get("min_domestic", 4)

    domestic = [i for i in items if i.category == "domestic"]
    international = [i for i in items if i.category == "international"]
    others = [i for i in items if i.category not in ("domestic", "international")]

    result = []

    # 先取评分最高的国内和国际新闻
    result.extend(domestic[:min_dom])
    result.extend(international[:min_intl])

    # 再用剩余配额补全
    remaining = top_n - len(result)
    if remaining > 0:
        used_links = {i.link for i in result}
        pool = [i for i in items if i.link not in used_links]
        result.extend(pool[:remaining])

    # 重新按分数排序最终结果
    result.sort(key=lambda x: x.score, reverse=True)

    return result[:top_n]
