"""
新闻筛选模块 - 按热度评分排序选出 TOP10

核心策略：
  1. 优先选择24小时内的新闻（时效性最重要）
  2. 按关键词热度+来源权重+时间新鲜度评分
  3. 保证国内外新闻平衡
  4. 过滤广告/推广类内容
"""
import pytz
from datetime import datetime, timezone, timedelta
from typing import List
from news_fetcher import NewsItem
from config import NEWS_FILTER

SHANGHAI_TZ = pytz.timezone("Asia/Shanghai")

# general 类别（滚动新闻）的关键词分类
INTL_KEYWORDS = ["国际", "美国", "日本", "韩国", "俄罗斯", "欧盟", "英国", "法国",
                 "德国", "联合国", "外交", "特朗普", "拜登", "乌克兰", "中东",
                 "以色列", "巴勒斯坦", "北约", "朝鲜", "伊朗", "古巴", "委内瑞拉"]
DOMESTIC_KEYWORDS = ["国内", "国务院", "习近平", "中央", "全国", "省委", "市委",
                     "改革", "发展", "政策", "民生", "经济", "财政", "税收",
                     "法院", "检察院", "公安", "教育部", "卫健委", "央行"]


def classify_general_news(item: NewsItem) -> str:
    """
    对 general 类别（滚动新闻）进行二次分类
    根据标题关键词判断是国内还是国际新闻
    """
    if item.category != "general":
        return item.category

    title = item.title
    for kw in INTL_KEYWORDS:
        if kw in title:
            return "international"
    for kw in DOMESTIC_KEYWORDS:
        if kw in title:
            return "domestic"
    return "general"  # 无法判断的归为其他


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

    # 4. 时间新鲜度加分（越新分越高，权重最大）
    now = datetime.now(SHANGHAI_TZ)
    try:
        pub = item.published
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        hours_ago = (now - pub).total_seconds() / 3600
        if hours_ago < 3:
            score += 5.0    # 3小时内最高优先级
        elif hours_ago < 6:
            score += 3.5
        elif hours_ago < 12:
            score += 2.0
        elif hours_ago < 24:
            score += 1.0
        elif hours_ago < 48:
            score -= 1.0    # 超过24小时降分
        else:
            score -= 3.0    # 超过48小时严重降分
    except Exception:
        pass

    # 5. 惩罚：标题过短
    if len(title) < 8:
        score -= 2.0

    # 6. 惩罚：广告/推广类内容
    spam_words = ["广告", "推广", "优惠", "折扣", "免费领", "点击购买",
                  "优惠券", "满减", "限时秒杀"]
    for word in spam_words:
        if word in title:
            score -= 10.0
            break

    return score


def filter_top_news(items: List[NewsItem]) -> List[NewsItem]:
    """筛选 TOP N 新闻，保证国内外平衡"""
    if not items:
        return []

    top_n = NEWS_FILTER["top_n"]

    # 对 general 类别新闻进行二次分类
    for item in items:
        item.category = classify_general_news(item)

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

    # 再用剩余配额从所有新闻中补全（取分数最高的）
    remaining = top_n - len(result)
    if remaining > 0:
        used_links = {i.link for i in result}
        pool = [i for i in items if i.link not in used_links]
        result.extend(pool[:remaining])

    # 重新按分数排序最终结果
    result.sort(key=lambda x: x.score, reverse=True)

    return result[:top_n]
