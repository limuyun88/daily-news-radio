"""
播报文稿生成模块 - 将新闻转为口语化播报文稿，含开头问候和祝福结尾

核心改进：
  1. 每条新闻生成50字以上的口语化概括（不只有标题）
  2. 不播报新闻来源
  3. 总文稿控制在1500-2200字（约7-10分钟播报）
"""
import re
import pytz
from datetime import datetime
from typing import List
from news_fetcher import NewsItem
from config import BLESSINGS

WEEKDAY_MAP = {
    0: "一", 1: "二", 2: "三", 3: "四",
    4: "五", 5: "六", 6: "日",
}

# 每条新闻播报目标字数
NEWS_TARGET_MIN = 100  # 最少100字（含标题和概括）
NEWS_TARGET_MAX = 220  # 最多220字

# 7-10分钟播报对应的总字数范围（edge-tts -10%约3.5字/秒）
SCRIPT_TARGET_MIN = 1500  # ~7分钟
SCRIPT_TARGET_MAX = 2100  # ~10分钟


def get_today_blessing() -> str:
    """根据日期获取今日祝福语（轮换）"""
    today = datetime.now(pytz.timezone("Asia/Shanghai"))
    day_of_year = today.timetuple().tm_yday
    index = day_of_year % len(BLESSINGS)
    return BLESSINGS[index]


def clean_summary(summary: str) -> str:
    """清理摘要中的电头、记者名等无用信息，保留核心内容"""
    if not summary:
        return ""

    text = summary.strip()

    # 删除电头：新华社北京7月19日电、中新网东莞7月20日电 等
    text = re.sub(r'^[新华人民中环球球]社?[\u4e00-\u9fa5]{2,15}[\d]{1,2}月[\d]{1,2}日电?\s*', '', text)
    text = re.sub(r'^本报[\u4e00-\u9fa5]{2,8}[\d]{1,2}月[\d]{1,2}日电?\s*', '', text)
    text = re.sub(r'^（记者[^）]+）\s*', '', text)
    text = re.sub(r'^\(记者[^)]+\)\s*', '', text)
    # 删除开头的 "题：" 等
    text = re.sub(r'^题[：:]\s*', '', text)
    # 删除 "XX日电" 残留
    text = re.sub(r'^[\u4e00-\u9fa5]{2,8}[\d]{1,2}月[\d]{1,2}日电?\s*', '', text)
    # 删除记者名括号（如"(向一鹏)"、"(记者 苏婧欣)"、"(付敬懿 吕伟铭)"）
    text = re.sub(r'^[\(（][^）)]*[\)）]\s*', '', text)

    # 如果清理后太短且是记者名等，返回空
    if len(text) < 15 and re.match(r'^[\u4e00-\u9fa5]{2,6}$', text):
        return ""

    # 删除来源标记（来源：XXX）
    text = re.sub(r'来源[:：][\u4e00-\u9fa5\w]+', '', text)

    # 全局删除总台记者/记者名标记（可能在文中任意位置）
    text = re.sub(r'[\(（]总台记者[^）)]*[\)）]', '', text)
    text = re.sub(r'[\(（]记者[^）)]*[\)）]', '', text)
    # 删除结尾的记者署名（如 "宫祥诚"）
    text = re.sub(r'[\u4e00-\u9fa5]{2,4}$', '', text) if len(text) > 50 else text

    # 清理多余空白
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def clean_title(title: str) -> str:
    """清理标题中的特殊符号和前缀"""
    title = title.strip()
    # 去掉括号内容（如"(国际论坛)"）
    title = re.sub(r'[（(][^）)]*[）)]', '', title)
    # 去掉前缀（如"新华时评·"等保留原样，但去掉频道标记）
    title = re.sub(r'^[\u4e00-\u9fa5]{2,4}[:：]\s*', '', title)
    # 替换特殊分隔符
    title = re.sub(r'[丨|·——\-—]', '，', title)
    # 清理多余的逗号和空白
    title = re.sub(r'，\s*，', '，', title)
    title = re.sub(r'^[，,\s]+', '', title)
    title = title.strip('，。 ')
    return title


def generate_summary_speech(title: str, raw_summary: str) -> str:
    """
    从标题和摘要生成口语化播报文案

    策略：
    1. 清理标题和摘要
    2. 如果摘要开头与标题重复，删除重复部分
    3. 如果清理后的摘要有实质内容（>30字），使用摘要
    4. 如果摘要太短，用标题+关键词扩展成通顺的语句
    5. 保证每条不少于50字的概括
    """
    clean_t = clean_title(title)
    clean_s = clean_summary(raw_summary)

    # 如果摘要开头包含标题（或反过来），删除重复部分
    if clean_s and clean_t:
        # 摘要以标题开头
        if clean_s.startswith(clean_t):
            clean_s = clean_s[len(clean_t):].strip("。，、， ")
        # 标题以摘要开头（摘要包含完整标题）
        elif clean_t.startswith(clean_s[:len(clean_t)]):
            pass  # 标题已经说了，摘要的重复部分会在后面截取时自然去掉
        # 模糊匹配：前15字重复
        elif len(clean_s) > 15 and len(clean_t) > 15:
            prefix = clean_t[:15]
            if clean_s.startswith(prefix):
                clean_s = clean_s[len(prefix):].strip("。，、， ")

    # 情况1：摘要足够长（>50字），直接用清理后的摘要
    if len(clean_s) >= 50:
        if len(clean_s) > NEWS_TARGET_MAX:
            # 截断到合适长度
            cut = clean_s[:NEWS_TARGET_MAX]
            for sep in ["。", "；", "，", "、"]:
                pos = cut.rfind(sep)
                if pos > 60:
                    return cut[:pos] + "。"
            return cut[:150] + "。"
        return clean_s if clean_s.endswith("。") else clean_s + "。"

    # 情况2：摘要有内容但不够长（10-50字），用摘要+扩展
    if len(clean_s) >= 10:
        # 如果摘要本身够了
        if len(clean_s) >= 50:
            return clean_s if clean_s.endswith("。") else clean_s + "。"
        # 不够的话用摘要+扩展文案
        base = clean_s if clean_s.endswith("。") else clean_s + "。"
        extra = generate_contextual_expansion(title, len(base))
        return f"{base}{extra}"

    # 情况3：摘要几乎没有可用内容，用扩展文案
    else:
        extra = generate_contextual_expansion(title, 0)
        return extra
        return f"{base}{extra}"


def generate_contextual_expansion(title: str, current_len: int) -> str:
    """
    根据新闻类型生成上下文相关的扩展文案
    确保每条新闻的总字数达到100字以上
    """
    need_chars = max(NEWS_TARGET_MIN - current_len, 30)

    # 根据新闻主题生成不同的扩展文案
    expansions = []

    if any(kw in title for kw in ["经济", "增长", "出口", "进口", "产业", "GDP", "消费"]):
        expansions = [
            "这一消息反映出当前经济运行中的新变化和新趋势，值得大家关注。",
            "从这则消息中可以看出，相关行业正在迎来新的发展机遇和挑战。",
            "这也体现了我国在推动经济高质量发展方面取得的积极成效。",
        ]
    elif any(kw in title for kw in ["国际", "美国", "日本", "韩国", "俄罗斯", "欧盟", "联合国"]):
        expansions = [
            "这一动态引起了国际社会的广泛关注，也对相关地区的局势产生影响。",
            "这一消息反映了当前国际关系的新变化，值得我们持续关注。",
            "国际形势的发展变化与我们息息相关，需要我们密切关注。",
        ]
    elif any(kw in title for kw in ["政策", "改革", "部署", "印发", "制度", "法规"]):
        expansions = [
            "这一举措将对相关领域产生积极影响，惠及广大人民群众。",
            "有关部门表示，将继续推进相关工作的落实和完善。",
            "这一政策的实施，将为社会发展和民生改善带来实实在在的好处。",
        ]
    elif any(kw in title for kw in ["科技", "人工智能", "技术", "创新", "数字", "芯片"]):
        expansions = [
            "这标志着我国在这一科技领域又取得了新的进展和突破。",
            "科技创新的步伐不断加快，将为我们带来更多便利和机遇。",
            "这一成果展现了科技发展的最新趋势，值得我们期待。",
        ]
    elif any(kw in title for kw in ["安全", "灾害", "地震", "事故", "救援", "应急"]):
        expansions = [
            "相关部门已迅速展开应急处置和救援工作，确保人民群众生命财产安全。",
            "目前各项救援和善后工作正在紧张有序地进行中。",
            "这一事件提醒我们要增强安全意识，做好防范工作。",
        ]
    elif any(kw in title for kw in ["教育", "学校", "学生", "考试", "高考"]):
        expansions = [
            "这一消息引起了社会各界的广泛讨论和关注。",
            "教育领域的新变化，将对学生和家长产生直接影响。",
            "这也反映出我国教育改革持续推进的积极态势。",
        ]
    elif any(kw in title for kw in ["健康", "医疗", "卫生", "药品", "疾病"]):
        expansions = [
            "这一消息与大家的健康息息相关，值得关注和了解。",
            "医疗健康领域的新进展，将为群众带来更好的就医体验。",
            "有关部门提醒大家关注自身健康，做好疾病预防工作。",
        ]
    elif any(kw in title for kw in ["环境", "生态", "保护", "气候", "碳"]):
        expansions = [
            "这体现了我国在生态文明建设方面的持续努力和投入。",
            "环境保护工作的推进，将为子孙后代留下绿水青山。",
            "这一举措有助于推动绿色低碳发展，建设美丽中国。",
        ]
    else:
        expansions = [
            "这一消息引起了社会各界的关注和讨论，值得我们深入了解。",
            "相关工作的推进，将为经济社会发展带来积极影响。",
            "这反映了当前社会发展的新动态和新趋势。",
            "有关部门正在积极推进相关工作的落实和完善。",
        ]

    # 组合扩展文案直到达到目标字数
    import random
    result = ""
    for exp in expansions:
        if len(result) >= need_chars:
            break
        result += exp

    # 如果还不够，补充通用语句
    if len(result) < need_chars - 10:
        result += "让我们一起关注后续的发展情况。"

    return result


def format_news_for_speech(item: NewsItem, index: int) -> str:
    """
    将单条新闻转为口语化播报文案
    格式：第X条：标题。概括（50字以上，不含来源）
    """
    title = item.title.strip()
    clean_t = clean_title(title)

    # 生成核心概括
    summary_speech = generate_summary_speech(title, item.summary)

    return f"第{index}条：{clean_t}。{summary_speech}"


def estimate_duration(text: str) -> float:
    """估算播报时长（秒），edge-tts -10%语速约3.5字/秒"""
    effective = len(re.sub(r'[\s\n]', '', text))
    return effective / 3.5


def generate_broadcast_script(news_items: List[NewsItem], weather_speech: str = "") -> str:
    """
    生成完整播报文稿
    格式：问候 + 天气播报 + 新闻列表 + 祝福结尾
    总字数控制在1500-2200字（约7-10分钟）
    """
    shanghai_tz = pytz.timezone("Asia/Shanghai")
    now = datetime.now(shanghai_tz)

    weekday = WEEKDAY_MAP[now.weekday()]
    date_str = f"{now.month}月{now.day}日，星期{weekday}"

    script_parts = [
        f"早上好！今天是{date_str}。",
    ]

    if weather_speech:
        script_parts.append(weather_speech)
        script_parts.append("")

    script_parts.append(f"下面为您播报今日新闻，共{len(news_items)}条。")
    script_parts.append("")

    for i, item in enumerate(news_items, 1):
        script_parts.append(format_news_for_speech(item, i))
        script_parts.append("")

    blessing = get_today_blessing()
    script_parts.extend([
        "",
        "以上就是今天的全部新闻。",
        f"最后送您一句话：{blessing}",
        "祝您今天心情愉快，身体健康！我们明天再见。",
    ])

    script = "\n".join(script_parts)

    # 统计字数和时长
    duration = estimate_duration(script)
    total_chars = len(re.sub(r'[\s\n]', '', script))
    print(f"  📊 文稿统计：{total_chars}字，预计播报{duration:.0f}秒（约{duration/60:.1f}分钟）")

    if duration < 420:
        print(f"  ⚠️  预计时长{duration/60:.1f}分钟，低于7分钟目标")
    elif duration > 600:
        print(f"  ⚠️  预计时长{duration/60:.1f}分钟，超过10分钟目标")
    else:
        print(f"  ✅ 播报时长在7-10分钟目标范围内")

    return script


def truncate_summary(summary: str, max_len: int = 60) -> str:
    """截取摘要到指定长度（H5页面展示用）"""
    if not summary:
        return ""
    if len(summary) <= max_len:
        return summary
    cut = summary[:max_len]
    for sep in ["。", "；", "，", "、", " "]:
        pos = cut.rfind(sep)
        if pos > max_len // 2:
            return cut[:pos] + "。"
    return cut + "……"


def generate_text_summary(news_items: List[NewsItem]) -> str:
    """生成纯文本新闻摘要（用于H5页面和历史记录）"""
    lines = []
    for i, item in enumerate(news_items, 1):
        lines.append(f"{i}. {item.title}")
        speech = generate_summary_speech(item.title, item.summary)
        if speech:
            lines.append(f"   {speech}")
        lines.append("")

    return "\n".join(lines)
