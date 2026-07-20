"""
播报文稿生成模块 - 将新闻转为口语化播报文稿，含开头问候和祝福结尾
"""
import pytz
from datetime import datetime
from typing import List
from news_fetcher import NewsItem
from config import BLESSINGS

WEEKDAY_MAP = {
    0: "一", 1: "二", 2: "三", 3: "四",
    4: "五", 5: "六", 6: "日",
}


def get_today_blessing() -> str:
    """根据日期获取今日祝福语（轮换）"""
    today = datetime.now(pytz.timezone("Asia/Shanghai"))
    day_of_year = today.timetuple().tm_yday
    index = day_of_year % len(BLESSINGS)
    return BLESSINGS[index]


def truncate_summary(summary: str, max_len: int = 60) -> str:
    """截取摘要到指定长度，保证语句通顺"""
    if not summary:
        return ""
    if len(summary) <= max_len:
        return summary

    # 尝试在句号处截断
    cut = summary[:max_len]
    for sep in ["。", "；", "，", "、", " "]:
        pos = cut.rfind(sep)
        if pos > max_len // 2:
            return cut[:pos] + "。"
    return cut + "……"


def format_news_for_speech(item: NewsItem, index: int) -> str:
    """将单条新闻转为口语化播报文案"""
    title = item.title.strip()

    # 截取摘要
    summary = truncate_summary(item.summary, max_len=80)

    if summary:
        return f"第{index}条：{title}。{summary}"
    else:
        return f"第{index}条：{title}。"


def generate_broadcast_script(news_items: List[NewsItem], weather_speech: str = "") -> str:
    """
    生成完整播报文稿
    格式：问候 + 天气播报 + 新闻列表 + 祝福结尾

    Args:
        news_items: 新闻列表
        weather_speech: 天气播报文案（空字符串则跳过天气）
    """
    shanghai_tz = pytz.timezone("Asia/Shanghai")
    now = datetime.now(shanghai_tz)

    weekday = WEEKDAY_MAP[now.weekday()]
    date_str = f"{now.month}月{now.day}日，星期{weekday}"

    # 开头问候
    script_parts = [
        f"早上好！今天是{date_str}。",
    ]

    # 天气播报（如果有）
    if weather_speech:
        script_parts.append(weather_speech)
        script_parts.append("")

    # 过渡到新闻
    script_parts.append(f"下面为您播报今日新闻，共{len(news_items)}条。")
    script_parts.append("")

    # 新闻正文
    for i, item in enumerate(news_items, 1):
        script_parts.append(format_news_for_speech(item, i))
        script_parts.append("")  # 间隔

    # 结尾祝福
    blessing = get_today_blessing()
    script_parts.extend([
        "",
        "以上就是今天的全部新闻。",
        f"最后送您一句话：{blessing}",
        "祝您今天心情愉快，身体健康！我们明天再见。",
    ])

    return "\n".join(script_parts)


def generate_text_summary(news_items: List[NewsItem]) -> str:
    """生成纯文本新闻摘要（用于H5页面展示）"""
    lines = []
    for i, item in enumerate(news_items, 1):
        lines.append(f"{i}. {item.title}")
        if item.summary:
            summary = truncate_summary(item.summary, max_len=100)
            lines.append(f"   {summary}")
        if item.source:
            lines.append(f"   来源：{item.source}")
        lines.append("")

    return "\n".join(lines)
