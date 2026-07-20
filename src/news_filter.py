"""
新闻筛选模块 - 根据时长目标灵活筛选新闻

核心策略：
  1. 不固定条数，根据7-10分钟播报时长目标灵活调整
  2. 保证国内国际新闻各占一半（交替选取）
  3. 优先选择24小时内的新闻（时效性最重要）
  4. 按关键词热度+来源权重+时间新鲜度评分
  5. 过滤广告/推广类内容
"""
import re
import pytz
from datetime import datetime, timezone, timedelta
from typing import List
from news_fetcher import NewsItem
from config import NEWS_FILTER

SHANGHAI_TZ = pytz.timezone("Asia/Shanghai")

# 7-10分钟播报对应的总字数范围（edge-tts -10%约3.5字/秒）
SCRIPT_TARGET_MIN = 1500  # ~7分钟
SCRIPT_TARGET_MAX = 2000  # ~9.5分钟（留余量给开头结尾天气祝福）

# 固定部分的大致字数（问候+天气+过渡+结尾祝福）
FIXED_TEXT_ESTIMATE = 200  # 开头问候+天气+过渡语+结尾祝福约200字

# 每条新闻的平均字数估计（标题+概括）
AVG_NEWS_CHARS = 130

# general 类别（滚动新闻）的关键词分类
INTL_KEYWORDS = ["美国", "日本", "韩国", "俄罗斯", "欧盟", "英国", "法国",
                 "德国", "联合国", "外交", "特朗普", "拜登", "乌克兰", "中东",
                 "以色列", "巴勒斯坦", "北约", "朝鲜", "伊朗", "古巴", "委内瑞拉",
                 "泰国", "越南", "马来西亚", "新加坡", "印度", "澳大利亚",
                 "加拿大", "巴西", "阿根廷", "墨西哥", "南非", "埃及",
                 "土耳其", "沙特", "菲律宾", "印尼", "巴基斯坦", "非盟",
                 "欧洲", "亚洲", "非洲", "美洲", "海外", "全球", "世界"]
DOMESTIC_KEYWORDS = ["国务院", "习近平", "中央", "全国", "省委", "市委",
                     "改革", "民生", "财政", "税收",
                     "法院", "检察院", "公安", "教育部", "卫健委", "央行",
                     "工信部", "科技部", "农业农村", "乡村振兴", "高考",
                     "社保", "医保", "住房", "就业", "退休", "养老金",
                     "GDP", "增长", "出口", "进口", "消费", "投资"]

# 排除的关键词——标题含这些词的新闻不适合播报
EXCLUDE_KEYWORDS = ["采购", "中标", "公告", "招标", "拍卖", "挂牌",
                    "成交", "出让", "拍卖会", "晚高峰", "早高峰",
                    "天气预报", "预警", "交通提示", "出行提示"]


def classify_general_news(item: NewsItem) -> str:
    """
    对 general 类别（滚动新闻）进行二次分类
    根据标题关键词判断是国内还是国际新闻
    """
    if item.category != "general":
        return item.category

    title = item.title

    # 如果标题包含排除关键词（采购/公告等），降为最低优先级
    for kw in EXCLUDE_KEYWORDS:
        if kw in title:
            return "low_quality"

    # 如果标题包含"国际"但后面跟着"旅行/保健/会议中心"等，可能是机构名而非国际新闻
    if "国际" in title:
        # 排除"XX国际XX中心/公司/学校"这类机构名
        if re.search(r'国际.{0,4}(中心|公司|学校|医院|保健|旅行|会议|酒店|机场|航班)', title):
            pass  # 不当作国际新闻
        else:
            return "international"

    for kw in INTL_KEYWORDS:
        if kw in title:
            return "international"
    for kw in DOMESTIC_KEYWORDS:
        if kw in title:
            return "domestic"

    # 如果标题无法判断，看摘要
    summary = item.summary or ""
    intl_hits = sum(1 for kw in INTL_KEYWORDS if kw in summary)
    dom_hits = sum(1 for kw in DOMESTIC_KEYWORDS if kw in summary)
    if intl_hits > dom_hits:
        return "international"
    elif dom_hits > intl_hits:
        return "domestic"

    return "general"


def calculate_score(item: NewsItem) -> float:
    """计算新闻的热度评分"""
    score = 0.0
    title = item.title
    summary = item.summary

    # 1. 关键词命中加分
    for keyword, weight in NEWS_FILTER["hot_keywords"].items():
        if keyword in title:
            score += weight * 2
        if keyword in summary:
            score += weight

    # 2. 来源权重
    score *= item.weight

    # 3. 时间新鲜度加分（越新分越高，权重最大）
    now = datetime.now(SHANGHAI_TZ)
    try:
        pub = item.published
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        hours_ago = (now - pub).total_seconds() / 3600
        if hours_ago < 3:
            score += 5.0
        elif hours_ago < 6:
            score += 3.5
        elif hours_ago < 12:
            score += 2.0
        elif hours_ago < 24:
            score += 1.0
        elif hours_ago < 48:
            score -= 1.0
        else:
            score -= 3.0
    except Exception:
        pass

    # 4. 惩罚：标题过短
    if len(title) < 8:
        score -= 2.0

    # 5. 惩罚：广告/推广类内容
    spam_words = ["广告", "推广", "优惠", "折扣", "免费领", "点击购买",
                  "优惠券", "满减", "限时秒杀"]
    for word in spam_words:
        if word in title:
            score -= 10.0
            break

    # 6. 排除：采购/招标/公告/出行提示等不适合播报的内容
    for word in EXCLUDE_KEYWORDS:
        if word in title:
            score -= 20.0  # 严重降分，几乎不会被选中
            break

    return score


def estimate_news_chars(item: NewsItem) -> int:
    """预估单条新闻的播报字数（标题+概括）"""
    title_len = len(re.sub(r'[\s\n]', '', item.title))
    summary_len = len(re.sub(r'[\s\n]', '', item.summary)) if item.summary else 0

    # 概括部分：如果摘要够长用摘要（截到180字），不够用扩展文案（约80字）
    if summary_len >= 50:
        speech_len = min(summary_len, 180)
    else:
        speech_len = max(summary_len, 0) + 80  # 扩展文案约80字

    return title_len + speech_len + 10  # +10是标点符号


def filter_top_news(items: List[NewsItem]) -> List[NewsItem]:
    """
    筛选新闻，不固定条数，根据时长目标灵活调整

    策略：
    1. 将新闻分为国内和国际两组
    2. 交替从两组中选取评分最高的新闻
    3. 累计预估字数达到目标（1500-2000字）时停止
    4. 保证国内国际各占一半
    """
    if not items:
        return []

    # 对 general 类别新闻进行二次分类
    for item in items:
        item.category = classify_general_news(item)

    # 计算评分
    for item in items:
        item.score = calculate_score(item)

    # 按分数排序
    items.sort(key=lambda x: x.score, reverse=True)

    # 分组（排除 low_quality）
    domestic = [i for i in items if i.category == "domestic"]
    international = [i for i in items if i.category == "international"]
    others = [i for i in items if i.category == "general"]  # 只用 general 补充，排除 low_quality

    # 将 general 类别的新闻按内容倾向分配到国内或国际
    # 如果某组不够，从 others 中补充
    if len(domestic) < len(international) // 2 and others:
        domestic.extend(others[:len(others) // 2])
    if len(international) < len(domestic) // 2 and others:
        used = set(i.link for i in domestic)
        intl_from_others = [i for i in others if i.link not in used]
        international.extend(intl_from_others[:len(others) // 2])

    # 交替选取，累计字数到目标
    result = []
    total_chars = 0
    target_chars = SCRIPT_TARGET_MAX - FIXED_TEXT_ESTIMATE  # 减去固定部分
    min_chars = SCRIPT_TARGET_MIN - FIXED_TEXT_ESTIMATE

    used_links = set()

    # 交替选取：国内国际轮流，保证各半
    # 先计算每组需要多少条（基于预估平均字数）
    approx_total = len(domestic) + len(international)
    if approx_total == 0:
        # 没有分类的新闻，用全部
        for item in items:
            if item.category == "low_quality":
                continue
            result.append(item)
            total_chars += estimate_news_chars(item)
            if total_chars >= target_chars:
                break
    else:
        dom_idx = 0
        intl_idx = 0
        turn = "domestic"  # 先从国内开始

        while True:
            chosen = None

            if turn == "domestic":
                # 找下一条未用的国内新闻
                while dom_idx < len(domestic) and domestic[dom_idx].link in used_links:
                    dom_idx += 1
                if dom_idx < len(domestic):
                    chosen = domestic[dom_idx]
                    dom_idx += 1
                # 如果国内没有了，尝试用国际补
                if not chosen:
                    while intl_idx < len(international) and international[intl_idx].link in used_links:
                        intl_idx += 1
                    if intl_idx < len(international):
                        chosen = international[intl_idx]
                        intl_idx += 1
                turn = "international"
            else:
                # 找下一条未用的国际新闻
                while intl_idx < len(international) and international[intl_idx].link in used_links:
                    intl_idx += 1
                if intl_idx < len(international):
                    chosen = international[intl_idx]
                    intl_idx += 1
                # 如果国际没有了，尝试用国内补
                if not chosen:
                    while dom_idx < len(domestic) and domestic[dom_idx].link in used_links:
                        dom_idx += 1
                    if dom_idx < len(domestic):
                        chosen = domestic[dom_idx]
                        dom_idx += 1
                turn = "domestic"

            if not chosen:
                # 两组都取完了，尝试从 others 补充
                for o in others:
                    if o.link not in used_links:
                        chosen = o
                        break
                if not chosen:
                    break

            # 检查是否超目标
            news_chars = estimate_news_chars(chosen)
            if total_chars + news_chars > target_chars + 50:
                if total_chars < min_chars:
                    pass  # 还没达到最低目标，继续加
                else:
                    break  # 已达目标，停止

            result.append(chosen)
            used_links.add(chosen.link)
            total_chars += news_chars

            if total_chars >= target_chars:
                break

    # 按评分排序（播报顺序：评分高的先播）
    result.sort(key=lambda x: x.score, reverse=True)

    # 打印统计
    dom_count = sum(1 for i in result if i.category == "domestic")
    intl_count = sum(1 for i in result if i.category == "international")
    other_count = len(result) - dom_count - intl_count
    print(f"  📊 筛选结果：共{len(result)}条 | 国内{dom_count}条 国际{intl_count}条 其他{other_count}条")
    print(f"  📊 预估新闻部分约{total_chars}字，加固定部分约{total_chars + FIXED_TEXT_ESTIMATE}字")

    return result
